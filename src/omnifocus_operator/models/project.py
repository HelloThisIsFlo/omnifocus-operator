"""Project model -- represents a single OmniFocus project."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnifocus_operator.agent_messages.descriptions import (
    NEXT_TASK,
    PROJECT_DOC,
    PROJECT_FOLDER_DESC,
)
from omnifocus_operator.models.common import (
    ActionableEntity,
    FolderRef,
    ReviewInterval,
    TaskRef,
)


class Project(ActionableEntity):
    __doc__ = PROJECT_DOC

    # Review (all required per BRIDGE-SPEC)
    last_review_date: AwareDatetime
    next_review_date: AwareDatetime
    review_interval: ReviewInterval

    # Relationships
    next_task: TaskRef | None = Field(
        default=None,
        description=NEXT_TASK,
    )
    folder: FolderRef | None = Field(default=None, description=PROJECT_FOLDER_DESC)
