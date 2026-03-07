"""InMemoryRepository -- returns pre-built entities without bridge interaction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task

__all__ = ["InMemoryRepository"]


class InMemoryRepository:
    """Repository backed by a pre-built ``AllEntities`` instance.

    Useful for testing where no bridge, adapter, or caching is needed.
    Simply returns the data passed at construction time.
    """

    def __init__(self, snapshot: AllEntities) -> None:
        self._snapshot = snapshot

    async def get_all(self) -> AllEntities:
        """Return all pre-built entities."""
        return self._snapshot

    async def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        return next((t for t in self._snapshot.tasks if t.id == task_id), None)

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        return next((p for p in self._snapshot.projects if p.id == project_id), None)

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
        return next((t for t in self._snapshot.tags if t.id == tag_id), None)
