"""Task model -- represents a single OmniFocus task."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnifocus_operator.agent_messages.descriptions import (
    EFFECTIVE_COMPLETION_DATE,
    TASK_DOC,
    TASK_PROJECT_DESC,
)
from omnifocus_operator.models.common import ActionableEntity, ParentRef, ProjectRef


class Task(ActionableEntity):
    __doc__ = TASK_DOC

    # Dates (task-only -- always null on projects)
    effective_completion_date: AwareDatetime | None = Field(
        default=None,
        description=EFFECTIVE_COMPLETION_DATE,
    )

    # Parent reference (tagged wrapper: project or task)
    parent: ParentRef

    # Containing project (at any nesting depth, or $inbox)
    project: ProjectRef = Field(description=TASK_PROJECT_DESC)
