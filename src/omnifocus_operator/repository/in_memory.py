"""InMemoryRepository -- returns pre-built entities without bridge interaction."""

from __future__ import annotations

from datetime import UTC, datetime
from typing import TYPE_CHECKING
from uuid import uuid4

from omnifocus_operator.contracts.protocols import Repository

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.create_task import (
        CreateTaskRepoPayload,
        CreateTaskRepoResult,
    )
    from omnifocus_operator.contracts.use_cases.edit_task import (
        EditTaskRepoPayload,
        EditTaskRepoResult,
    )
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.snapshot import AllEntities
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task

__all__ = ["InMemoryRepository"]


class InMemoryRepository(Repository):
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

    async def add_task(self, payload: CreateTaskRepoPayload) -> CreateTaskRepoResult:
        """Create a task in-memory and append to snapshot.

        Generates a synthetic ID and builds a Task with computed fields.
        Used for testing without a real bridge.
        """
        from omnifocus_operator.contracts.use_cases.create_task import CreateTaskRepoResult
        from omnifocus_operator.models.task import Task

        task_id = f"mem-{uuid4().hex[:8]}"
        now = datetime.now(tz=UTC)
        has_parent = payload.parent is not None

        task = Task.model_validate(
            {
                "id": task_id,
                "name": payload.name,
                "url": f"omnifocus:///task/{task_id}",
                "added": now.isoformat(),
                "modified": now.isoformat(),
                "note": payload.note or "",
                "flagged": payload.flagged or False,
                "effectiveFlagged": payload.flagged or False,
                "urgency": "none",
                "availability": "available",
                "inInbox": not has_parent,
                "dueDate": payload.due_date,
                "deferDate": payload.defer_date,
                "plannedDate": payload.planned_date,
                "estimatedMinutes": payload.estimated_minutes,
                "hasChildren": False,
                "parent": None,
                "tags": [],
            }
        )

        # Append to mutable tasks list
        self._snapshot.tasks.append(task)

        return CreateTaskRepoResult(id=task_id, name=payload.name)

    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult:
        """Edit a task in-memory by mutating the snapshot.

        Serializes the typed payload to a camelCase dict, then applies
        existing mutation logic on that dict for consistency.
        """
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskRepoResult
        from omnifocus_operator.models.common import ParentRef, TagRef

        raw = payload.model_dump(by_alias=True, exclude_unset=True)

        task_id = raw["id"]
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
        for key, value in raw.items():
            if key in skip_keys:
                continue
            attr = _key_map.get(key)
            if attr is not None:
                setattr(task, attr, value)

        # Handle tag operations (diff-based: removals first, then additions)
        remove_ids = set(raw.get("removeTagIds", []))
        if remove_ids:
            task.tags = [t for t in task.tags if t.id not in remove_ids]
        add_ids = raw.get("addTagIds", [])
        if add_ids:
            existing_ids = {t.id for t in task.tags}
            for tid in add_ids:
                if tid not in existing_ids:
                    task.tags.append(TagRef(id=tid, name=tid))

        # Handle lifecycle
        lifecycle = raw.get("lifecycle")
        if lifecycle is not None:
            from omnifocus_operator.models.enums import Availability

            if lifecycle == "complete":
                task.availability = Availability.COMPLETED
            elif lifecycle == "drop":
                task.availability = Availability.DROPPED

        # Handle moveTo (simplified -- just update parent)
        move_to = raw.get("moveTo")
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

        return EditTaskRepoResult(id=task.id, name=task.name)
