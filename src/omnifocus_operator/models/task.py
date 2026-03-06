"""Task model -- represents a single OmniFocus task.

Maps to the flattenedTasks.map() output in the bridge script.
Task has 4 own fields + inherited from ActionableEntity and OmniFocusEntity.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import ActionableEntity

if TYPE_CHECKING:
    from omnifocus_operator.models.enums import TaskStatus


class Task(ActionableEntity):
    """A single OmniFocus task with all bridge fields.

    Inherits shared fields from ActionableEntity (dates, flags, etc.)
    and OmniFocusEntity (url, added, modified, active, effective_active).
    Adds task-specific fields (status, inbox, relationships).

    Fields unique to Task (not on Project in bridge output):
    - status: computed TaskStatus
    - in_inbox: whether task is in inbox
    - project, parent: relationship IDs
    """

    # Status (required, no default)
    status: TaskStatus

    # Inbox
    in_inbox: bool

    # Relationships (optional)
    project: str | None = None
    parent: str | None = None
