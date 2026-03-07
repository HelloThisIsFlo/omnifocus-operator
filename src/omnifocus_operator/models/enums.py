"""Status enumerations for OmniFocus entities.

Values use snake_case strings matching the new two-axis model:
- Urgency: time pressure axis (overdue, due_soon, none)
- Availability: work readiness axis (available, blocked, completed, dropped)
- TagStatus: tag lifecycle (active, on_hold, dropped)
- FolderStatus: folder lifecycle (active, dropped)
- ScheduleType: repetition schedule type (regularly, from_completion)
- AnchorDateKey: anchor date for repetition rules (due_date, defer_date, planned_date)
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


class TagStatus(StrEnum):
    """Lifecycle status for tags."""

    ACTIVE = "active"
    ON_HOLD = "on_hold"
    DROPPED = "dropped"


class FolderStatus(StrEnum):
    """Lifecycle status for folders."""

    ACTIVE = "active"
    DROPPED = "dropped"


class ScheduleType(StrEnum):
    """Repetition schedule type."""

    REGULARLY = "regularly"
    FROM_COMPLETION = "from_completion"


class AnchorDateKey(StrEnum):
    """Anchor date key for repetition rules."""

    DUE_DATE = "due_date"
    DEFER_DATE = "defer_date"
    PLANNED_DATE = "planned_date"
