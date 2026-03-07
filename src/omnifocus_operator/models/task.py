"""Task model -- represents a single OmniFocus task.

Maps to the flattenedTasks.map() output in the bridge script.
Task has 3 own fields + inherited from ActionableEntity and OmniFocusEntity.
"""

from __future__ import annotations

from omnifocus_operator.models.base import ActionableEntity


class Task(ActionableEntity):
    """A single OmniFocus task with all fields.

    Inherits shared fields from ActionableEntity (urgency, availability,
    dates, flags, etc.) and OmniFocusEntity (url, added, modified).
    Adds task-specific fields (inbox, relationships).

    Fields unique to Task (not on Project):
    - in_inbox: whether task is in inbox
    - project, parent: relationship IDs
    """

    # Inbox
    in_inbox: bool

    # Relationships (optional)
    project: str | None = None
    parent: str | None = None
