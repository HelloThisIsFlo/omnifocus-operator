"""Common models: entity base classes, nested reference types."""

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
    """Base fields shared by all OmniFocus entity types: id, name, url, timestamps."""

    id: str
    name: str
    url: str
    added: AwareDatetime
    modified: AwareDatetime


class ActionableEntity(OmniFocusEntity):
    """Shared fields for tasks and projects: status, dates, flags, tags, repetition rules."""

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
