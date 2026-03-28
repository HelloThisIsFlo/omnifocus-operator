"""Common standalone models used as nested types in Task and Project.

These models represent nested objects in the bridge JSON output:
- TagRef: tag reference with id and name
- ParentRef: parent reference with type, id, and name
- ReviewInterval: from bridge ri() function
"""

from __future__ import annotations

from omnifocus_operator.models.base import OmniFocusBaseModel


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


class ReviewInterval(OmniFocusBaseModel):
    """Review interval for project review scheduling.

    Serializes to: {"steps": N, "unit": "..."}
    """

    steps: int
    unit: str
