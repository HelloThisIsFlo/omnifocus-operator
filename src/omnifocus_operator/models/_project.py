"""Project model -- represents a single OmniFocus project.

Maps to the flattenedProjects.map() output in the bridge script.
Project has 31 total fields (inherited from ActionableEntity + own).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models._base import ActionableEntity

if TYPE_CHECKING:
    from pydantic import AwareDatetime

    from omnifocus_operator.models._common import ReviewInterval
    from omnifocus_operator.models._enums import EntityStatus, TaskStatus


class Project(ActionableEntity):
    """A single OmniFocus project with all bridge fields.

    Inherits shared fields from ActionableEntity (dates, flags, etc.)
    and adds project-specific fields (dual status, review, structure).

    Note: Project does NOT have active, effectiveActive, added, or
    modified fields in the bridge output (those are Task-specific).
    """

    # Dual status fields
    status: EntityStatus | None = None  # Lifecycle status (Active/Done/Dropped)
    task_status: TaskStatus  # Computed availability (like task status)

    # Structure
    contains_singleton_actions: bool

    # Review
    last_review_date: AwareDatetime | None = None
    next_review_date: AwareDatetime | None = None
    review_interval: ReviewInterval | None = None

    # Relationships
    next_task: str | None = None
    folder: str | None = None
