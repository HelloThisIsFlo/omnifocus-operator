"""Service module -- primary API surface for the MCP server.

The service layer provides the primary API surface for the MCP server.
Currently a simple delegation to ``Repository``; future phases may add
orchestration, caching policies, or multi-repository coordination.
"""

from __future__ import annotations

import logging
from datetime import UTC, datetime
from typing import TYPE_CHECKING, NoReturn

from omnifocus_operator.models.enums import Availability

if TYPE_CHECKING:
    from omnifocus_operator.models.common import TagRef
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.models.write import (
        MoveToSpec,
        TagActionSpec,
        TaskCreateResult,
        TaskCreateSpec,
        TaskEditResult,
        TaskEditSpec,
    )
    from omnifocus_operator.repository import Repository

__all__ = ["ErrorOperatorService", "OperatorService"]

logger = logging.getLogger("omnifocus_operator")


def _to_utc_ts(val: object) -> object:
    """Normalize a date value to UTC timestamp for comparison, or return as-is."""
    if val is None:
        return None
    if isinstance(val, datetime):
        return val.astimezone(UTC).timestamp()
    if isinstance(val, str):
        return datetime.fromisoformat(val).astimezone(UTC).timestamp()
    return val


class OperatorService:
    """Service layer that delegates to the Repository protocol.

    Parameters
    ----------
    repository:
        Any ``Repository`` implementation (e.g. ``BridgeRepository``,
        ``InMemoryRepository``) that provides ``get_all()``.
    """

    def __init__(self, repository: Repository) -> None:
        self._repository = repository

    async def get_all_data(self) -> AllEntities:
        """Return all OmniFocus entities from the repository.

        Delegates directly to ``repository.get_all()``.  Any errors
        from the repository (bridge errors, validation errors, mtime
        errors) propagate to the caller unchanged.
        """
        logger.debug("OperatorService.get_all_data: delegating to repository")
        return await self._repository.get_all()

    async def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        logger.debug("OperatorService.get_task: id=%s", task_id)
        return await self._repository.get_task(task_id)

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        logger.debug("OperatorService.get_project: id=%s", project_id)
        return await self._repository.get_project(project_id)

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
        logger.debug("OperatorService.get_tag: id=%s", tag_id)
        return await self._repository.get_tag(tag_id)

    async def add_task(self, spec: TaskCreateSpec) -> TaskCreateResult:
        """Create a task with validation and delegation to repository.

        Validates name, resolves parent (project or task), resolves tag
        names to IDs, then delegates to repository.add_task.

        Raises
        ------
        ValueError
            If name is empty, parent not found, or tag resolution fails.
        """
        logger.debug(
            "OperatorService.add_task: name=%s, parent=%s, tags=%s",
            spec.name,
            spec.parent,
            spec.tags,
        )

        # Validate name
        if not spec.name or not spec.name.strip():
            msg = "Task name is required"
            raise ValueError(msg)

        # Resolve parent
        if spec.parent is not None:
            await self._resolve_parent(spec.parent)

        # Resolve tags
        resolved_tag_ids: list[str] | None = None
        if spec.tags is not None:
            resolved_tag_ids = await self._resolve_tags(spec.tags)
            logger.debug(
                "OperatorService.add_task: resolved %d tags to IDs: %s",
                len(resolved_tag_ids),
                resolved_tag_ids,
            )

        logger.debug("OperatorService.add_task: delegating to repository")
        return await self._repository.add_task(spec, resolved_tag_ids=resolved_tag_ids)

    async def edit_task(self, spec: TaskEditSpec) -> TaskEditResult:
        """Edit a task with validation and delegation to repository.

        Validates task existence, name, resolves tags and parent/moveTo,
        checks for cycles, builds minimal payload, and delegates to
        repository.edit_task.

        Raises
        ------
        ValueError
            If task not found, name empty, parent not found, anchor not
            found, or move would create a cycle.
        """
        from omnifocus_operator.models.write import TaskEditResult, _Unset

        # 1. Verify task exists
        logger.debug("OperatorService.edit_task: id=%s, fetching current state", spec.id)
        task = await self._repository.get_task(spec.id)
        if task is None:
            msg = f"Task not found: {spec.id}"
            raise ValueError(msg)
        logger.debug(
            "OperatorService.edit_task: task found, name=%s, current_tags=%d",
            task.name,
            len(task.tags),
        )

        warnings: list[str] = []

        # 2. Handle actions block detection
        has_actions = not isinstance(spec.actions, _Unset)

        # 2a. Process lifecycle BEFORE status warning
        lifecycle_handled = False
        has_lifecycle = (
            has_actions
            and not isinstance(spec.actions, _Unset)
            and not isinstance(spec.actions.lifecycle, _Unset)
        )

        # 3. Build payload with only non-UNSET fields
        payload: dict[str, object] = {"id": spec.id}

        if has_lifecycle:
            assert not isinstance(spec.actions, _Unset)
            lifecycle_action: str = spec.actions.lifecycle  # type: ignore[assignment]
            should_call, lifecycle_warnings = self._process_lifecycle(lifecycle_action, task)
            warnings.extend(lifecycle_warnings)
            lifecycle_handled = True
            if should_call:
                payload["lifecycle"] = lifecycle_action

        # Warn about editing completed/dropped tasks (only if lifecycle not handled)
        if not lifecycle_handled and task.availability in (
            Availability.COMPLETED,
            Availability.DROPPED,
        ):
            status = task.availability.value
            warnings.append(
                f"This task is {status} -- your changes were applied, "
                f"but please confirm with the user that they intended to edit a {status} task."
            )

        # 4. Validate name (if provided)
        if not isinstance(spec.name, _Unset) and (not spec.name or not spec.name.strip()):
            msg = "Task name cannot be empty"
            raise ValueError(msg)

        # 5. Build payload fields
        # Simple fields: (spec_attr, payload_key)
        _simple_fields = [
            ("name", "name"),
            ("note", "note"),
            ("flagged", "flagged"),
            ("estimated_minutes", "estimatedMinutes"),
        ]
        for attr, key in _simple_fields:
            value = getattr(spec, attr)
            if not isinstance(value, _Unset):
                payload[key] = value

        # null-means-clear: note=None -> "" (OmniFocus rejects null notes)
        if "note" in payload and payload["note"] is None:
            payload["note"] = ""

        # Date fields: serialize to ISO string if not None
        _date_fields = [
            ("due_date", "dueDate"),
            ("defer_date", "deferDate"),
            ("planned_date", "plannedDate"),
        ]
        for attr, key in _date_fields:
            value = getattr(spec, attr)
            if not isinstance(value, _Unset):
                payload[key] = value.isoformat() if value is not None else None

        # 4b. Handle tags via diff computation
        has_tag_actions = (
            has_actions
            and not isinstance(spec.actions, _Unset)
            and not isinstance(spec.actions.tags, _Unset)
        )
        if has_tag_actions:
            assert not isinstance(spec.actions, _Unset)
            tag_actions: TagActionSpec = spec.actions.tags  # type: ignore[assignment]
            add_ids, remove_ids, tag_warnings = await self._compute_tag_diff(tag_actions, task.tags)
            logger.debug("OperatorService.edit_task: current_tags=%s", [t.id for t in task.tags])
            logger.debug(
                "OperatorService.edit_task: tag diff add_ids=%s, remove_ids=%s", add_ids, remove_ids
            )
            if add_ids:
                payload["addTagIds"] = add_ids
            if remove_ids:
                payload["removeTagIds"] = remove_ids
            logger.debug("OperatorService.edit_task: payload keys=%s", list(payload.keys()))
            warnings.extend(tag_warnings)

        # 5. Handle moveTo
        has_move = (
            has_actions
            and not isinstance(spec.actions, _Unset)
            and not isinstance(spec.actions.move, _Unset)
        )
        if has_move:
            logger.debug("OperatorService.edit_task: processing move action")
            assert not isinstance(spec.actions, _Unset)
            move_to_spec: MoveToSpec = spec.actions.move  # type: ignore[assignment]
            move_to_dict: dict[str, object] = {}

            # Find which key is set
            for position_key in ("beginning", "ending"):
                value = getattr(move_to_spec, position_key)
                if not isinstance(value, _Unset):
                    if value is None:
                        # Move to inbox
                        move_to_dict = {"position": position_key, "containerId": None}
                    else:
                        # Resolve container
                        await self._resolve_parent(value)
                        move_to_dict = {"position": position_key, "containerId": value}

                        # Cycle detection: check if container is a task
                        container_task = await self._repository.get_task(value)
                        if container_task is not None:
                            await self._check_cycle(spec.id, value)

            for position_key in ("before", "after"):
                value = getattr(move_to_spec, position_key)
                if not isinstance(value, _Unset):
                    # Validate anchor exists
                    anchor = await self._repository.get_task(value)
                    if anchor is None:
                        msg = f"Anchor task not found: {value}"
                        raise ValueError(msg)
                    move_to_dict = {"position": position_key, "anchorId": value}

            payload["moveTo"] = move_to_dict

        # 6. Early return for completely empty edit (no fields, no tags, no move)
        if len(payload) == 1 and not warnings:  # Only "id" key, no action-specific warnings
            logger.debug("OperatorService.edit_task: empty edit (no fields), returning early")
            return TaskEditResult(
                success=True,
                id=spec.id,
                name=task.name,
                warnings=[
                    "No changes specified -- if you intended to change fields, "
                    "include them in the request"
                ],
            )
        if len(payload) == 1 and warnings:
            # Action-specific warnings already present (e.g. lifecycle no-op, tag no-op)
            logger.debug(
                "OperatorService.edit_task: empty edit with action warnings, returning early"
            )
            return TaskEditResult(
                success=True,
                id=spec.id,
                name=task.name,
                warnings=warnings,
            )

        # 7. Generic no-op detection: compare payload against current task state
        is_noop = True
        _date_keys = {"dueDate", "deferDate", "plannedDate"}
        field_comparisons: dict[str, object] = {
            "name": task.name,
            "note": task.note,
            "flagged": task.flagged,
            "estimatedMinutes": task.estimated_minutes,
            "dueDate": task.due_date,
            "deferDate": task.defer_date,
            "plannedDate": task.planned_date,
        }
        for key, current_value in field_comparisons.items():
            if key in payload:
                payload_val = payload[key]
                if key in _date_keys:
                    # Normalize both sides to UTC timestamp for tz-aware comparison
                    if _to_utc_ts(payload_val) != _to_utc_ts(current_value):
                        is_noop = False
                        break
                elif payload_val != current_value:
                    is_noop = False
                    break

        # Check tag changes: if addTagIds or removeTagIds present, it's not a no-op
        if is_noop and ("addTagIds" in payload or "removeTagIds" in payload):
            is_noop = False

        # Check lifecycle: if lifecycle is in payload, it's not a no-op
        if is_noop and "lifecycle" in payload:
            is_noop = False

        # Check moveTo
        if is_noop and "moveTo" in payload:
            move_data = payload["moveTo"]
            assert isinstance(move_data, dict)
            position = move_data.get("position")
            if position in ("beginning", "ending"):
                container_id = move_data.get("containerId")
                current_parent_id = task.parent.id if task.parent else None
                if container_id == current_parent_id:
                    warnings.append(
                        "Task is already in this container. OmniFocus API "
                        "limitation: 'beginning'/'ending' moves within the "
                        "same container may not change position. Workaround: "
                        "use 'before' or 'after' with a sibling task ID to "
                        "control ordering."
                    )
                    # is_noop stays True -- same container
                else:
                    is_noop = False
            else:
                # before/after -- can't detect same position
                is_noop = False

        if is_noop:
            if not warnings:
                # Genuine field-level no-op -- add generic warning
                warnings.append(
                    "No changes detected -- the task already has these values. "
                    "If you don't want to change a field, omit it from the request."
                )
            # Return early -- action-specific warnings already present, or generic added
            logger.debug(
                "OperatorService.edit_task: no-op detected, all values match current state"
            )
            return TaskEditResult(
                success=True,
                id=spec.id,
                name=task.name,
                warnings=warnings,
            )

        # 8. Delegate to repository
        logger.debug(
            "OperatorService.edit_task: delegating to repository, payload keys=%s",
            list(payload.keys()),
        )
        result = await self._repository.edit_task(payload)

        # 9. Return result
        return TaskEditResult(
            success=True,
            id=result["id"],
            name=result["name"],
            warnings=warnings or None,
        )

    def _process_lifecycle(self, lifecycle_action: str, task: Task) -> tuple[bool, list[str]]:
        """Process a lifecycle action against the task's current state.

        Returns (should_call_bridge, warnings).
        - No-op (already in target state): False + no-op warning
        - Cross-state (completed->dropped or vice versa): True + cross-state warning
        - Fresh (available->completed/dropped): True + no warnings (unless repeating)
        - Repeating task: appends occurrence-specific warning
        """
        warnings: list[str] = []

        target_availability = (
            Availability.COMPLETED if lifecycle_action == "complete" else Availability.DROPPED
        )

        # No-op check: already in target state
        if task.availability == target_availability:
            state_word = "complete" if lifecycle_action == "complete" else "dropped"
            warnings.append(
                f"Task is already {state_word} -- nothing changed. Omit actions.lifecycle to skip."
            )
            return False, warnings

        # Cross-state check: transitioning between completed and dropped
        if task.availability in (Availability.COMPLETED, Availability.DROPPED):
            prior_state = task.availability.value
            new_state = "complete" if lifecycle_action == "complete" else "dropped"
            warnings.append(
                f"Task was already {prior_state} -- lifecycle action applied, "
                f"task is now {new_state}. Confirm with user that this was intended."
            )

        # Repeating task check
        if task.repetition_rule is not None:
            if lifecycle_action == "complete":
                warnings.append(
                    "Repeating task -- this occurrence completed, next occurrence created."
                )
            else:
                warnings.append(
                    "Repeating task -- this occurrence was skipped, "
                    "next occurrence created. To drop the entire repeating "
                    "sequence, this must be done in the OmniFocus UI. "
                    "Confirm with user if this was their intent."
                )

        return True, warnings

    async def _check_cycle(self, task_id: str, container_id: str) -> None:
        """Check if moving task_id under container_id creates a cycle.

        Walks the parent chain from container_id upward. If task_id is
        found, the move would create a circular reference.
        """
        logger.debug(
            "OperatorService._check_cycle: task=%s under container=%s", task_id, container_id
        )
        all_data = await self._repository.get_all()
        task_map = {t.id: t for t in all_data.tasks}

        current = container_id
        while current is not None:
            if current == task_id:
                logger.debug("OperatorService._check_cycle: CYCLE DETECTED")
                msg = "Cannot move task: would create circular reference"
                raise ValueError(msg)
            t = task_map.get(current)
            if t is None or t.parent is None:
                break
            if t.parent.type != "task":
                break
            current = t.parent.id

    async def _resolve_parent(self, parent_id: str) -> str:
        """Resolve parent ID to project or task. Raises ValueError if neither found."""
        logger.debug("OperatorService._resolve_parent: id=%s", parent_id)
        project = await self._repository.get_project(parent_id)
        if project is not None:
            logger.debug("OperatorService._resolve_parent: resolved as project")
            return parent_id

        task = await self._repository.get_task(parent_id)
        if task is not None:
            logger.debug("OperatorService._resolve_parent: resolved as task")
            return parent_id

        msg = f"Parent not found: {parent_id}"
        raise ValueError(msg)

    async def _resolve_tags(self, tag_names: list[str]) -> list[str]:
        """Resolve tag names to IDs case-insensitively. Falls back to ID lookup."""
        logger.debug(
            "OperatorService._resolve_tags: resolving %d tags: %s", len(tag_names), tag_names
        )
        all_data = await self._repository.get_all()
        resolved: list[str] = []

        for name in tag_names:
            # Case-insensitive name match
            matches = [t for t in all_data.tags if t.name.lower() == name.lower()]

            if len(matches) == 1:
                resolved.append(matches[0].id)
            elif len(matches) > 1:
                ids = ", ".join(m.id for m in matches)
                msg = f"Ambiguous tag '{name}': multiple matches ({ids})"
                raise ValueError(msg)
            else:
                # No name match -- try as ID fallback
                logger.debug(
                    "OperatorService._resolve_tags: '%s' no name match, trying as ID", name
                )
                tag = await self._repository.get_tag(name)
                if tag is not None:
                    resolved.append(tag.id)
                else:
                    msg = f"Tag not found: {name}"
                    raise ValueError(msg)

        return resolved

    async def _compute_tag_diff(
        self,
        tag_actions: TagActionSpec,
        current_tags: list[TagRef],
    ) -> tuple[list[str], list[str], list[str]]:
        """Compute the minimal (add_ids, remove_ids, warnings) diff for tag actions.

        Resolves tag names to IDs, computes the final tag set from the
        TagActionSpec input, and returns only the IDs that need adding or
        removing. Warnings are generated by comparing user intent against
        current state BEFORE computing the final set.
        """
        from omnifocus_operator.models.write import _Unset

        warnings: list[str] = []
        current_ids = {t.id for t in current_tags}

        has_replace = not isinstance(tag_actions.replace, _Unset)
        has_add = not isinstance(tag_actions.add, _Unset)
        has_remove = not isinstance(tag_actions.remove, _Unset)
        logger.debug("OperatorService._compute_tag_diff: current_ids=%s", current_ids)
        logger.debug(
            "OperatorService._compute_tag_diff: has_replace=%s, has_add=%s, has_remove=%s",
            has_replace,
            has_add,
            has_remove,
        )

        # Build tag ID -> name map for warning display names
        all_tag_names: dict[str, str] = {}
        if has_add or has_remove or has_replace:
            all_data = await self._repository.get_all()
            all_tag_names = {t.id: t.name for t in all_data.tags}

        if has_replace:
            # replace: null or replace: [] means clear all
            tag_list = tag_actions.replace if isinstance(tag_actions.replace, list) else []
            resolved_ids = await self._resolve_tags(tag_list) if tag_list else []
            final = set(resolved_ids)

            # Warn if tags already match
            if final == current_ids:
                warnings.append("Tags already match the requested set -- no tag changes applied")
        elif has_add and has_remove:
            assert isinstance(tag_actions.add, list)
            assert isinstance(tag_actions.remove, list)
            add_resolved = await self._resolve_tags(tag_actions.add) if tag_actions.add else []
            remove_resolved = (
                await self._resolve_tags(tag_actions.remove) if tag_actions.remove else []
            )

            # Per-tag warnings BEFORE computing final set
            for i, _tag_name in enumerate(tag_actions.add):
                if i < len(add_resolved) and add_resolved[i] in current_ids:
                    display = all_tag_names.get(add_resolved[i], _tag_name)
                    warnings.append(f"Tag '{display}' ({add_resolved[i]}) is already on this task")
            for i, _tag_name in enumerate(tag_actions.remove):
                if i < len(remove_resolved) and remove_resolved[i] not in current_ids:
                    display = all_tag_names.get(remove_resolved[i], _tag_name)
                    warnings.append(f"Tag '{display}' ({remove_resolved[i]}) is not on this task")

            final = (current_ids | set(add_resolved)) - set(remove_resolved)
        elif has_add:
            assert isinstance(tag_actions.add, list)
            add_resolved = await self._resolve_tags(tag_actions.add) if tag_actions.add else []

            # Per-tag warnings
            for i, _tag_name in enumerate(tag_actions.add):
                if i < len(add_resolved) and add_resolved[i] in current_ids:
                    display = all_tag_names.get(add_resolved[i], _tag_name)
                    warnings.append(f"Tag '{display}' ({add_resolved[i]}) is already on this task")

            final = current_ids | set(add_resolved)
        elif has_remove:
            assert isinstance(tag_actions.remove, list)
            remove_resolved = (
                await self._resolve_tags(tag_actions.remove) if tag_actions.remove else []
            )

            # Per-tag warnings
            for i, _tag_name in enumerate(tag_actions.remove):
                if i < len(remove_resolved) and remove_resolved[i] not in current_ids:
                    display = all_tag_names.get(remove_resolved[i], _tag_name)
                    warnings.append(f"Tag '{display}' ({remove_resolved[i]}) is not on this task")

            final = current_ids - set(remove_resolved)
        else:
            # No tag actions -- shouldn't reach here due to TagActionSpec validation
            final = current_ids

        to_add = list(final - current_ids)
        to_remove = list(current_ids - final)

        return to_add, to_remove, warnings


class ErrorOperatorService(OperatorService):
    """Stand-in service that raises on every attribute access.

    Used when the server fails to start (e.g. missing OmniFocus database).
    Instead of crashing, the MCP server stays alive in degraded mode and
    serves the startup error through tool responses.
    """

    def __init__(self, error: Exception) -> None:
        # Bypass OperatorService.__init__ -- we have no repository.
        # Use object.__setattr__ to avoid triggering __getattr__.
        object.__setattr__(
            self,
            "_error_message",
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\nRestart the server after fixing.",
        )

    def __getattr__(self, name: str) -> NoReturn:
        """Intercept every attribute access and raise with the startup error."""
        logger.warning("Tool call in error mode (attribute: %s)", name)
        raise RuntimeError(self._error_message)
