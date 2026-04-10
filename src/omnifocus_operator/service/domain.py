"""Business rules -- lifecycle, tags, cycle detection, no-op, move processing.

Encapsulates all domain logic that the orchestrator delegates to. Receives
clean Python values (never ``_Unset``), returns results the orchestrator can
merge into the final response.
"""

from __future__ import annotations

import calendar
import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar

if TYPE_CHECKING:
    from collections.abc import Mapping, Sequence

from pydantic import BaseModel

from omnifocus_operator.agent_messages.errors import (
    CIRCULAR_REFERENCE,
    ENTITY_TYPE_MISMATCH_ANCHOR,
    NO_POSITION_KEY,
)
from omnifocus_operator.agent_messages.warnings import (
    AVAILABILITY_REMAINING_INCLUDES_AVAILABLE,
    AVAILABILITY_REMAINING_INCLUDES_BLOCKED,
    DEFER_AFTER_NOW_HINT,
    DEFER_BEFORE_NOW_HINT,
    DUE_SOON_THRESHOLD_NOT_DETECTED,
    EDIT_COMPLETED_TASK,
    EDIT_NO_CHANGES_DETECTED,
    EDIT_NO_CHANGES_SPECIFIED,
    FILTER_DID_YOU_MEAN,
    FILTER_MULTI_MATCH,
    FILTER_NO_MATCH,
    LIFECYCLE_ALREADY_IN_STATE,
    LIFECYCLE_CROSS_STATE,
    LIFECYCLE_REPEATING_COMPLETE,
    LIFECYCLE_REPEATING_DROP,
    MOVE_SAME_CONTAINER,
    REPETITION_ANCHOR_DATE_MISSING,
    REPETITION_AUTO_CLEAR_ON,
    REPETITION_AUTO_CLEAR_ON_DATES,
    REPETITION_EMPTY_ON,
    REPETITION_EMPTY_ON_DATES,
    REPETITION_EMPTY_ON_DAYS,
    REPETITION_END_DATE_PAST,
    REPETITION_FROM_COMPLETION_BYDAY,
    REPETITION_NO_OP,
    TAG_ALREADY_ON_TASK,
    TAG_NOT_ON_TASK,
    TAGS_ALREADY_MATCH,
)
from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskResult
from omnifocus_operator.contracts.use_cases.list._date_filter import DateFilter
from omnifocus_operator.contracts.use_cases.list._enums import AvailabilityFilter
from omnifocus_operator.models.enums import Availability, DurationUnit, Schedule
from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    Frequency,
    RepetitionRule,
)
from omnifocus_operator.service.errors import EntityTypeMismatchError
from omnifocus_operator.service.fuzzy import (
    suggest_close_matches as _suggest_close_matches,
)
from omnifocus_operator.service.resolve_dates import (
    ResolvedDateBounds,
    resolve_date_filter,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.protocols import Repository
    from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
    from omnifocus_operator.contracts.shared.repetition_rule import (
        FrequencyEditSpec,
        RepetitionRuleRepoPayload,
    )
    from omnifocus_operator.contracts.use_cases.edit.tasks import (
        EditTaskCommand,
        EditTaskRepoPayload,
    )
    from omnifocus_operator.contracts.use_cases.list.projects import (
        ReviewDueFilter,
    )
    from omnifocus_operator.models.common import TagRef
    from omnifocus_operator.models.enums import BasedOn, DueSoonSetting
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.service.resolve import Resolver, _HasIdAndName

logger = logging.getLogger(__name__)

__all__ = ["DomainLogic", "ResolvedDateFilters"]


# ---------------------------------------------------------------------------
# Data structures
# ---------------------------------------------------------------------------


@dataclass(frozen=True)
class ResolvedDateFilters:
    """Result of resolving all date filter fields to absolute bounds.

    Internal dataclass -- not a boundary model (see model-taxonomy.md).
    """

    bounds: dict[str, ResolvedDateBounds]
    lifecycle_additions: list[Availability]
    warnings: list[str]


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _to_utc_ts(val: object) -> object:
    """Normalize a date value to UTC timestamp for comparison, or return as-is."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.astimezone(UTC).timestamp()
    if isinstance(val, str):
        return datetime.fromisoformat(val).astimezone(UTC).timestamp()
    return val


# ---------------------------------------------------------------------------
# DomainLogic
# ---------------------------------------------------------------------------


class DomainLogic:
    """Product decisions — the opinionated logic that defines this tool's behavior.

    See architecture.md "Service Layer: Product Decisions vs Plumbing".
    """

    def __init__(self, repo: Repository, resolver: Resolver) -> None:
        self._repo = repo
        self._resolver = resolver

    # -- Date filter resolution ------------------------------------------------

    _DATE_FIELD_NAMES = ("due", "defer", "planned", "completed", "dropped", "added", "modified")
    _LIFECYCLE_MAP: ClassVar[dict[str, Availability]] = {
        "completed": Availability.COMPLETED,
        "dropped": Availability.DROPPED,
    }

    def resolve_date_filters(
        self,
        query: Any,
        now: datetime,
        week_start: int,
        due_soon_setting: DueSoonSetting | None,
    ) -> ResolvedDateFilters:
        """Resolve date filter fields to absolute bounds with lifecycle mapping.

        Extracts the 7 date fields from *query*, skipping any that are unset.
        For each set field:
        - Lifecycle fields (completed/dropped) add the corresponding Availability.
        - "any" shortcuts expand availability only -- no date bounds.
        - "soon" without ``due_soon_setting`` falls back to TODAY bounds + warning.
        - Everything else delegates to ``resolve_date_filter()``.
        """
        bounds: dict[str, ResolvedDateBounds] = {}
        lifecycle_additions: list[Availability] = []
        warnings: list[str] = []

        for field_name in self._DATE_FIELD_NAMES:
            value = getattr(query, field_name)
            if not is_set(value):
                continue
            # Lifecycle expansion
            if field_name in self._LIFECYCLE_MAP:
                lifecycle_additions.append(self._LIFECYCLE_MAP[field_name])

            # Defer hint detection (D-10, D-11)

            if field_name == "defer" and isinstance(value, DateFilter):
                if value.after == "now":
                    warnings.append(DEFER_AFTER_NOW_HINT)
                if value.before == "now":
                    warnings.append(DEFER_BEFORE_NOW_HINT)

            # "all" shortcut -- lifecycle expansion only, no date bounds
            if isinstance(value, StrEnum) and value.value == "all":
                continue

            # "soon" without due_soon_setting -- domain owns fallback
            if isinstance(value, StrEnum) and value.value == "soon" and due_soon_setting is None:
                midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                bounds[field_name] = ResolvedDateBounds(
                    after=midnight,
                    before=midnight + timedelta(days=1),
                )
                warnings.append(DUE_SOON_THRESHOLD_NOT_DETECTED)
                continue

            # Normal resolution
            bounds[field_name] = resolve_date_filter(
                value,
                field_name,
                now,
                week_start=week_start,
                due_soon_setting=due_soon_setting,
            )

        return ResolvedDateFilters(
            bounds=bounds,
            lifecycle_additions=lifecycle_additions,
            warnings=warnings,
        )

    # -- Availability expansion ------------------------------------------------

    def expand_task_availability(
        self,
        filters: list[AvailabilityFilter],
        lifecycle_additions: list[Availability],
    ) -> tuple[list[Availability], list[str]]:
        """Expand availability filters + merge lifecycle additions.

        REMAINING expands to {AVAILABLE, BLOCKED}. Redundant combos warn.
        Returns (expanded availability list, warnings).
        """

        warnings: list[str] = []
        result_set: set[Availability] = set()

        has_remaining = AvailabilityFilter.REMAINING in filters
        if has_remaining:
            result_set |= {Availability.AVAILABLE, Availability.BLOCKED}
            if AvailabilityFilter.AVAILABLE in filters:
                warnings.append(AVAILABILITY_REMAINING_INCLUDES_AVAILABLE)
            if AvailabilityFilter.BLOCKED in filters:
                warnings.append(AVAILABILITY_REMAINING_INCLUDES_BLOCKED)
        for f in filters:
            if f != AvailabilityFilter.REMAINING:
                result_set.add(Availability(f.value))

        result_set |= set(lifecycle_additions)
        return list(result_set), warnings

    # -- Review-due expansion --------------------------------------------------

    def expand_review_due(self, f: ReviewDueFilter, now: datetime) -> datetime:
        """Expand ReviewDueFilter to a concrete datetime threshold."""
        if f.amount is None:
            return now
        unit: DurationUnit = f.unit  # type: ignore[assignment]
        amount = f.amount
        if unit is DurationUnit.DAYS:
            return now + timedelta(days=amount)
        if unit is DurationUnit.WEEKS:
            return now + timedelta(weeks=amount)
        if unit is DurationUnit.MONTHS:
            month = now.month + amount
            year = now.year + (month - 1) // 12
            month = (month - 1) % 12 + 1
            day = min(now.day, calendar.monthrange(year, month)[1])
            return now.replace(year=year, month=month, day=day)
        if unit is DurationUnit.YEARS:
            year = now.year + amount
            day = min(now.day, calendar.monthrange(year, now.month)[1])
            return now.replace(year=year, day=day)
        raise AssertionError  # unreachable: all DurationUnit members handled above

    # -- Filter resolution -----------------------------------------------------

    def check_filter_resolution(
        self,
        value: str,
        resolved_ids: list[str],
        entities: Sequence[_HasIdAndName],
        entity_type: str,
    ) -> list[str]:
        """Generate warnings for filter resolution outcomes.

        Returns 0 or 1 warnings:
        - Multiple matches → FILTER_MULTI_MATCH with IDs and names
        - No match with close names → FILTER_DID_YOU_MEAN
        - No match, no suggestions → FILTER_NO_MATCH
        - Single match → no warning
        """
        if len(resolved_ids) > 1:
            name_map = {e.id: e.name for e in entities}
            match_details = ", ".join(f"{eid} ({name_map.get(eid, '?')})" for eid in resolved_ids)
            return [
                FILTER_MULTI_MATCH.format(
                    value=value,
                    count=len(resolved_ids),
                    entity_type=entity_type,
                    matches=match_details,
                )
            ]
        if len(resolved_ids) == 0:
            entity_names = [e.name for e in entities]
            suggestions = _suggest_close_matches(value, entity_names)
            if suggestions:
                return [
                    FILTER_DID_YOU_MEAN.format(
                        entity_type=entity_type,
                        value=value,
                        suggestions=", ".join(suggestions),
                    )
                ]
            return [FILTER_NO_MATCH.format(entity_type=entity_type, value=value)]
        return []

    # -- Clear-intent normalization ----------------------------------------

    def normalize_clear_intents(self, command: EditTaskCommand) -> EditTaskCommand:
        """Normalize null-means-clear fields before payload construction.

        OmniFocus semantics:
        - note=None -> note='' (bridge expects empty string to clear)
        - tags.replace=None -> tags.replace=[] (empty list clears all tags)

        Centralizes this pattern so PayloadBuilder stays pure construction.
        """
        # note: None means "clear the note" -> empty string for bridge
        if is_set(command.note) and command.note is None:
            command = command.model_copy(update={"note": ""})

        # tags.replace: None means "clear all tags" -> empty list
        if is_set(command.actions) and is_set(command.actions.tags):
            tag_actions = command.actions.tags
            if is_set(tag_actions.replace) and tag_actions.replace is None:
                new_tags = tag_actions.model_copy(update={"replace": []})
                new_actions = command.actions.model_copy(update={"tags": new_tags})
                command = command.model_copy(update={"actions": new_actions})

        return command

    # -- Lifecycle ---------------------------------------------------------

    def process_lifecycle(
        self,
        action: str,
        task: Task,
    ) -> tuple[bool, list[str]]:
        """Returns (should_call_bridge, warnings)."""
        warnings: list[str] = []
        target = Availability.COMPLETED if action == "complete" else Availability.DROPPED

        # No-op: already in target state
        if task.availability == target:
            state_word = "complete" if action == "complete" else "dropped"
            warnings.append(LIFECYCLE_ALREADY_IN_STATE.format(state_word=state_word))
            return False, warnings

        # Cross-state: completed <-> dropped
        if task.availability in (Availability.COMPLETED, Availability.DROPPED):
            prior_state = task.availability.value
            new_state = "complete" if action == "complete" else "dropped"
            warnings.append(
                LIFECYCLE_CROSS_STATE.format(prior_state=prior_state, new_state=new_state)
            )

        # Repeating task
        if task.repetition_rule is not None:
            if action == "complete":
                warnings.append(LIFECYCLE_REPEATING_COMPLETE)
            else:
                warnings.append(LIFECYCLE_REPEATING_DROP)

        return True, warnings

    # -- Status warnings ---------------------------------------------------

    def check_completed_status(
        self,
        task: Task,
        has_lifecycle: bool,
    ) -> list[str]:
        """Warn if editing a completed/dropped task without lifecycle action."""
        if not has_lifecycle and task.availability in (
            Availability.COMPLETED,
            Availability.DROPPED,
        ):
            return [EDIT_COMPLETED_TASK.format(status=task.availability.value)]
        return []

    # -- Repetition rule warnings -------------------------------------------

    def check_repetition_warnings(
        self,
        end: object | None,
        task: Task,
    ) -> list[str]:
        """Generate warnings for repetition rule edge cases.

        Checks:
        - End date in the past (VALID-05)
        """
        warnings: list[str] = []

        # End date in past
        if isinstance(end, EndByDate) and end.date < date_type.today():
            warnings.append(REPETITION_END_DATE_PAST.format(date=end.date))

        return warnings

    def check_anchor_date_warning(
        self,
        based_on: BasedOn,
        effective_dates: Mapping[str, object],
    ) -> list[str]:
        """Warn if basedOn references an anchor date that isn't set on the task.

        OmniFocus creates the missing anchor date from scratch using the
        completion date and the user's default time settings -- this is
        rarely the user's intent.
        """
        _anchor_map: dict[str, tuple[str, str]] = {
            "due_date": ("due_date", "dueDate"),
            "defer_date": ("defer_date", "deferDate"),
            "planned_date": ("planned_date", "plannedDate"),
        }
        snake_key, camel_display = _anchor_map[based_on.value]
        if effective_dates.get(snake_key) is None:
            return [
                REPETITION_ANCHOR_DATE_MISSING.format(
                    based_on=based_on.value,
                    date_field=camel_display,
                )
            ]
        return []

    def check_from_completion_byday_warning(
        self,
        schedule: Schedule,
        frequency: Frequency,
    ) -> list[str]:
        """Warn when from_completion is combined with day-of-week patterns.

        This combination produces counterintuitive results: same-day skipping,
        grid resets on INTERVAL>=2, and early-completion dismissal.
        See docs/byday-edge-cases.md for details.
        """
        if schedule == Schedule.FROM_COMPLETION and frequency.on_days is not None:
            return [REPETITION_FROM_COMPLETION_BYDAY]
        return []

    def normalize_empty_specialization_fields(
        self,
        frequency: Frequency,
    ) -> tuple[Frequency, list[str]]:
        """Normalize empty specialization fields to None + warning (D-17).

        Handles all 3 fields:
        - weekly with on_days=[] -> on_days=None + warning
        - monthly with on={} -> on=None + warning
        - monthly with on_dates=[] -> on_dates=None + warning

        Returns (possibly-normalized frequency, warnings).
        """
        warnings: list[str] = []
        updates: dict[str, Any] = {}

        if (
            frequency.type == "weekly"
            and frequency.on_days is not None
            and len(frequency.on_days) == 0
        ):
            updates["on_days"] = None
            warnings.append(REPETITION_EMPTY_ON_DAYS)

        _ordinal_fields = ("first", "second", "third", "fourth", "fifth", "last")
        if (
            frequency.type == "monthly"
            and frequency.on is not None
            and all(getattr(frequency.on, f) is None for f in _ordinal_fields)
        ):
            updates["on"] = None
            warnings.append(REPETITION_EMPTY_ON)

        if (
            frequency.type == "monthly"
            and frequency.on_dates is not None
            and len(frequency.on_dates) == 0
        ):
            updates["on_dates"] = None
            warnings.append(REPETITION_EMPTY_ON_DATES)

        if updates:
            frequency = frequency.model_copy(update=updates)

        return (frequency, warnings)

    def merge_frequency(
        self,
        edit_spec: FrequencyEditSpec,
        existing: Frequency,
    ) -> tuple[Frequency, list[str]]:
        """Merge edit spec with existing frequency for same-type updates (D-08, D-11).

        Uses is_set() on edit spec fields to determine provenance:
        UNSET = preserve from existing, None = clear, value = set.

        Handles monthly mutual exclusion: if both on and on_dates end up
        set after merge, auto-clears whichever was NOT explicitly set
        by the agent. If both were agent-set, on takes precedence.

        Returns (merged Frequency, warnings).
        """
        warnings: list[str] = []
        merged: dict[str, Any] = {"type": existing.type}

        # Interval
        merged["interval"] = edit_spec.interval if is_set(edit_spec.interval) else existing.interval

        # Specialization fields: UNSET=preserve, None=clear, value=set
        for field_name in ("on_days", "on", "on_dates"):
            edit_val = getattr(edit_spec, field_name)
            if is_set(edit_val):
                # Spec->Core boundary: model_dump() for nested models
                if isinstance(edit_val, BaseModel):
                    merged[field_name] = edit_val.model_dump(exclude_defaults=True)
                else:
                    merged[field_name] = edit_val
            else:
                merged[field_name] = getattr(existing, field_name)

        # Monthly mutual exclusion (D-08): auto-clear based on provenance
        if existing.type == "monthly":
            has_on = merged.get("on") is not None
            has_on_dates = merged.get("on_dates") is not None
            if has_on and has_on_dates:
                if is_set(edit_spec.on_dates) and not is_set(edit_spec.on):
                    merged["on"] = None
                    warnings.append(REPETITION_AUTO_CLEAR_ON)
                else:
                    merged["on_dates"] = None
                    warnings.append(REPETITION_AUTO_CLEAR_ON_DATES)

        return Frequency.model_validate(merged), warnings

    # -- Tags --------------------------------------------------------------

    async def compute_tag_diff(
        self,
        tag_actions: TagAction,
        current_tags: list[TagRef],
    ) -> tuple[list[str], list[str], list[str]]:
        """Returns (add_ids, remove_ids, warnings)."""
        current_ids = {t.id for t in current_tags}

        has_replace = is_set(tag_actions.replace)
        has_add = is_set(tag_actions.add)
        has_remove = is_set(tag_actions.remove)
        logger.debug("DomainLogic.compute_tag_diff: current_ids=%s", current_ids)
        logger.debug(
            "DomainLogic.compute_tag_diff: has_replace=%s, has_add=%s, has_remove=%s",
            has_replace,
            has_add,
            has_remove,
        )

        tag_names = await self._build_tag_name_map()

        if has_replace:
            final, warns = await self._apply_replace(tag_actions, current_ids, tag_names)
        elif has_add and has_remove:
            final, warns = await self._apply_add_remove(tag_actions, current_ids, tag_names)
        elif has_add:
            final, warns = await self._apply_add(tag_actions, current_ids, tag_names)
        elif has_remove:
            final, warns = await self._apply_remove(tag_actions, current_ids, tag_names)
        else:
            final = current_ids
            warns = []

        return list(final - current_ids), list(current_ids - final), warns

    async def _apply_replace(
        self,
        tag_actions: TagAction,
        current_ids: set[str],
        tag_names: dict[str, str],
    ) -> tuple[set[str], list[str]]:
        """Replace all tags. Returns (final_set, warnings)."""
        assert isinstance(tag_actions.replace, list), (
            f"tag_actions.replace must be list after normalization, got {type(tag_actions.replace)}"
        )
        tag_list = tag_actions.replace
        resolved_ids = await self._resolver.resolve_tags(tag_list) if tag_list else []
        final = set(resolved_ids)

        warns: list[str] = []
        if final == current_ids:
            warns.append(TAGS_ALREADY_MATCH)
        return final, warns

    async def _apply_add(
        self,
        tag_actions: TagAction,
        current_ids: set[str],
        tag_names: dict[str, str],
    ) -> tuple[set[str], list[str]]:
        """Add tags. Returns (final_set, warnings)."""
        assert isinstance(tag_actions.add, list)
        add_resolved = await self._resolver.resolve_tags(tag_actions.add) if tag_actions.add else []
        warns = self._warn_already_on(tag_actions.add, add_resolved, current_ids, tag_names)
        return current_ids | set(add_resolved), warns

    async def _apply_remove(
        self,
        tag_actions: TagAction,
        current_ids: set[str],
        tag_names: dict[str, str],
    ) -> tuple[set[str], list[str]]:
        """Remove tags. Returns (final_set, warnings)."""
        assert isinstance(tag_actions.remove, list)
        remove_resolved = (
            await self._resolver.resolve_tags(tag_actions.remove) if tag_actions.remove else []
        )
        warns = self._warn_not_on(tag_actions.remove, remove_resolved, current_ids, tag_names)
        return current_ids - set(remove_resolved), warns

    async def _apply_add_remove(
        self,
        tag_actions: TagAction,
        current_ids: set[str],
        tag_names: dict[str, str],
    ) -> tuple[set[str], list[str]]:
        """Add and remove tags simultaneously. Returns (final_set, warnings)."""
        assert isinstance(tag_actions.add, list)
        assert isinstance(tag_actions.remove, list)
        add_resolved = await self._resolver.resolve_tags(tag_actions.add) if tag_actions.add else []
        remove_resolved = (
            await self._resolver.resolve_tags(tag_actions.remove) if tag_actions.remove else []
        )
        warns = self._warn_already_on(
            tag_actions.add, add_resolved, current_ids, tag_names
        ) + self._warn_not_on(tag_actions.remove, remove_resolved, current_ids, tag_names)
        return (current_ids | set(add_resolved)) - set(remove_resolved), warns

    @staticmethod
    def _warn_already_on(
        input_names: list[str],
        resolved_ids: list[str],
        current_ids: set[str],
        tag_names: dict[str, str],
    ) -> list[str]:
        """Warn for each resolved tag that is already on the task."""
        warns: list[str] = []
        for i, name in enumerate(input_names):
            if i < len(resolved_ids) and resolved_ids[i] in current_ids:
                display = tag_names.get(resolved_ids[i], name)
                warns.append(TAG_ALREADY_ON_TASK.format(display=display, tag_id=resolved_ids[i]))
        return warns

    @staticmethod
    def _warn_not_on(
        input_names: list[str],
        resolved_ids: list[str],
        current_ids: set[str],
        tag_names: dict[str, str],
    ) -> list[str]:
        """Warn for each resolved tag that is not currently on the task."""
        warns: list[str] = []
        for i, name in enumerate(input_names):
            if i < len(resolved_ids) and resolved_ids[i] not in current_ids:
                display = tag_names.get(resolved_ids[i], name)
                warns.append(TAG_NOT_ON_TASK.format(display=display, tag_id=resolved_ids[i]))
        return warns

    async def _build_tag_name_map(self) -> dict[str, str]:
        """Build tag ID -> name map for warning display names."""
        all_data = await self._repo.get_all()
        return {t.id: t.name for t in all_data.tags}

    # -- Cycle detection ---------------------------------------------------

    async def check_cycle(self, task_id: str, container_id: str) -> None:
        """Raises ValueError if move would create circular reference."""
        logger.debug(
            "DomainLogic.check_cycle: task=%s under container=%s",
            task_id,
            container_id,
        )
        all_data = await self._repo.get_all()
        task_map = {t.id: t for t in all_data.tasks}

        current = container_id
        while current is not None:
            if current == task_id:
                logger.debug("DomainLogic.check_cycle: CYCLE DETECTED")
                msg = CIRCULAR_REFERENCE
                raise ValueError(msg)
            t = task_map.get(current)
            if t is None:
                break
            if t.parent.task is None:
                break
            current = t.parent.task.id

    # -- Move processing ---------------------------------------------------

    async def process_move(
        self,
        move_action: MoveAction,
        task_id: str,
    ) -> dict[str, object]:
        """Resolve, validate, cycle-check a move. Returns move_to dict."""
        logger.debug("DomainLogic.process_move: processing move action")
        position, target_id = self._extract_move_target(move_action)

        if position in ("beginning", "ending"):
            return await self._process_container_move(position, target_id, task_id)
        # position in ("before", "after") -- target_id is always str for anchor moves
        assert target_id is not None
        return await self._process_anchor_move(position, target_id)

    def _extract_move_target(
        self,
        move_action: MoveAction,
    ) -> tuple[str, str | None]:
        """Find which position key is set. Returns (position, target_id)."""
        for key in ("beginning", "ending", "before", "after"):
            value = getattr(move_action, key)
            if is_set(value):
                return key, value
        msg = NO_POSITION_KEY
        raise ValueError(msg)

    async def _process_container_move(
        self,
        position: str,
        container_id: str | None,
        task_id: str,
    ) -> dict[str, object]:
        """Move to beginning/ending of a container (or inbox if None)."""
        if container_id is None:
            return {"position": position, "container_id": None}

        # Resolve container name/ID to canonical ID ($inbox -> None)
        resolved_id = await self._resolver.resolve_container(container_id)
        if resolved_id is None:
            return {"position": position, "container_id": None}

        # If container is a task, check for circular reference
        container_task = await self._repo.get_task(resolved_id)
        if container_task is not None:
            await self.check_cycle(task_id, resolved_id)

        return {"position": position, "container_id": resolved_id}

    async def _process_anchor_move(
        self,
        position: str,
        anchor_id: str,
    ) -> dict[str, object]:
        """Move before/after a sibling task."""
        try:
            resolved_id = await self._resolver.resolve_anchor(anchor_id)
        except EntityTypeMismatchError as exc:
            msg = ENTITY_TYPE_MISMATCH_ANCHOR.format(
                value=exc.value, resolved_type=exc.resolved_type.value
            )
            raise ValueError(msg) from exc
        return {"position": position, "anchor_id": resolved_id}

    # -- No-op detection ---------------------------------------------------

    def detect_early_return(
        self,
        payload: EditTaskRepoPayload,
        task: Task,
        warnings: list[str],
    ) -> EditTaskResult | None:
        """Returns early result if edit is empty or a no-op, else None."""
        if self._is_empty_edit(payload, warnings):
            if warnings:
                return EditTaskResult(
                    success=True,
                    id=payload.id,
                    name=task.name,
                    warnings=warnings,
                )
            return EditTaskResult(
                success=True,
                id=payload.id,
                name=task.name,
                warnings=[EDIT_NO_CHANGES_SPECIFIED],
            )
        if self._all_fields_match(payload, task, warnings):
            # No-op takes priority over status warnings
            filtered = [w for w in warnings if "your changes were applied" not in w]
            if not filtered:
                filtered = [EDIT_NO_CHANGES_DETECTED]
            return EditTaskResult(
                success=True,
                id=payload.id,
                name=task.name,
                warnings=filtered,
            )
        return None

    def _is_empty_edit(self, payload: EditTaskRepoPayload, warnings: list[str]) -> bool:
        """Only 'id' in payload, nothing to change."""
        # Use model_fields_set to detect which fields were explicitly provided,
        # since None can mean "clear" for clearable fields (dates, note, etc.)
        return payload.model_fields_set == {"id"}

    def _all_fields_match(
        self,
        payload: EditTaskRepoPayload,
        task: Task,
        warnings: list[str],
    ) -> bool:
        """Compare each payload field against current task state.

        Returns True if every set field already matches the task's value,
        meaning the edit would be a no-op. May append MOVE_SAME_CONTAINER
        warning to the warnings list.
        """
        _date_keys = {"due_date", "defer_date", "planned_date"}
        field_comparisons: dict[str, object] = {
            "name": task.name,
            "note": task.note,
            "flagged": task.flagged,
            "estimated_minutes": task.estimated_minutes,
            "due_date": task.due_date,
            "defer_date": task.defer_date,
            "planned_date": task.planned_date,
        }

        # Use model_fields_set to detect which fields were explicitly provided,
        # since None can mean "clear" for clearable fields (dates, note, etc.)
        fields_set = payload.model_fields_set

        for key, current_value in field_comparisons.items():
            if key in fields_set:
                payload_val = getattr(payload, key)
                if key in _date_keys:
                    if _to_utc_ts(payload_val) != _to_utc_ts(current_value):
                        return False
                elif payload_val != current_value:
                    return False

        # Check tag changes
        if "add_tag_ids" in fields_set or "remove_tag_ids" in fields_set:
            return False

        # Check lifecycle
        if "lifecycle" in fields_set:
            return False

        # Check repetition_rule
        if "repetition_rule" in fields_set:
            if not self._repetition_rule_matches(payload, task):
                return False
            # Same repetition rule -- no-op, specific warning
            warnings.append(REPETITION_NO_OP)

        # Check move_to
        if "move_to" in fields_set and payload.move_to is not None:
            position = payload.move_to.position
            if position in ("beginning", "ending"):
                container_id = payload.move_to.container_id
                # Extract direct parent ID from tagged ParentRef
                if task.parent.task is not None:
                    current_parent_id = task.parent.task.id
                elif task.parent.project is not None:
                    current_parent_id = task.parent.project.id
                else:
                    current_parent_id = None
                if container_id != current_parent_id:
                    return False
                # Same container -- no-op, but warn
                warnings.append(MOVE_SAME_CONTAINER)
            else:
                # before/after -- can't detect same position
                return False

        return True

    def _repetition_rule_matches(
        self,
        payload: EditTaskRepoPayload,
        task: Task,
    ) -> bool:
        """Compare repetition rule in payload against task's existing rule.

        Returns True if they match (no-op), False if different.
        """
        if payload.repetition_rule is None:
            return task.repetition_rule is None

        existing = task.repetition_rule
        if existing is None:
            return False

        return self.repetition_payload_matches_existing(payload.repetition_rule, existing)

    def repetition_payload_matches_existing(
        self,
        payload: RepetitionRuleRepoPayload,
        existing: RepetitionRule,
    ) -> bool:
        """Check if a repo payload is equivalent to an existing rule."""
        return (
            payload.frequency == existing.frequency
            and payload.schedule == existing.schedule
            and payload.based_on == existing.based_on
            and payload.end == existing.end
        )
