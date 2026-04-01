"""Project model -- represents a single OmniFocus project."""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnifocus_operator.agent_messages.descriptions import NEXT_TASK, PROJECT_DOC
from omnifocus_operator.models.common import ActionableEntity, ReviewInterval


class Project(ActionableEntity):
    __doc__ = PROJECT_DOC

    # Review (all required per BRIDGE-SPEC)
    last_review_date: AwareDatetime
    next_review_date: AwareDatetime
    review_interval: ReviewInterval

    # Relationships
    next_task: str | None = Field(
        default=None,
        description=NEXT_TASK,
    )
    folder: str | None = None
