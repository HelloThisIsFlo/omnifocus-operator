"""Business rules -- lifecycle, tags, cycle detection, no-op, move processing.

Encapsulates all domain logic that the orchestrator delegates to. Receives
clean Python values (never ``_Unset``), returns results the orchestrator can
merge into the final response.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING

from omnifocus_operator.models.enums import Availability
from omnifocus_operator.warnings import (
    EDIT_COMPLETED_TASK,
    EDIT_NO_CHANGES_DETECTED,
    EDIT_NO_CHANGES_SPECIFIED,
    LIFECYCLE_ALREADY_IN_STATE,
    LIFECYCLE_CROSS_STATE,
    LIFECYCLE_REPEATING_COMPLETE,
    LIFECYCLE_REPEATING_DROP,
    MOVE_SAME_CONTAINER,
    TAG_ALREADY_ON_TASK,
    TAG_NOT_ON_TASK,
    TAGS_ALREADY_MATCH,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.common import MoveAction, TagAction
    from omnifocus_operator.contracts.protocols import Repository
    from omnifocus_operator.contracts.use_cases.edit_task import (
        EditTaskCommand,
        EditTaskRepoPayload,
        EditTaskResult,
    )
    from omnifocus_operator.models.common import TagRef
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.service.resolve import Resolver

logger = logging.getLogger("omnifocus_operator")

__all__ = ["DomainLogic"]


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
    """Applies business rules for the edit-task pipeline."""

    def __init__(self, repo: Repository, resolver: Resolver) -> None:
        self._repo = repo
        self._resolver = resolver

    # -- Clear-intent normalization ----------------------------------------

    def normalize_clear_intents(self, command: EditTaskCommand) -> EditTaskCommand:
        """Normalize null-means-clear fields before payload construction.

        OmniFocus semantics:
        - note=None -> note='' (bridge expects empty string to clear)
        - tags.replace=None -> tags.replace=[] (empty list clears all tags)

        Centralizes this pattern so PayloadBuilder stays pure construction.
        """
        from omnifocus_operator.contracts.base import _Unset

        # note: None means "clear the note" -> empty string for bridge
        if not isinstance(command.note, _Unset) and command.note is None:
            command = command.model_copy(update={"note": ""})

        # tags.replace: None means "clear all tags" -> empty list
        if not isinstance(command.actions, _Unset) and not isinstance(command.actions.tags, _Unset):
            tag_actions = command.actions.tags
            if not isinstance(tag_actions.replace, _Unset) and tag_actions.replace is None:
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

    # -- Tags --------------------------------------------------------------

    async def compute_tag_diff(
        self,
        tag_actions: TagAction,
        current_tags: list[TagRef],
    ) -> tuple[list[str], list[str], list[str]]:
        """Returns (add_ids, remove_ids, warnings)."""
        from omnifocus_operator.contracts.base import _Unset

        current_ids = {t.id for t in current_tags}

        has_replace = not isinstance(tag_actions.replace, _Unset)
        has_add = not isinstance(tag_actions.add, _Unset)
        has_remove = not isinstance(tag_actions.remove, _Unset)
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

        warns: list[str] = []
        for i, _tag_name in enumerate(tag_actions.add):
            if i < len(add_resolved) and add_resolved[i] in current_ids:
                display = tag_names.get(add_resolved[i], _tag_name)
                warns.append(TAG_ALREADY_ON_TASK.format(display=display, tag_id=add_resolved[i]))

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

        warns: list[str] = []
        for i, _tag_name in enumerate(tag_actions.remove):
            if i < len(remove_resolved) and remove_resolved[i] not in current_ids:
                display = tag_names.get(remove_resolved[i], _tag_name)
                warns.append(TAG_NOT_ON_TASK.format(display=display, tag_id=remove_resolved[i]))

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

        warns: list[str] = []
        for i, _tag_name in enumerate(tag_actions.add):
            if i < len(add_resolved) and add_resolved[i] in current_ids:
                display = tag_names.get(add_resolved[i], _tag_name)
                warns.append(TAG_ALREADY_ON_TASK.format(display=display, tag_id=add_resolved[i]))
        for i, _tag_name in enumerate(tag_actions.remove):
            if i < len(remove_resolved) and remove_resolved[i] not in current_ids:
                display = tag_names.get(remove_resolved[i], _tag_name)
                warns.append(TAG_NOT_ON_TASK.format(display=display, tag_id=remove_resolved[i]))

        return (current_ids | set(add_resolved)) - set(remove_resolved), warns

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
                msg = "Cannot move task: would create circular reference"
                raise ValueError(msg)
            t = task_map.get(current)
            if t is None or t.parent is None:
                break
            if t.parent.type != "task":
                break
            current = t.parent.id

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
        from omnifocus_operator.contracts.base import _Unset

        for key in ("beginning", "ending", "before", "after"):
            value = getattr(move_action, key)
            if not isinstance(value, _Unset):
                return key, value
        msg = "No position key set on move action"
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

        # Verify container exists (project or task)
        await self._resolver.resolve_parent(container_id)

        # If container is a task, check for circular reference
        container_task = await self._repo.get_task(container_id)
        if container_task is not None:
            await self.check_cycle(task_id, container_id)

        return {"position": position, "container_id": container_id}

    async def _process_anchor_move(
        self,
        position: str,
        anchor_id: str,
    ) -> dict[str, object]:
        """Move before/after a sibling task."""
        try:
            await self._resolver.resolve_task(anchor_id)
        except ValueError:
            msg = f"Anchor task not found: {anchor_id}"
            raise ValueError(msg) from None
        return {"position": position, "anchor_id": anchor_id}

    # -- No-op detection ---------------------------------------------------

    def detect_early_return(
        self,
        payload: EditTaskRepoPayload,
        task: Task,
        warnings: list[str],
    ) -> EditTaskResult | None:
        """Returns early result if edit is empty or a no-op, else None."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskResult

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

        # Check move_to
        if "move_to" in fields_set and payload.move_to is not None:
            position = payload.move_to.position
            if position in ("beginning", "ending"):
                container_id = payload.move_to.container_id
                current_parent_id = task.parent.id if task.parent else None
                if container_id != current_parent_id:
                    return False
                # Same container -- no-op, but warn
                warnings.append(MOVE_SAME_CONTAINER)
            else:
                # before/after -- can't detect same position
                return False

        return True
