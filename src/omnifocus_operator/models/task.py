"""Task model -- represents a single OmniFocus task.

Maps to the flattenedTasks.map() output in the bridge script.
Task has 3 own fields + inherited from ActionableEntity and OmniFocusEntity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import ActionableEntity

if TYPE_CHECKING:
    from pydantic import AwareDatetime

    from omnifocus_operator.models.common import ParentRef


class Task(ActionableEntity):
    """A single OmniFocus task with all fields.

    Inherits shared fields from ActionableEntity (urgency, availability,
    dates, flags, etc.) and OmniFocusEntity (url, added, modified).
    Adds task-specific fields (inbox, completion, parent reference).

    Fields unique to Task (not on Project):
    - in_inbox: whether task is in inbox
    - effective_completion_date: only meaningful on tasks (always null on projects)
    - parent: reference to containing project or parent task, None for inbox
    """

    # Inbox
    in_inbox: bool

    # Dates (task-only -- always null on projects)
    effective_completion_date: AwareDatetime | None = None

    # Parent reference (None = inbox task)
    parent: ParentRef | None = None
