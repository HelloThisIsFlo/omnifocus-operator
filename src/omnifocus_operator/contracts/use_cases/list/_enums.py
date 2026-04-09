"""Filter-side availability enums with shorthand values.

These mirror the core enums (Availability, TagAvailability, FolderAvailability)
and add shorthand values for ergonomic queries: REMAINING on AvailabilityFilter
(expands to AVAILABLE + BLOCKED), ALL on Tag/FolderAvailabilityFilter (expands
to full list). Service layer expands shorthands and maps back to core enums.
"""

from enum import StrEnum

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
