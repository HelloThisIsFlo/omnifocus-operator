"""Filter-side availability enums with shorthand values, and due-soon config enum.

These mirror the core enums (Availability, TagAvailability, FolderAvailability)
and add shorthand values for ergonomic queries: REMAINING on AvailabilityFilter
(expands to AVAILABLE + BLOCKED), ALL on Tag/FolderAvailabilityFilter (expands
to full list). Service layer expands shorthands and maps back to core enums.

DueSoonSetting captures the 7 discrete "due soon" threshold options from
OmniFocus preferences, expressed as domain properties rather than raw SQLite ints.
"""

from enum import Enum, StrEnum

from omnifocus_operator.agent_messages.descriptions import (
    AVAILABILITY_DOC,
    DUE_DATE_SHORTCUT_DOC,
    FOLDER_AVAILABILITY_DOC,
    LIFECYCLE_DATE_SHORTCUT_DOC,
    TAG_AVAILABILITY_DOC,
)


class AvailabilityFilter(StrEnum):
    __doc__ = AVAILABILITY_DOC

    AVAILABLE = "available"
    BLOCKED = "blocked"
    REMAINING = "remaining"


class TagAvailabilityFilter(StrEnum):
    __doc__ = TAG_AVAILABILITY_DOC

    AVAILABLE = "available"
    BLOCKED = "blocked"
    DROPPED = "dropped"
    ALL = "ALL"


class FolderAvailabilityFilter(StrEnum):
    __doc__ = FOLDER_AVAILABILITY_DOC

    AVAILABLE = "available"
    DROPPED = "dropped"
    ALL = "ALL"


class DueDateShortcut(StrEnum):
    __doc__ = DUE_DATE_SHORTCUT_DOC

    OVERDUE = "overdue"
    SOON = "soon"
    TODAY = "today"


class LifecycleDateShortcut(StrEnum):
    __doc__ = LIFECYCLE_DATE_SHORTCUT_DOC

    ALL = "all"
    TODAY = "today"


class DueSoonSetting(Enum):
    """OmniFocus "due soon" threshold settings.

    OmniFocus exposes exactly 7 discrete options for the "due soon" threshold
    in its preferences. Each setting has two domain properties:

    - ``days``: the number of days in the threshold window
    - ``calendar_aligned``: whether the threshold snaps to midnight (True)
      or rolls from the current time (False)

    Calendar-aligned (``calendar_aligned=True``): "due soon" means the task is
    due before midnight N days from now. At 11 PM with a 1-day setting, only
    1 hour remains.

    Rolling (``calendar_aligned=False``): "due soon" means the task is due
    within N*24 hours from now. At 11 PM with a 1-day setting, 24 hours remain.

    Only TWENTY_FOUR_HOURS uses rolling mode; all other settings are
    calendar-aligned.
    """

    TODAY = (1, True)
    TWENTY_FOUR_HOURS = (1, False)
    TWO_DAYS = (2, True)
    THREE_DAYS = (3, True)
    FOUR_DAYS = (4, True)
    FIVE_DAYS = (5, True)
    ONE_WEEK = (7, True)

    def __init__(self, days: int, calendar_aligned: bool) -> None:
        self._days = days
        self._calendar_aligned = calendar_aligned

    @property
    def days(self) -> int:
        """Number of days in the threshold window."""
        return self._days

    @property
    def calendar_aligned(self) -> bool:
        """Whether the threshold snaps to midnight (True) or rolls from now (False)."""
        return self._calendar_aligned
