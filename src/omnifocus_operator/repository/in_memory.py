"""InMemoryRepository -- returns pre-built entities without bridge interaction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any
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

    async def edit_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Edit a task in-memory by mutating the snapshot.

        Simplified mutation for testing -- maps camelCase payload keys to
        snake_case model attributes and updates tags/parent as needed.
        """
        from omnifocus_operator.models.common import ParentRef, TagRef

        task_id = payload["id"]
        task = next((t for t in self._snapshot.tasks if t.id == task_id), None)
        if task is None:
            msg = f"Task not found: {task_id}"
            raise ValueError(msg)

        # camelCase payload key -> snake_case attribute
        _key_map: dict[str, str] = {
            "name": "name",
            "note": "note",
            "flagged": "flagged",
            "dueDate": "due_date",
            "deferDate": "defer_date",
            "plannedDate": "planned_date",
            "estimatedMinutes": "estimated_minutes",
        }

        skip_keys = {"id", "addTagIds", "removeTagIds", "moveTo", "lifecycle"}
        for key, value in payload.items():
            if key in skip_keys:
                continue
            attr = _key_map.get(key)
            if attr is not None:
                setattr(task, attr, value)

        # Handle tag operations (diff-based: removals first, then additions)
        remove_ids = set(payload.get("removeTagIds", []))
        if remove_ids:
            task.tags = [t for t in task.tags if t.id not in remove_ids]
        add_ids = payload.get("addTagIds", [])
        if add_ids:
            existing_ids = {t.id for t in task.tags}
            for tid in add_ids:
                if tid not in existing_ids:
                    task.tags.append(TagRef(id=tid, name=tid))

        # Handle lifecycle
        lifecycle = payload.get("lifecycle")
        if lifecycle is not None:
            from omnifocus_operator.models.enums import Availability

            if lifecycle == "complete":
                task.availability = Availability.COMPLETED
            elif lifecycle == "drop":
                task.availability = Availability.DROPPED

        # Handle moveTo (simplified -- just update parent)
        move_to = payload.get("moveTo")
        if move_to is not None:
            container_id = move_to.get("containerId")
            if container_id is None:
                # Moving to inbox
                task.parent = None
                task.in_inbox = True
            else:
                # Check if container is a project or task
                project = next((p for p in self._snapshot.projects if p.id == container_id), None)
                if project is not None:
                    task.parent = ParentRef(type="project", id=container_id, name=project.name)
                    task.in_inbox = False
                else:
                    parent_task = next(
                        (t for t in self._snapshot.tasks if t.id == container_id), None
                    )
                    name = parent_task.name if parent_task else ""
                    task.parent = ParentRef(type="task", id=container_id, name=name)
                    task.in_inbox = False

        return {"id": task.id, "name": task.name}
