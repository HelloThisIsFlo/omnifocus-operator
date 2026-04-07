"""Filter-side availability enums with ALL shorthand.

These mirror the core enums (Availability, TagAvailability, FolderAvailability)
and add an ALL value for ergonomic "include everything" queries.
Used in agent-facing query models. Service layer expands ALL to full list
and maps back to core enums for repo queries.
"""

from enum import StrEnum

from omnifocus_operator.agent_messages.descriptions import (
    AVAILABILITY_DOC,
    FOLDER_AVAILABILITY_DOC,
    TAG_AVAILABILITY_DOC,
)


class AvailabilityFilter(StrEnum):
    __doc__ = AVAILABILITY_DOC

    AVAILABLE = "available"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DROPPED = "dropped"
    ALL = "ALL"


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
