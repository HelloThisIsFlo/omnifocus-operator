"""Repository protocol -- structural typing interface for OmniFocus data access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.models.write import TaskCreateResult, TaskCreateSpec

__all__ = ["Repository"]


@runtime_checkable
class Repository(Protocol):
    """Protocol for OmniFocus data repositories.

    Any class with a matching ``async get_all`` method satisfies this
    protocol via structural subtyping -- no inheritance required.
    """

    async def get_all(self) -> AllEntities:
        """Return all OmniFocus entities."""
        ...

    async def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        ...

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        ...

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
        ...

    async def add_task(
        self,
        spec: TaskCreateSpec,
        *,
        resolved_tag_ids: list[str] | None = None,
    ) -> TaskCreateResult:
        """Create a task and return the result."""
        ...
