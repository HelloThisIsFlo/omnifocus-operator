"""Status enumerations for OmniFocus entities.

Values match the exact strings produced by the bridge script:
- TaskStatus: from the ts() function mapping Task.Status values
- EntityStatus: from .status.name property on Project, Tag, Folder
"""

from enum import StrEnum


class TaskStatus(StrEnum):
    """Computed availability status for tasks (from bridge ts() function)."""

    AVAILABLE = "Available"
    BLOCKED = "Blocked"
    COMPLETED = "Completed"
    DROPPED = "Dropped"
    DUE_SOON = "DueSoon"
    NEXT = "Next"
    OVERDUE = "Overdue"


class EntityStatus(StrEnum):
    """Lifecycle status for projects, tags, and folders (from .status.name)."""

    ACTIVE = "Active"
    DONE = "Done"
    DROPPED = "Dropped"
