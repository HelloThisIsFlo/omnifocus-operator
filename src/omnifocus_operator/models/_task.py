"""Task model -- represents a single OmniFocus task.

Maps to the flattenedTasks.map() output in the bridge script.
Task has 32 total fields (inherited from ActionableEntity + own).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models._base import ActionableEntity

if TYPE_CHECKING:
    from pydantic import AwareDatetime

    from omnifocus_operator.models._enums import TaskStatus


class Task(ActionableEntity):
    """A single OmniFocus task with all bridge fields.

    Inherits shared fields from ActionableEntity (dates, flags, etc.)
    and adds task-specific fields (status, inbox, relationships).

    Fields unique to Task (not on Project in bridge output):
    - added, modified: timestamps
    - active, effective_active: availability flags
    - status: computed TaskStatus
    - in_inbox: whether task is in inbox
    - project, parent, assigned_container: relationship IDs
    """

    # Lifecycle (Task-specific -- not on Project in bridge output)
    added: AwareDatetime | None = None
    modified: AwareDatetime | None = None
    active: bool
    effective_active: bool

    # Status (required, no default)
    status: TaskStatus

    # Inbox
    in_inbox: bool

    # Relationships (optional)
    project: str | None = None
    parent: str | None = None
    assigned_container: str | None = None
