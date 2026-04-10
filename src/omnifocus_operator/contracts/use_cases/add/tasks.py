"""Create-task contracts: command, result, repo payload."""

from __future__ import annotations

from datetime import datetime as _datetime

from pydantic import Field, field_validator

from omnifocus_operator.agent_messages.descriptions import (
    ADD_TASK_RESULT_DOC,
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
)
from omnifocus_operator.agent_messages.errors import ADD_PARENT_NULL, INVALID_DATE_FORMAT
from omnifocus_operator.contracts.base import UNSET, CommandModel, Patch
from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleAddSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.base import OmniFocusBaseModel


def _validate_date_string(v: object) -> object:
    """Validate that a string is a parseable ISO date or datetime (syntax only)."""
    if not isinstance(v, str):
        return v
    try:
        _datetime.fromisoformat(v)
    except ValueError:
        raise ValueError(INVALID_DATE_FORMAT.format(value=v)) from None
    return v


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
        return _validate_date_string(v)

    flagged: bool = Field(default=False, description=FLAGGED)
    estimated_minutes: float | None = Field(default=None, description=ESTIMATED_MINUTES)
    note: str | None = Field(default=None, description=NOTE_ADD_COMMAND)
    repetition_rule: RepetitionRuleAddSpec | None = None


class AddTaskResult(OmniFocusBaseModel):
    __doc__ = ADD_TASK_RESULT_DOC

    success: bool
    id: str
    name: str
    warnings: list[str] | None = None


class AddTaskRepoPayload(CommandModel):
    """Bridge-ready payload for task creation. Service has resolved all fields."""

    name: str
    parent: str | None = None
    tag_ids: list[str] | None = None
    due_date: str | None = None
    defer_date: str | None = None
    planned_date: str | None = None
    flagged: bool = False
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
