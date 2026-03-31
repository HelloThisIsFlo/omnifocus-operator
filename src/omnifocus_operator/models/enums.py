"""Status and repetition enumerations for OmniFocus entities.

Values use snake_case strings matching the new two-axis model:
- Urgency: time pressure axis (overdue, due_soon, none)
- Availability: work readiness axis (available, blocked, completed, dropped)
- TagAvailability: tag availability (available, blocked, dropped)
- FolderAvailability: folder availability (available, dropped)
- Schedule: repetition schedule type (regularly, regularly_with_catch_up, from_completion)
- BasedOn: anchor date for repetition rules (due_date, defer_date, planned_date)
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


class TagAvailability(StrEnum):
    """Availability status for tags."""

    AVAILABLE = "available"
    BLOCKED = "blocked"
    DROPPED = "dropped"


class FolderAvailability(StrEnum):
    """Availability status for folders."""

    AVAILABLE = "available"
    DROPPED = "dropped"


class Schedule(StrEnum):
    """Repetition schedule type."""

    REGULARLY = "regularly"
    REGULARLY_WITH_CATCH_UP = "regularly_with_catch_up"
    FROM_COMPLETION = "from_completion"


class BasedOn(StrEnum):
    """Anchor date for repetition rules."""

    DUE_DATE = "due_date"
    DEFER_DATE = "defer_date"
    PLANNED_DATE = "planned_date"
