"""InMemoryRepository -- returns pre-built entities without bridge interaction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

if TYPE_CHECKING:
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task
    from omnifocus_operator.models.write import TaskCreateResult, TaskCreateSpec

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

    async def add_task(
        self,
        spec: TaskCreateSpec,
        *,
        resolved_tag_ids: list[str] | None = None,
    ) -> TaskCreateResult:
        """Create a task in-memory and append to snapshot.

        Generates a synthetic ID and builds a Task with computed fields.
        Used for testing without a real bridge.
        """
        from omnifocus_operator.models.task import Task
        from omnifocus_operator.models.write import TaskCreateResult

        task_id = f"mem-{uuid4().hex[:8]}"
        now = datetime.now(tz=UTC)
        has_parent = spec.parent is not None

        task = Task.model_validate(
            {
                "id": task_id,
                "name": spec.name,
                "url": f"omnifocus:///task/{task_id}",
                "added": now.isoformat(),
                "modified": now.isoformat(),
                "note": spec.note or "",
                "flagged": spec.flagged or False,
                "effectiveFlagged": spec.flagged or False,
                "urgency": "none",
                "availability": "available",
                "inInbox": not has_parent,
                "dueDate": spec.due_date.isoformat() if spec.due_date else None,
                "deferDate": spec.defer_date.isoformat() if spec.defer_date else None,
                "plannedDate": spec.planned_date.isoformat() if spec.planned_date else None,
                "estimatedMinutes": spec.estimated_minutes,
                "hasChildren": False,
                "parent": None,
                "tags": [],
            }
        )

        # Append to mutable tasks list
        self._snapshot.tasks.append(task)

        return TaskCreateResult(success=True, id=task_id, name=spec.name)
