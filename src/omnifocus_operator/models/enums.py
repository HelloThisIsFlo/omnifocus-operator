"""Status enumerations for OmniFocus entities.

Values match the exact strings produced by the bridge script:
- TaskStatus: from the ts() function mapping Task.Status values
- ProjectStatus: from the bridge ps() resolver
- TagStatus: from the bridge gs() resolver
- FolderStatus: from the bridge fs() resolver
- ScheduleType: from the bridge rst() resolver
- AnchorDateKey: from the bridge adk() resolver
"""

from enum import StrEnum


class Urgency(StrEnum):
    """Time pressure axis -- is this task/project pressing?"""

    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    NONE = "none"


class Availability(StrEnum):
    """Work readiness axis -- can this be worked on?"""

    AVAILABLE = "available"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DROPPED = "dropped"


class TaskStatus(StrEnum):
    """Computed availability status for tasks (from bridge ts() function)."""

    AVAILABLE = "Available"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"
    DROPPED = "Dropped"
    DUE_SOON = "DueSoon"
    NEXT = "Next"
    OVERDUE = "Overdue"


class ProjectStatus(StrEnum):
    """Lifecycle status for projects (from bridge ps() resolver)."""

    ACTIVE = "Active"
    ON_HOLD = "OnHold"
    DONE = "Done"
    DROPPED = "Dropped"


class TagStatus(StrEnum):
    """Lifecycle status for tags (from bridge gs() resolver)."""

    ACTIVE = "Active"
    ON_HOLD = "OnHold"
    DROPPED = "Dropped"


class FolderStatus(StrEnum):
    """Lifecycle status for folders (from bridge fs() resolver)."""

    ACTIVE = "Active"
    DROPPED = "Dropped"


class ScheduleType(StrEnum):
    """Repetition schedule type (from bridge rst() resolver)."""

    REGULARLY = "Regularly"
    FROM_COMPLETION = "FromCompletion"
    NONE = "None"


class AnchorDateKey(StrEnum):
    """Anchor date key for repetition rules (from bridge adk() resolver)."""

    DUE_DATE = "DueDate"
    DEFER_DATE = "DeferDate"
    PLANNED_DATE = "PlannedDate"
