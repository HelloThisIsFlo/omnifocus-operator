"""Status, repetition, and entity-type enumerations for OmniFocus entities.

Values use snake_case strings matching the new two-axis model:
- EntityType: top-level entity kind (project, task, tag)
- Urgency: time pressure axis (overdue, due_soon, none)
- Availability: work readiness axis (available, blocked, completed, dropped)
- TagAvailability: tag availability (available, blocked, dropped)
- FolderAvailability: folder availability (available, dropped)
- Schedule: repetition schedule type (regularly, regularly_with_catch_up, from_completion)
- BasedOn: anchor date for repetition rules (due_date, defer_date, planned_date)
"""

from enum import StrEnum

from omnifocus_operator.agent_messages.descriptions import (
    AVAILABILITY_DOC,
    BASED_ON_DOC,
    FOLDER_AVAILABILITY_DOC,
    SCHEDULE_DOC,
    TAG_AVAILABILITY_DOC,
    URGENCY_DOC,
)


class EntityType(StrEnum):
    PROJECT = "project"
    TASK = "task"
    TAG = "tag"


class Urgency(StrEnum):
    __doc__ = URGENCY_DOC

    OVERDUE = "overdue"
    DUE_SOON = "due_soon"
    NONE = "none"


class Availability(StrEnum):
    __doc__ = AVAILABILITY_DOC

    AVAILABLE = "available"
    BLOCKED = "blocked"
    COMPLETED = "completed"
    DROPPED = "dropped"


class TagAvailability(StrEnum):
    __doc__ = TAG_AVAILABILITY_DOC

    AVAILABLE = "available"
    BLOCKED = "blocked"
    DROPPED = "dropped"


class FolderAvailability(StrEnum):
    __doc__ = FOLDER_AVAILABILITY_DOC

    AVAILABLE = "available"
    DROPPED = "dropped"


class Schedule(StrEnum):
    __doc__ = SCHEDULE_DOC

    REGULARLY = "regularly"
    REGULARLY_WITH_CATCH_UP = "regularly_with_catch_up"
    FROM_COMPLETION = "from_completion"


class BasedOn(StrEnum):
    __doc__ = BASED_ON_DOC

    DUE_DATE = "due_date"
    DEFER_DATE = "defer_date"
    PLANNED_DATE = "planned_date"
