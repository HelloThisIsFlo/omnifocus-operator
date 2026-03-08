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
    from omnifocus_operator.models.write import TaskCreateResult, TaskCreateSpec
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
