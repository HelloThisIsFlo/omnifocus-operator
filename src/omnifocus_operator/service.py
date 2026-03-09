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
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.models.write import (
        MoveToSpec,
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
        return await self._repository.get_all()

    async def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        return await self._repository.get_task(task_id)

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        return await self._repository.get_project(project_id)

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
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
        task = await self._repository.get_task(spec.id)
        if task is None:
            msg = f"Task not found: {spec.id}"
            raise ValueError(msg)

        warnings: list[str] = []

        # Warn about editing completed/dropped tasks
        if task.availability in (Availability.COMPLETED, Availability.DROPPED):
            status = task.availability.value
            warnings.append(
                f"This task is {status} -- your changes were applied, "
                f"but please confirm with the user that they intended to edit a {status} task."
            )

        # 2. Validate name (if provided)
        if not isinstance(spec.name, _Unset) and (not spec.name or not spec.name.strip()):
            msg = "Task name cannot be empty"
            raise ValueError(msg)

        # 3. Build payload with only non-UNSET fields
        payload: dict[str, object] = {"id": spec.id}

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

        # 4. Handle tags
        has_replace = not isinstance(spec.tags, _Unset)
        has_add = not isinstance(spec.add_tags, _Unset)
        has_remove = not isinstance(spec.remove_tags, _Unset)

        # Build tag ID -> name map for warning display names
        # (resolves human-readable names when caller passes raw IDs)
        all_tag_names: dict[str, str] = {}
        if has_add or has_remove:
            all_data = await self._repository.get_all()
            all_tag_names = {t.id: t.name for t in all_data.tags}

        if has_replace:
            # tags: null means clear all (same as tags: [])
            tag_list = spec.tags if isinstance(spec.tags, list) else []
            resolved_ids = await self._resolve_tags(tag_list) if tag_list else []
            payload["tagMode"] = "replace"
            payload["tagIds"] = resolved_ids
        elif has_add and has_remove:
            # Add + remove mode
            assert isinstance(spec.add_tags, list)
            assert isinstance(spec.remove_tags, list)
            add_ids = await self._resolve_tags(spec.add_tags) if spec.add_tags else []
            remove_ids = await self._resolve_tags(spec.remove_tags) if spec.remove_tags else []
            # Warnings for tags already on task (add duplicates)
            current_tag_ids = {t.id for t in task.tags}
            for i, tag_name in enumerate(spec.add_tags):
                if i < len(add_ids) and add_ids[i] in current_tag_ids:
                    display = all_tag_names.get(add_ids[i], tag_name)
                    warnings.append(f"Tag '{display}' ({add_ids[i]}) is already on this task")
            # Warnings for removing tags not on task
            for i, tag_name in enumerate(spec.remove_tags):
                if remove_ids[i] not in current_tag_ids:
                    display = all_tag_names.get(remove_ids[i], tag_name)
                    warnings.append(f"Tag '{display}' ({remove_ids[i]}) is not on this task")
            payload["tagMode"] = "add_remove"
            payload["addTagIds"] = add_ids
            payload["removeTagIds"] = remove_ids
        elif has_add:
            # Add-only mode
            assert isinstance(spec.add_tags, list)
            add_ids = await self._resolve_tags(spec.add_tags) if spec.add_tags else []
            # Warn about tags already present
            current_tag_ids = {t.id for t in task.tags}
            for i, tag_name in enumerate(spec.add_tags):
                if i < len(add_ids) and add_ids[i] in current_tag_ids:
                    display = all_tag_names.get(add_ids[i], tag_name)
                    warnings.append(f"Tag '{display}' ({add_ids[i]}) is already on this task")
            payload["tagMode"] = "add"
            payload["tagIds"] = add_ids
        elif has_remove:
            # Remove-only mode
            assert isinstance(spec.remove_tags, list)
            remove_ids = await self._resolve_tags(spec.remove_tags) if spec.remove_tags else []
            # Warnings for removing tags not on task
            current_tag_ids = {t.id for t in task.tags}
            for i, tag_name in enumerate(spec.remove_tags):
                if remove_ids[i] not in current_tag_ids:
                    display = all_tag_names.get(remove_ids[i], tag_name)
                    warnings.append(f"Tag '{display}' ({remove_ids[i]}) is not on this task")
            payload["tagMode"] = "remove"
            payload["removeTagIds"] = remove_ids

        # 5. Handle moveTo
        if not isinstance(spec.move_to, _Unset):
            move_to_spec: MoveToSpec = spec.move_to
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
        if len(payload) == 1:  # Only "id" key
            return TaskEditResult(
                success=True,
                id=spec.id,
                name=task.name,
                warnings=(warnings or [])
                + [
                    "No changes specified -- if you intended to change fields, "
                    "include them in the request"
                ],
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

        # Check tag changes if no field changes detected yet
        if is_noop and "tagMode" in payload:
            sorted_current_tag_ids = sorted(t.id for t in task.tags)
            if payload.get("tagMode") == "replace":
                raw_ids = payload.get("tagIds")
                new_tag_ids = sorted(raw_ids) if isinstance(raw_ids, list) else []
                if new_tag_ids != sorted_current_tag_ids:
                    is_noop = False
            else:
                # add/remove/add_remove modes always represent intentional changes
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
                    warnings.append("Task is already in this location")
                    # is_noop stays True -- same container
                else:
                    is_noop = False
            else:
                # before/after -- can't detect same position
                is_noop = False

        if is_noop and len(payload) > 1:
            return TaskEditResult(
                success=True,
                id=spec.id,
                name=task.name,
                warnings=(warnings or [])
                + [
                    "No changes detected -- the task already has these values. "
                    "If you don't want to change a field, omit it from the request."
                ],
            )

        # 8. Delegate to repository
        result = await self._repository.edit_task(payload)

        # 9. Return result
        return TaskEditResult(
            success=True,
            id=result["id"],
            name=result["name"],
            warnings=warnings or None,
        )

    async def _check_cycle(self, task_id: str, container_id: str) -> None:
        """Check if moving task_id under container_id creates a cycle.

        Walks the parent chain from container_id upward. If task_id is
        found, the move would create a circular reference.
        """
        all_data = await self._repository.get_all()
        task_map = {t.id: t for t in all_data.tasks}

        current = container_id
        while current is not None:
            if current == task_id:
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
        project = await self._repository.get_project(parent_id)
        if project is not None:
            return parent_id

        task = await self._repository.get_task(parent_id)
        if task is not None:
            return parent_id

        msg = f"Parent not found: {parent_id}"
        raise ValueError(msg)

    async def _resolve_tags(self, tag_names: list[str]) -> list[str]:
        """Resolve tag names to IDs case-insensitively. Falls back to ID lookup."""
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
                tag = await self._repository.get_tag(name)
                if tag is not None:
                    resolved.append(tag.id)
                else:
                    msg = f"Tag not found: {name}"
                    raise ValueError(msg)

        return resolved


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
