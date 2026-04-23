"""Business rules -- lifecycle, tags, cycle detection, no-op, move processing.

Encapsulates all domain logic that the orchestrator delegates to. Receives
clean Python values (never ``_Unset``), returns results the orchestrator can
merge into the final response.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass
from datetime import UTC, datetime, timedelta
from datetime import date as date_type
from enum import StrEnum
from typing import TYPE_CHECKING, Any, ClassVar, Literal

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
    FILTERED_SUBTREE_WARNING,
    LIFECYCLE_ALREADY_IN_STATE,
    LIFECYCLE_CROSS_STATE,
    LIFECYCLE_REPEATING_COMPLETE,
    LIFECYCLE_REPEATING_DROP,
    MOVE_ALREADY_AT_POSITION,
    NOTE_ALREADY_EMPTY,
    NOTE_APPEND_EMPTY,
    NOTE_REPLACE_ALREADY_CONTENT,
    PARENT_PROJECT_COMBINED_WARNING,
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
from omnifocus_operator.config import SYSTEM_LOCATIONS
from omnifocus_operator.contracts.base import UNSET, _Unset, is_set
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskResult
from omnifocus_operator.contracts.use_cases.list._enums import AvailabilityFilter
from omnifocus_operator.contracts.use_cases.list._validators import parse_duration
from omnifocus_operator.models.enums import Availability, ProjectType, Schedule, TaskType
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
    add_duration,
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
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery
    from omnifocus_operator.models.common import TagRef
    from omnifocus_operator.models.enums import BasedOn, DueSoonSetting
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.service.resolve import Resolver, _HasIdAndName

logger = logging.getLogger(__name__)

__all__ = ["DomainLogic", "ResolvedDateFilters"]


# ---------------------------------------------------------------------------
# Inherited field pairs (D-05): direct field -> inherited field on Task
# ---------------------------------------------------------------------------

_INHERITED_FIELD_PAIRS: tuple[tuple[str, str], ...] = (
    ("flagged", "inherited_flagged"),
    ("due_date", "inherited_due_date"),
    ("defer_date", "inherited_defer_date"),
    ("planned_date", "inherited_planned_date"),
    ("drop_date", "inherited_drop_date"),
    ("completion_date", "inherited_completion_date"),
)

# Per-field aggregation strategies (INHERIT-05 through INHERIT-10)
# See: .research/deep-dives/omnifocus-inheritance-semantics/FINDINGS.md
_MIN_FIELDS: frozenset[str] = frozenset({"inherited_due_date"})
_MAX_FIELDS: frozenset[str] = frozenset({"inherited_defer_date"})
_FIRST_FOUND_FIELDS: frozenset[str] = frozenset(
    {
        "inherited_planned_date",
        "inherited_drop_date",
        "inherited_completion_date",
    }
)
# inherited_flagged uses any-True (separate code path, not date-based)


# ---------------------------------------------------------------------------
# Cross-filter warning fields (WARN-01)
# ---------------------------------------------------------------------------
# Patch fields on ListTasksQuery that prune the subtree when combined with a
# scope filter: each is a task-attribute predicate that can exclude intermediate
# or descendant tasks from the scope's result set. Their presence alongside
# ``project``/``parent`` triggers FILTERED_SUBTREE_WARNING.
#
# Explicitly NOT listed:
#   - ``availability``: non-empty default (REMAINING) -- including it would
#     fire on every scope-filtered query, destroying signal (D-13). Non-default
#     availability IS pruning, but the predicate would need value-awareness to
#     handle that distinction (deferred -- see UAT-57 Case 2).
#   - ``completed``/``dropped``: **inclusion** filters, not pruning. They ADD
#     completed/dropped tasks to the default ``remaining`` bucket; they never
#     exclude tasks already in it. A value like ``{"before": "2020-01-01"}``
#     adds zero tasks (returning baseline unchanged) rather than restricting
#     to zero. Live-verified in UAT-57 Case 1.
_SUBTREE_PRUNING_FIELDS: tuple[str, ...] = (
    "flagged",
    "in_inbox",
    "tags",
    "estimated_minutes_max",
    "search",
    "due",
    "defer",
    "planned",
    "added",
    "modified",
)

# Patch fields on ListTasksQuery that do NOT prune the subtree. Two flavors,
# both legitimate members of this set:
#   - Scope filters (``project``, ``parent``): define WHICH subtree to look
#     at. Not dimensional filters -- they ARE the scope the warning is about.
#   - Inclusion filters (``completed``, ``dropped``): ADD lifecycle states
#     to the default ``remaining`` bucket. Live-verified (UAT-57 Case 1):
#     ``completed={"before": "2020-01-01"}`` returns the baseline unchanged,
#     never restricting it -- so they're purely additive, never pruning.
#
# Kept disjoint from _SUBTREE_PRUNING_FIELDS so every Patch field on
# ListTasksQuery is classified as exactly one of the two, enforced by
# TestSubtreePruningFieldsDrift at CI time.
_NON_SUBTREE_PRUNING_FIELDS: frozenset[str] = frozenset(
    {"project", "parent", "completed", "dropped"},
)


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


def normalize_date_input(value: str, default_time: str = "00:00:00") -> str:
    """Normalize a date input string to naive local ISO format for the bridge.

    This is a product decision: "OmniFocus thinks in local time, so should the API."
    See docs/architecture.md for rationale.

    Three cases:
    - Date-only ("2026-07-15"): append the caller's default_time (user-configured per date field).
      Falls back to midnight ("00:00:00") when no default_time is provided.
    - Naive datetime ("2026-07-15T17:00:00"): pass through as-is (already local by contract)
    - Aware datetime ("2026-07-15T17:00:00Z", "...+01:00"): convert to local, strip tzinfo

    Returns an ISO datetime string suitable for the JS bridge's new Date() constructor.
    """
    if "T" not in value and "t" not in value:
        # Date-only: append user-configured default time for this field
        return f"{value}T{default_time}"

    dt = datetime.fromisoformat(value)
    if dt.tzinfo is not None:
        # Aware: convert to system local, strip tzinfo
        local_dt = dt.astimezone()
        return local_dt.replace(tzinfo=None).isoformat()

    # Naive: already local by contract — pass through
    return value


def _to_utc_ts(val: object) -> object:
    """Normalize a date value to UTC timestamp for comparison, or return as-is.

    After Phase 49, date strings from commands are naive-local (no tzinfo).
    Treat naive datetimes as local time for comparison.
    """
    if val is None:
        return None
    if isinstance(val, datetime):
        if val.tzinfo is not None:
            return val.astimezone(UTC).timestamp()
        # Naive datetime: treat as local, convert to UTC for comparison
        return val.astimezone().astimezone(UTC).timestamp()
    if isinstance(val, str):
        dt = datetime.fromisoformat(val)
        if dt.tzinfo is not None:
            return dt.astimezone(UTC).timestamp()
        # Naive string: treat as local time
        return dt.astimezone().astimezone(UTC).timestamp()
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

    # -- True inheritance walk -------------------------------------------------

    async def compute_true_inheritance(self, tasks: list[Task]) -> list[Task]:
        """Walk parent hierarchy to determine truly inherited fields (D-03).

        For each task, walks ancestor tasks and the containing project (D-01)
        to check whether each inherited field is actually set by an ancestor.
        Self-echoed inherited values (where no ancestor sets the field) are
        reset to their "no inheritance" value (False for flagged, None for dates).

        Each field uses a specific aggregation strategy when multiple ancestors
        contribute: min (due), max (defer), first-found (planned/drop/completion),
        any-True (flagged). See FINDINGS.md for empirical evidence.

        Calls ``self._repo.get_all()`` internally -- cache makes this free (D-03).
        """
        if not tasks:
            return []
        all_data = await self._repo.get_all()
        task_map: dict[str, Task] = {t.id: t for t in all_data.tasks}
        project_map: dict[str, Project] = {p.id: p for p in all_data.projects}
        return [self._walk_one(t, task_map, project_map) for t in tasks]

    def _walk_one(
        self,
        task: Task,
        task_map: dict[str, Task],
        project_map: dict[str, Project],
    ) -> Task:
        """Determine truly inherited field values using per-field aggregation.

        Strategies: min (due_date), max (defer_date), first-found
        (planned/drop/completion), any-True (flagged).
        """
        # Track actual ancestor values (not just presence booleans).
        # inherited_flagged: any-True semantics (False until an ancestor is True).
        ancestor_vals: dict[str, object] = {inh: None for _, inh in _INHERITED_FIELD_PAIRS}
        ancestor_vals["inherited_flagged"] = False

        # Walk ancestor task chain via parent.task.id
        current_id: str | None = task.parent.task.id if task.parent.task else None
        while current_id is not None:
            ancestor = task_map.get(current_id)
            if ancestor is None:
                break
            for direct, inherited in _INHERITED_FIELD_PAIRS:
                val = getattr(ancestor, direct)
                if direct == "flagged":
                    # any-True: once True, stays True
                    if val is True:
                        ancestor_vals[inherited] = True
                elif val is not None:
                    cur = ancestor_vals[inherited]
                    if inherited in _FIRST_FOUND_FIELDS:
                        # Override family: take first non-null, skip once found
                        if cur is None:
                            ancestor_vals[inherited] = val
                    elif inherited in _MAX_FIELDS:
                        # Constraint (max): latest block wins
                        if cur is None or val > cur:
                            ancestor_vals[inherited] = val
                    else:
                        # Constraint (min): tightest deadline wins (due_date)
                        if cur is None or val < cur:
                            ancestor_vals[inherited] = val
            current_id = ancestor.parent.task.id if ancestor.parent.task else None

        # Check containing project as final ancestor (D-01)
        # Use task.project.id (not task.parent.project.id) -- Pitfall 3
        project = project_map.get(task.project.id)
        if project is not None:
            for direct, inherited in _INHERITED_FIELD_PAIRS:
                if not hasattr(project, direct):
                    continue
                val = getattr(project, direct)
                if direct == "flagged":
                    if val is True:
                        ancestor_vals[inherited] = True
                elif val is not None:
                    cur = ancestor_vals[inherited]
                    if inherited in _FIRST_FOUND_FIELDS:
                        if cur is None:
                            ancestor_vals[inherited] = val
                    elif inherited in _MAX_FIELDS:
                        if cur is None or val > cur:
                            ancestor_vals[inherited] = val
                    else:
                        if cur is None or val < cur:
                            ancestor_vals[inherited] = val

        # Build update dict: always set all 6 inherited fields to computed
        # ancestor values. Replaces OF's effective value with the true
        # ancestor value (or the "no inheritance" default).
        updates: dict[str, object] = {}
        for _, inherited in _INHERITED_FIELD_PAIRS:
            updates[inherited] = ancestor_vals[inherited]

        return task.model_copy(update=updates)

    # -- Derived presence flags (Phase 56-03, FLAG-04 + FLAG-05) --------------

    def enrich_task_presence_flags(self, task: Task) -> Task:
        """Compute task-side derived flags from structural fields.

        - ``is_sequential``       = ``task.type == TaskType.SEQUENTIAL`` (FLAG-04)
        - ``depends_on_children`` = ``has_children and not completes_with_children`` (FLAG-05)

        Phase 56-08 hoisted ``is_sequential`` to ActionableEntity — it now
        applies to both tasks and projects. ``depends_on_children`` stays
        tasks-only (projects are always containers; the semantic does not
        apply). The domain owns this derivation so repositories stay
        ignorant of product decisions.
        """
        is_sequential = task.type == TaskType.SEQUENTIAL
        depends_on_children = task.has_children and not task.completes_with_children
        return task.model_copy(
            update={
                "is_sequential": is_sequential,
                "depends_on_children": depends_on_children,
            }
        )

    def enrich_project_presence_flags(self, project: Project) -> Project:
        """Compute project-side derived flag from structural fields (Phase 56-08).

        - ``is_sequential`` = ``project.type == ProjectType.SEQUENTIAL`` (FLAG-04)

        Mirrors ``enrich_task_presence_flags`` for the project read path.
        ``dependsOnChildren`` (FLAG-05) does not apply to projects — they
        are always containers, so the "real unit of work waiting on
        children" semantic is not meaningful. ``singleActions`` projects
        resolve to is_sequential=False (HIER-05 precedence: only the final
        assembled type of SEQUENTIAL yields True).
        """
        is_sequential = project.type == ProjectType.SEQUENTIAL
        return project.model_copy(update={"is_sequential": is_sequential})

    def assemble_project_type(
        self,
        *,
        sequential: bool,
        contains_singleton_actions: bool,
    ) -> ProjectType:
        """HIER-05 precedence: ``singleActions`` beats ``sequential``.

        Truth table:
        - (True,  True)  -> SINGLE_ACTIONS (precedence)
        - (False, True)  -> SINGLE_ACTIONS
        - (True,  False) -> SEQUENTIAL
        - (False, False) -> PARALLEL

        Kept at the domain layer even though Phase 56-02 currently computes
        ``ProjectType`` at the repository layer for cross-path self-check
        ergonomics. The domain copy is the lock on HIER-05 precedence and
        is reused by tests; if the repository computation is relocated to
        the service layer in a later plan, this is the single source of
        truth it should call.
        """
        if contains_singleton_actions:
            return ProjectType.SINGLE_ACTIONS
        if sequential:
            return ProjectType.SEQUENTIAL
        return ProjectType.PARALLEL

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

            # "all" shortcut -- lifecycle expansion only, no date bounds
            if isinstance(value, StrEnum) and value.value == "all":
                continue

            # "soon" without due_soon_setting -- domain owns fallback
            if isinstance(value, StrEnum) and value.value == "soon" and due_soon_setting is None:
                # Defensive: preferences module should always provide a value.
                # Fall back to OmniFocus factory default (TWO_DAYS = 2 days, calendar-aligned).
                midnight = now.replace(hour=0, minute=0, second=0, microsecond=0)
                bounds[field_name] = ResolvedDateBounds(
                    after=midnight,
                    before=midnight + timedelta(days=2),
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

            # Defer hint: every defer filter gets a hint. Defer is one of
            # four blocking reasons -- the agent almost always wants
            # availability: 'available' or 'blocked' instead.
            if field_name == "defer":
                resolved = bounds[field_name]
                entirely_future = resolved.after is not None and resolved.after >= now
                if entirely_future:
                    warnings.append(DEFER_AFTER_NOW_HINT)
                else:
                    warnings.append(DEFER_BEFORE_NOW_HINT)

        return ResolvedDateFilters(
            bounds=bounds,
            lifecycle_additions=lifecycle_additions,
            warnings=warnings,
        )

    # -- Availability expansion ------------------------------------------------

    def expand_availability(
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

    def expand_review_due(self, value: str, now: datetime) -> datetime:
        """Expand a review-due duration string to a concrete datetime threshold."""
        if value == "now":
            return now
        count, unit = parse_duration(value)
        return add_duration(now, count, unit)

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

    # -- Cross-filter warning checks (WARN-01, WARN-03) --------------------

    def check_filtered_subtree(self, query: ListTasksQuery) -> list[str]:
        """WARN-01: scope filter combined with any subtree-pruning filter.

        Fires when ``(project or parent)`` is set AND at least one of the
        fields in ``_SUBTREE_PRUNING_FIELDS`` is set.
        """
        if not (is_set(query.project) or is_set(query.parent)):
            return []
        if any(is_set(getattr(query, f)) for f in _SUBTREE_PRUNING_FIELDS):
            return [FILTERED_SUBTREE_WARNING]
        return []

    def check_parent_project_combined(self, query: ListTasksQuery) -> list[str]:
        """WARN-03: both ``project`` and ``parent`` filters set together.

        Presence-based (D-13): fires independent of whether the resolved
        scope-set intersection is empty or not. The emptiness question is a
        runtime outcome at the repo layer; this warning is a soft heads-up at
        the query-inspection layer.
        """
        if is_set(query.project) and is_set(query.parent):
            return [PARENT_PROJECT_COMBINED_WARNING]
        return []

    # -- Clear-intent normalization ----------------------------------------

    def normalize_clear_intents(self, command: EditTaskCommand) -> EditTaskCommand:
        """Normalize null-means-clear fields before payload construction.

        OmniFocus semantics:
        - tags.replace=None -> tags.replace=[] (empty list clears all tags)

        Centralizes this pattern so PayloadBuilder stays pure construction.
        """
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

    # -- Note action -------------------------------------------------------

    def process_note_action(
        self,
        command: EditTaskCommand,
        task: Task,
    ) -> tuple[str | _Unset, bool, list[str]]:
        """Compose note state from actions.note.

        Returns (new_value_or_UNSET, should_skip_bridge, warnings):
        - UNSET => leave note absent from the bridge payload (no-op at this layer)
        - str  => send this string to the bridge (empty string clears the note)
        - skip => True when the whole note operation is a no-op

        D-04 N1: empty OR whitespace-only append -> no-op with NOTE_APPEND_EMPTY warning.
            OmniFocus normalizes whitespace-only notes to empty and trims trailing
            whitespace on write (verified via OmniJS UAT Phase 55), so a whitespace-only
            append is invisible to the user end-to-end. Treating it as N1 matches
            observable behavior and gives agents helpful feedback.
        D-05 N2: identical replace -> no-op with NOTE_REPLACE_ALREADY_CONTENT
        D-06 N3: clear on already-empty note -> no-op with NOTE_ALREADY_EMPTY
        D-08/D-09: strip-and-check; whitespace-only existing note treated as empty
        """
        warnings: list[str] = []

        # No note action -> skip
        if not is_set(command.actions):
            return UNSET, True, warnings
        actions = command.actions
        if not is_set(actions.note):
            return UNSET, True, warnings

        note_action = actions.note
        existing = task.note or ""
        existing_stripped = existing.strip()

        # Append branch
        if is_set(note_action.append):
            append_text = note_action.append
            # N1: empty or whitespace-only append -> no-op (see docstring D-04)
            if append_text.strip() == "":
                warnings.append(NOTE_APPEND_EMPTY)
                return UNSET, True, warnings
            # NOTE-04 / D-09: empty or whitespace-only note -> set directly (no separator)
            if existing_stripped == "":
                return append_text, False, warnings
            # Normal concatenation
            return existing + "\n" + append_text, False, warnings

        # Replace branch (NoteAction validator guarantees either append or replace is set)
        replace_val = note_action.replace
        clearing = replace_val is None or replace_val == ""
        target = replace_val if replace_val is not None else ""

        # N3 takes precedence over N2 when both match (Pitfall 3)
        if clearing and existing_stripped == "":
            warnings.append(NOTE_ALREADY_EMPTY)
            return UNSET, True, warnings

        # N2: identical content
        if target == existing:
            warnings.append(NOTE_REPLACE_ALREADY_CONTENT)
            return UNSET, True, warnings

        # Real replace (includes clear of non-empty: target is "")
        return target, False, warnings

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

    def collect_repetition_warnings(
        self,
        end: object | None,
        based_on: BasedOn,
        effective_dates: Mapping[str, object],
        schedule: Schedule,
        frequency: Frequency,
    ) -> list[str]:
        """Collect all repetition rule warnings in one call.

        Checks:
        - End date in the past (VALID-05)
        - Anchor date not set for basedOn field
        - from_completion + day-of-week edge cases
        """
        warnings: list[str] = []
        warnings.extend(self.check_repetition_warnings(end))
        warnings.extend(self.check_anchor_date_warning(based_on, effective_dates))
        warnings.extend(self.check_from_completion_byday_warning(schedule, frequency))
        return warnings

    def check_repetition_warnings(self, end: object | None) -> list[str]:
        """Check for end date in the past (VALID-05)."""
        if isinstance(end, EndByDate) and end.date < date_type.today():
            return [REPETITION_END_DATE_PAST.format(date=end.date)]
        return []

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
        assert len(resolved_ids) == len(input_names), (
            f"resolve_tags must return one ID per input; "
            f"got {len(resolved_ids)} for {len(input_names)} inputs"
        )
        warns: list[str] = []
        for i, name in enumerate(input_names):
            if resolved_ids[i] in current_ids:
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
        assert len(resolved_ids) == len(input_names), (
            f"resolve_tags must return one ID per input; "
            f"got {len(resolved_ids)} for {len(input_names)} inputs"
        )
        warns: list[str] = []
        for i, name in enumerate(input_names):
            if resolved_ids[i] not in current_ids:
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
        """Move to beginning/ending of a container (or inbox if None).

        Translates beginning/ending to before/after when the target container
        has children (D-06, D-07). OmniFocus silently no-ops on same-container
        beginning/ending moves -- this translation makes them work.
        """

        inbox_id = SYSTEM_LOCATIONS["inbox"].id

        if container_id is None:
            resolved_id = None
            effective_parent_id = inbox_id
        else:
            # Resolve container name/ID to canonical ID ($inbox -> None)
            resolved_id = await self._resolver.resolve_container(container_id)
            if resolved_id is None:
                effective_parent_id = inbox_id
            else:
                effective_parent_id = resolved_id
                # If container is a task, check for circular reference.
                # check_cycle walks the ancestor chain and terminates at project-level
                # parents (t.parent.task is None), so it correctly guards against
                # task-under-task cycles. Cross-container cycles (task A moved under
                # project B that contains A's ancestor) are structurally impossible:
                # OmniFocus does not allow project nesting.
                container_task = await self._repo.get_task(resolved_id)
                if container_task is not None:
                    await self.check_cycle(task_id, resolved_id)

        # Translate beginning/ending to before/after when container has children (D-06, D-07)
        edge: Literal["first", "last"] = "first" if position == "beginning" else "last"
        edge_child_id = await self._repo.get_edge_child_id(effective_parent_id, edge)

        if edge_child_id is not None:
            # Container has children -- translate to anchor-based move
            translated_position = "before" if position == "beginning" else "after"
            return {"position": translated_position, "anchor_id": edge_child_id}

        # Empty container -- direct moveTo (D-07)
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
                    status="success",
                    id=payload.id,
                    name=task.name,
                    warnings=warnings,
                )
            return EditTaskResult(
                status="success",
                id=payload.id,
                name=task.name,
                warnings=[EDIT_NO_CHANGES_SPECIFIED],
            )
        if self._all_fields_match(payload, task, warnings):
            # No-op takes priority over status warnings
            # Prefix derived from template constant -- stable regardless of {status} value
            _prefix = EDIT_COMPLETED_TASK.split("{")[0]
            filtered = [w for w in warnings if not w.startswith(_prefix)]
            if not filtered:
                filtered = [EDIT_NO_CHANGES_DETECTED]
            return EditTaskResult(
                status="success",
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
        meaning the edit would be a no-op. Detects translated move no-ops
        via anchor_id == task_id (D-12, D-13).
        """
        _date_keys = {"due_date", "defer_date", "planned_date"}
        # Plan 56-06: completes_with_children + type participate in no-op
        # detection so a patch like `completes_with_children=False` on a task
        # whose stored value is True actually flows to the bridge (not
        # short-circuited as a no-op).
        field_comparisons: dict[str, object] = {
            "name": task.name,
            "note": task.note,
            "flagged": task.flagged,
            "estimated_minutes": task.estimated_minutes,
            "due_date": task.due_date,
            "defer_date": task.defer_date,
            "planned_date": task.planned_date,
            "completes_with_children": task.completes_with_children,
            "type": task.type.value,
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
            move = payload.move_to
            if move.anchor_id is not None:
                # Translated move (before/after with anchor)
                # Self-reference = already in position (D-12, D-13)
                if move.anchor_id != payload.id:
                    return False
                # anchor_id == task_id: no-op
                # Determine original position for the warning message
                original_position = "beginning" if move.position == "before" else "ending"
                warnings.append(MOVE_ALREADY_AT_POSITION.format(position=original_position))
            elif move.position in ("beginning", "ending"):
                # Untranslated move (empty container) -- compare container
                container_id = move.container_id
                if task.parent.task is not None:
                    current_parent_id = task.parent.task.id
                elif task.parent.project is not None:
                    current_parent_id = task.parent.project.id
                else:
                    current_parent_id = None
                if container_id != current_parent_id:
                    return False
                # Same empty container -> no-op (task is alone, already at beginning AND ending)
                warnings.append(MOVE_ALREADY_AT_POSITION.format(position=move.position))
            else:
                # before/after without anchor_id is unreachable after translation
                assert False, (  # noqa: B011
                    f"_all_fields_match: before/after move with no anchor_id "
                    f"(payload.id={payload.id}); this should never happen after "
                    f"_process_container_move translation"
                )

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
