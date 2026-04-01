"""Task model -- represents a single OmniFocus task."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnifocus_operator.agent_messages.descriptions import (
    EFFECTIVE_COMPLETION_DATE,
    TASK_DOC,
)
from omnifocus_operator.models.common import ActionableEntity, ParentRef


class Task(ActionableEntity):
    __doc__ = TASK_DOC

    # Inbox
    in_inbox: bool

    # Dates (task-only -- always null on projects)
    effective_completion_date: AwareDatetime | None = Field(
        default=None,
        description=EFFECTIVE_COMPLETION_DATE,
    )

    # Parent reference (None = inbox task)
    parent: ParentRef | None = None
