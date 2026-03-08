"""Service module -- primary API surface for the MCP server.

The service layer provides the primary API surface for the MCP server.
Currently a simple delegation to ``Repository``; future phases may add
orchestration, caching policies, or multi-repository coordination.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NoReturn

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
        warnings: list[str] = []

        has_replace = not isinstance(spec.tags, _Unset)
        has_add = not isinstance(spec.add_tags, _Unset)
        has_remove = not isinstance(spec.remove_tags, _Unset)

        if has_replace:
            # Replace mode -- tags is list[str] here (not _Unset)
            assert isinstance(spec.tags, list)
            resolved_ids = await self._resolve_tags(spec.tags) if spec.tags else []
            payload["tagMode"] = "replace"
            payload["tagIds"] = resolved_ids
        elif has_add and has_remove:
            # Add + remove mode
            assert isinstance(spec.add_tags, list)
            assert isinstance(spec.remove_tags, list)
            add_ids = await self._resolve_tags(spec.add_tags) if spec.add_tags else []
            remove_ids = await self._resolve_tags(spec.remove_tags) if spec.remove_tags else []
            # Warnings for removing tags not on task
            current_tag_ids = {t.id for t in task.tags}
            for i, tag_name in enumerate(spec.remove_tags):
                if remove_ids[i] not in current_tag_ids:
                    warnings.append(
                        f"Tag '{tag_name}' was not on this task"
                        " -- to skip tag changes, omit removeTags"
                    )
            payload["tagMode"] = "add_remove"
            payload["addTagIds"] = add_ids
            payload["removeTagIds"] = remove_ids
        elif has_add:
            # Add-only mode
            assert isinstance(spec.add_tags, list)
            add_ids = await self._resolve_tags(spec.add_tags) if spec.add_tags else []
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
                    warnings.append(
                        f"Tag '{tag_name}' was not on this task"
                        " -- to skip tag changes, omit removeTags"
                    )
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

        # 6. Delegate to repository
        result = await self._repository.edit_task(payload)

        # 7. Return result
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
