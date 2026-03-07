"""Task model -- represents a single OmniFocus task.

Maps to the flattenedTasks.map() output in the bridge script.
Task has 4 own fields + inherited from ActionableEntity and OmniFocusEntity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import ActionableEntity

if TYPE_CHECKING:
    from pydantic import AwareDatetime


class Task(ActionableEntity):
    """A single OmniFocus task with all fields.

    Inherits shared fields from ActionableEntity (urgency, availability,
    dates, flags, etc.) and OmniFocusEntity (url, added, modified).
    Adds task-specific fields (inbox, completion, relationships).

    Fields unique to Task (not on Project):
    - in_inbox: whether task is in inbox
    - effective_completion_date: only meaningful on tasks (always null on projects)
    - project, parent: relationship IDs
    """

    # Inbox
    in_inbox: bool

    # Dates (task-only -- always null on projects)
    effective_completion_date: AwareDatetime | None = None

    # Relationships (optional)
    project: str | None = None
    parent: str | None = None
