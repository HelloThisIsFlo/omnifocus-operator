"""Common models and entity base classes.

Standalone nested types:
- TagRef: tag reference with id and name
- ParentRef: parent reference with type, id, and name
- ReviewInterval: from bridge ri() function

Entity base classes (moved here to break circular imports with base.py):
- OmniFocusEntity: id, name, url, added, modified
- ActionableEntity: urgency, availability, dates, flags, tags, repetition
"""

from __future__ import annotations

from pydantic import AwareDatetime, Field

from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import Availability, Urgency
from omnifocus_operator.models.repetition_rule import RepetitionRule


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


class OmniFocusEntity(OmniFocusBaseModel):
    """Entity with identity and universal fields shared by all OmniFocus object types.

    All four entity types (Task, Project, Tag, Folder) have these fields.
    Perspective does NOT inherit from this class (nullable id, no lifecycle fields).
    """

    id: str
    name: str
    url: str
    added: AwareDatetime
    modified: AwareDatetime


class ActionableEntity(OmniFocusEntity):
    """Shared fields for Task and Project (status axes, dates, flags, relationships).

    Fields here are present on BOTH tasks and projects.
    Entity-specific fields (e.g. inInbox for Task, folder for Project) live on
    the concrete model classes.
    """

    # Two-axis status model
    urgency: Urgency
    availability: Availability

    # Content
    note: str

    # Flags
    flagged: bool
    effective_flagged: bool

    # Dates (all optional, timezone-aware)
    due_date: AwareDatetime | None = None
    defer_date: AwareDatetime | None = None
    planned_date: AwareDatetime | None = None
    completion_date: AwareDatetime | None = None
    drop_date: AwareDatetime | None = None
    effective_due_date: AwareDatetime | None = None
    effective_defer_date: AwareDatetime | None = None
    effective_planned_date: AwareDatetime | None = None
    # effective_completion_date is only present on Task, not Project
    effective_drop_date: AwareDatetime | None = None

    # Metadata
    estimated_minutes: float | None = None
    has_children: bool

    # Relationships
    tags: list[TagRef] = Field(default_factory=list)  # Tag references (id + name objects)
    repetition_rule: RepetitionRule | None = None
