"""Status, repetition, and entity-type enumerations for OmniFocus entities.

Values use snake_case strings matching the new two-axis model:
- EntityType: top-level entity kind (project, task, tag)
- Urgency: time pressure axis (overdue, due_soon, none)
- Availability: work readiness axis (available, blocked, completed, dropped)
- TagAvailability: tag availability (available, blocked, dropped)
- FolderAvailability: folder availability (available, dropped)
- Schedule: repetition schedule type (regularly, regularly_with_catch_up, from_completion)
- BasedOn: anchor date for repetition rules (due_date, defer_date, planned_date)
- DueSoonSetting: OmniFocus "due soon" threshold preference (7 discrete options)
"""

from enum import Enum, StrEnum

from omnifocus_operator.agent_messages.descriptions import (
    AVAILABILITY_DOC,
    BASED_ON_DOC,
    FOLDER_AVAILABILITY_DOC,
    SCHEDULE_DOC,
    TAG_AVAILABILITY_DOC,
    URGENCY_DOC,
)


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


class TaskType(StrEnum):
    """Per-type enum for tasks: parallel or sequential action groups.

    Tasks have only two options. Projects have a third (`singleActions`)
    captured by the separate `ProjectType` enum -- see HIER-05 for the
    precedence rule that distinguishes the two.
    """

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"


class ProjectType(StrEnum):
    """Per-type enum for projects: parallel, sequential, or singleActions.

    `singleActions` takes precedence over `sequential` when both underlying
    flags are set on the same project (HIER-05). The repository materialises
    the value directly from `(sequential, containsSingletonActions)` columns
    on the project's `Task` + `ProjectInfo` rows.
    """

    PARALLEL = "parallel"
    SEQUENTIAL = "sequential"
    SINGLE_ACTIONS = "singleActions"
