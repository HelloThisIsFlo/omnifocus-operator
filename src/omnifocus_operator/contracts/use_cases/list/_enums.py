"""Filter-side availability enums with ALL shorthand.

These mirror the core enums (Availability, TagAvailability, FolderAvailability)
and add an ALL value for ergonomic "include everything" queries.
Used in agent-facing query models. Service layer expands ALL to full list
and maps back to core enums for repo queries.
"""

from enum import StrEnum


class AvailabilityFilter(StrEnum):
    """Task/project availability filter values."""

    AVAILABLE = "available"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DROPPED = "dropped"
    ALL = "all"


class TagAvailabilityFilter(StrEnum):
    """Tag availability filter values."""

    AVAILABLE = "available"
    BLOCKED = "blocked"
    DROPPED = "dropped"
    ALL = "all"


class FolderAvailabilityFilter(StrEnum):
    """Folder availability filter values."""

    AVAILABLE = "available"
    DROPPED = "dropped"
    ALL = "all"
