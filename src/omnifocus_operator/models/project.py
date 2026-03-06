"""Project model -- represents a single OmniFocus project.

Maps to the flattenedProjects.map() output in the bridge script.
Project has 8 own fields + inherited from ActionableEntity and OmniFocusEntity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import ActionableEntity

if TYPE_CHECKING:
    from pydantic import AwareDatetime

    from omnifocus_operator.models.common import ReviewInterval
    from omnifocus_operator.models.enums import ProjectStatus, TaskStatus


class Project(ActionableEntity):
    """A single OmniFocus project with all bridge fields.

    Inherits shared fields from ActionableEntity (dates, flags, etc.)
    and OmniFocusEntity (url, added, modified, active, effective_active).
    Adds project-specific fields (dual status, review, structure).
    """

    # Dual status fields
    status: ProjectStatus  # Lifecycle status (Active/OnHold/Done/Dropped)
    task_status: TaskStatus  # Computed availability (like task status)

    # Structure
    contains_singleton_actions: bool

    # Review (all required per BRIDGE-SPEC)
    last_review_date: AwareDatetime
    next_review_date: AwareDatetime
    review_interval: ReviewInterval

    # Relationships
    next_task: str | None = None
    folder: str | None = None
