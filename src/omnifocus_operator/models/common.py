"""Common models: entity base classes, nested reference types."""

from __future__ import annotations

from pydantic import AwareDatetime, Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    DEFER_DATE,
    DUE_DATE,
    EFFECTIVE_DEFER_DATE,
    EFFECTIVE_DROP_DATE,
    EFFECTIVE_DUE_DATE,
    EFFECTIVE_FLAGGED,
    EFFECTIVE_PLANNED_DATE,
    FOLDER_REF_DOC,
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
    effective_flagged: bool = Field(
        description=EFFECTIVE_FLAGGED,
    )

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
    effective_due_date: AwareDatetime | None = Field(
        default=None,
        description=EFFECTIVE_DUE_DATE,
    )
    effective_defer_date: AwareDatetime | None = Field(
        default=None,
        description=EFFECTIVE_DEFER_DATE,
    )
    effective_planned_date: AwareDatetime | None = Field(
        default=None,
        description=EFFECTIVE_PLANNED_DATE,
    )
    # effective_completion_date is only present on Task, not Project
    effective_drop_date: AwareDatetime | None = Field(
        default=None,
        description=EFFECTIVE_DROP_DATE,
    )

    # Metadata
    estimated_minutes: float | None = None
    has_children: bool

    # Relationships
    tags: list[TagRef] = Field(
        default_factory=list,
        description=TAGS_OUTPUT,
    )
    repetition_rule: RepetitionRule | None = None
