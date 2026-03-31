"""Task model -- represents a single OmniFocus task."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnifocus_operator.models.common import ActionableEntity, ParentRef


class Task(ActionableEntity):
    """A single OmniFocus task with all fields."""

    # Inbox
    in_inbox: bool

    # Dates (task-only -- always null on projects)
    effective_completion_date: AwareDatetime | None = Field(
        default=None,
        description="Inherited from parent project or task if not set directly on this task.",
    )

    # Parent reference (None = inbox task)
    parent: ParentRef | None = None
