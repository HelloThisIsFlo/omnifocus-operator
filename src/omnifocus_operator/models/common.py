"""Common models: entity base classes, nested reference types."""

from __future__ import annotations

from pydantic import AwareDatetime, Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    COMPLETES_WITH_CHILDREN_DESC,
    DEFER_DATE,
    DUE_DATE,
    FOLDER_REF_DOC,
    HAS_ATTACHMENTS_DESC,
    HAS_NOTE_DESC,
    HAS_REPETITION_DESC,
    IS_SEQUENTIAL_DESC,
    PARENT_REF_DOC,
    PARENT_REF_PROJECT_FIELD,
    PARENT_REF_TASK_FIELD,
    PLANNED_DATE,
    PROJECT_REF_DOC,
    REVIEW_INTERVAL_DOC,
    TAG_REF_DOC,
    TAGS_OUTPUT,
    TASK_REF_DOC,
)
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import Availability, Urgency
from omnifocus_operator.models.repetition_rule import RepetitionRule


class TagRef(OmniFocusBaseModel):
    __doc__ = TAG_REF_DOC

    id: str
    name: str


class ProjectRef(OmniFocusBaseModel):
    __doc__ = PROJECT_REF_DOC

    id: str
    name: str


class TaskRef(OmniFocusBaseModel):
    __doc__ = TASK_REF_DOC

    id: str
    name: str


class FolderRef(OmniFocusBaseModel):
    __doc__ = FOLDER_REF_DOC

    id: str
    name: str


class ParentRef(OmniFocusBaseModel):
    __doc__ = PARENT_REF_DOC

    project: ProjectRef | None = Field(default=None, description=PARENT_REF_PROJECT_FIELD)
    task: TaskRef | None = Field(default=None, description=PARENT_REF_TASK_FIELD)

    @model_validator(mode="after")
    def _exactly_one_key(self) -> ParentRef:
        has_project = self.project is not None
        has_task = self.task is not None
        if has_project == has_task:
            msg = "Exactly one of 'project' or 'task' must be set."
            raise ValueError(msg)
        return self


class ReviewInterval(OmniFocusBaseModel):
    __doc__ = REVIEW_INTERVAL_DOC

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

    # Dates (all optional, timezone-aware)
    due_date: AwareDatetime | None = Field(
        default=None,
        description=DUE_DATE,
    )
    defer_date: AwareDatetime | None = Field(
        default=None,
        description=DEFER_DATE,
    )
    planned_date: AwareDatetime | None = Field(
        default=None,
        description=PLANNED_DATE,
    )
    completion_date: AwareDatetime | None = None
    drop_date: AwareDatetime | None = None

    # Metadata
    estimated_minutes: float | None = None
    has_children: bool
    has_note: bool = Field(description=HAS_NOTE_DESC)
    has_repetition: bool = Field(description=HAS_REPETITION_DESC)
    has_attachments: bool = Field(description=HAS_ATTACHMENTS_DESC)
    completes_with_children: bool = Field(description=COMPLETES_WITH_CHILDREN_DESC)

    # Derived presence flag (FLAG-04 — applies to tasks AND projects).
    # Populated by `DomainLogic.enrich_task_presence_flags` (tasks) or
    # `DomainLogic.enrich_project_presence_flags` (projects). Default is
    # `False` so the field stays safe if enrichment is somehow bypassed.
    # Projects with `type == 'singleActions'` resolve to is_sequential=False
    # (HIER-05 precedence); only `type == 'sequential'` yields True.
    is_sequential: bool = Field(default=False, description=IS_SEQUENTIAL_DESC)

    # Relationships
    tags: list[TagRef] = Field(
        default_factory=list,
        description=TAGS_OUTPUT,
    )
    repetition_rule: RepetitionRule | None = None
