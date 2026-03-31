"""Project model -- represents a single OmniFocus project."""

from __future__ import annotations

from pydantic import AwareDatetime

from omnifocus_operator.models.common import ActionableEntity, ReviewInterval


class Project(ActionableEntity):
    """A single OmniFocus project with all fields."""

    # Review (all required per BRIDGE-SPEC)
    last_review_date: AwareDatetime
    next_review_date: AwareDatetime
    review_interval: ReviewInterval

    # Relationships
    next_task: str | None = None
    folder: str | None = None
