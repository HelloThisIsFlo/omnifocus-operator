"""Create-task contracts: command, result, repo payload."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from omnifocus_operator.agent_messages.descriptions import (
    ADD_TASK_RESULT_DOC,
    COMPLETES_WITH_CHILDREN_WRITE,
    DATE_EXAMPLE,
    DEFER_DATE_WRITE,
    DUE_DATE_WRITE,
    ESTIMATED_MINUTES,
    FLAGGED,
    NAME_ADD_COMMAND,
    NOTE_ADD_COMMAND,
    PARENT,
    PLANNED_DATE_WRITE,
    TAGS_ADD_COMMAND,
    TASK_TYPE_WRITE,
)
from omnifocus_operator.agent_messages.errors import (
    ADD_COMPLETES_WITH_CHILDREN_NULL,
    ADD_PARENT_NULL,
    ADD_TASK_TYPE_NULL,
)
from omnifocus_operator.contracts.base import UNSET, CommandModel, Patch
from omnifocus_operator.contracts.shared.dates import validate_date_string
from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleAddSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import TaskType


class AddTaskCommand(CommandModel):
    name: str = Field(min_length=1, description=NAME_ADD_COMMAND)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: object) -> object:
        """Strip whitespace before min_length check."""
        return v.strip() if isinstance(v, str) else v

    parent: Patch[str] = Field(
        default=UNSET,
        description=PARENT,
    )

    @field_validator("parent", mode="before")
    @classmethod
    def _reject_null_parent(cls, v: object) -> object:
        if v is None:
            msg = ADD_PARENT_NULL
            raise ValueError(msg)
        return v

    tags: list[str] | None = Field(
        default=None,
        description=TAGS_ADD_COMMAND,
    )
    due_date: str | None = Field(
        default=None,
        description=DUE_DATE_WRITE,
        examples=[DATE_EXAMPLE],
    )
    defer_date: str | None = Field(
        default=None,
        description=DEFER_DATE_WRITE,
        examples=[DATE_EXAMPLE],
    )
    planned_date: str | None = Field(
        default=None,
        description=PLANNED_DATE_WRITE,
        examples=[DATE_EXAMPLE],
    )

    @field_validator("due_date", "defer_date", "planned_date", mode="before")
    @classmethod
    def _check_date_format(cls, v: object) -> object:
        return validate_date_string(v)

    flagged: bool = Field(default=False, description=FLAGGED)

    # PROP-01 / PROP-02 / PROP-05 / PROP-06 (plan 56-06):
    # Agent-writable task type fields. Patch semantics — omit to use the
    # user's OmniFocus preference (service resolves via OmniFocusPreferences
    # before building the repo payload), set to explicit value to override.
    # null rejected on both (no cleared state for booleans or enums).
    # `"singleActions"` rejected NATURALLY via TaskType enum — no custom
    # messaging (PROP-03 lock).
    completes_with_children: Patch[bool] = Field(
        default=UNSET, description=COMPLETES_WITH_CHILDREN_WRITE
    )
    type: Patch[TaskType] = Field(default=UNSET, description=TASK_TYPE_WRITE)

    @field_validator("completes_with_children", mode="before")
    @classmethod
    def _reject_null_completes_with_children(cls, v: object) -> object:
        if v is None:
            msg = ADD_COMPLETES_WITH_CHILDREN_NULL
            raise ValueError(msg)
        return v

    @field_validator("type", mode="before")
    @classmethod
    def _reject_null_task_type(cls, v: object) -> object:
        if v is None:
            msg = ADD_TASK_TYPE_NULL
            raise ValueError(msg)
        return v

    estimated_minutes: float | None = Field(default=None, description=ESTIMATED_MINUTES)
    note: str | None = Field(default=None, description=NOTE_ADD_COMMAND)
    repetition_rule: RepetitionRuleAddSpec | None = None


class AddTaskResult(OmniFocusBaseModel):
    __doc__ = ADD_TASK_RESULT_DOC

    status: Literal["success", "error", "skipped"]
    id: str | None = None
    name: str | None = None
    error: str | None = None
    warnings: list[str] | None = None


class AddTaskRepoPayload(CommandModel):
    """Bridge-ready payload for task creation. Service has resolved all fields.

    `completes_with_children` and `type` are REQUIRED — the service pipeline
    MUST resolve both (from agent value or user preference) before building
    the payload. The server never relies on OmniFocus's implicit defaulting
    (PROP-05 / PROP-06).
    """

    name: str
    parent: str | None = None
    tag_ids: list[str] | None = None
    due_date: str | None = None
    defer_date: str | None = None
    planned_date: str | None = None
    flagged: bool = False
    completes_with_children: bool  # required — service resolves (PROP-05)
    type: str  # required — service resolves; str because TaskType serialises as str (PROP-06)
    estimated_minutes: float | None = None
    note: str | None = None
    repetition_rule: RepetitionRuleRepoPayload | None = None


class AddTaskRepoResult(OmniFocusBaseModel):
    """Minimal confirmation from bridge after task creation."""

    id: str
    name: str


__all__ = [
    "AddTaskCommand",
    "AddTaskRepoPayload",
    "AddTaskRepoResult",
    "AddTaskResult",
]
