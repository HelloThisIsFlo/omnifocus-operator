"""Common standalone models used as nested types in Task and Project.

These models represent nested objects in the bridge JSON output:
- TagRef: tag reference with id and name
- RepetitionRule: from bridge rr() function (4 required fields)
- ReviewInterval: from bridge ri() function
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import OmniFocusBaseModel

if TYPE_CHECKING:
    from omnifocus_operator.models.enums import AnchorDateKey, ScheduleType


class TagRef(OmniFocusBaseModel):
    """Reference to a tag with both id and name for ergonomics."""

    id: str
    name: str


class ParentRef(OmniFocusBaseModel):
    """Reference to a parent entity (project or task) with type, id, and name.

    type is "project" for tasks directly in a project, "task" for subtasks.
    Inbox tasks have no ParentRef (represented as None at the Task level).
    """

    type: str
    id: str
    name: str


class RepetitionRule(OmniFocusBaseModel):
    """Repetition rule for recurring tasks and projects.

    All 4 fields are required -- the bridge rr() resolver extracts them
    from OmniFocus's RepetitionRule object. Null repetition rules are
    represented as None at the parent level (task/project), not as a
    RepetitionRule with optional fields.
    """

    rule_string: str
    schedule_type: ScheduleType
    anchor_date_key: AnchorDateKey
    catch_up_automatically: bool


class ReviewInterval(OmniFocusBaseModel):
    """Review interval for project review scheduling.

    Serializes to: {"steps": N, "unit": "..."}
    """

    steps: int
    unit: str
