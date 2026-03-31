"""Project model -- represents a single OmniFocus project.

Maps to the flattenedProjects.map() output in the bridge script.
Project has 5 own fields + inherited from ActionableEntity and OmniFocusEntity.
"""

from __future__ import annotations

from pydantic import AwareDatetime

from omnifocus_operator.models.common import ActionableEntity, ReviewInterval


class Project(ActionableEntity):
    """A single OmniFocus project with all fields.

    Inherits shared fields from ActionableEntity (urgency, availability,
    dates, flags, etc.) and OmniFocusEntity (url, added, modified).
    Adds project-specific fields (review, structure).
    """

    # Review (all required per BRIDGE-SPEC)
    last_review_date: AwareDatetime
    next_review_date: AwareDatetime
    review_interval: ReviewInterval

    # Relationships
    next_task: str | None = None
    folder: str | None = None
