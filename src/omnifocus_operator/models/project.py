"""Project model -- represents a single OmniFocus project."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnifocus_operator.agent_messages.descriptions import (
    NEXT_TASK,
    PROJECT_DOC,
    PROJECT_FOLDER_DESC,
    PROJECT_TYPE_DESC,
)
from omnifocus_operator.models.common import (
    ActionableEntity,
    FolderRef,
    ReviewInterval,
    TaskRef,
)
from omnifocus_operator.models.enums import ProjectType


class Project(ActionableEntity):
    __doc__ = PROJECT_DOC

    # Per-type enum (parallel | sequential | singleActions) -- HIER-02 / HIER-05.
    # `singleActions` takes precedence over `sequential` when both underlying
    # flags are set; assembly happens at the repository or service layer
    # depending on the final placement chosen by Phase 56-03.
    type: ProjectType = Field(description=PROJECT_TYPE_DESC)

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
