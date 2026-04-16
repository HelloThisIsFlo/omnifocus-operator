"""Edit-task contracts: command, actions, result, repo payload."""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator

from omnifocus_operator.agent_messages.descriptions import (
    DATE_EXAMPLE,
    DEFER_DATE_WRITE,
    DUE_DATE_WRITE,
    EDIT_TASK_ACTIONS_DOC,
    EDIT_TASK_RESULT_DOC,
    ESTIMATED_MINUTES_EDIT,
    FLAGGED,
    ID_EDIT_COMMAND,
    NAME_EDIT_COMMAND,
    PLANNED_DATE_WRITE,
)
from omnifocus_operator.agent_messages.errors import (
    LIFECYCLE_INVALID_VALUE,
    TASK_NAME_EMPTY,
)
from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
)
from omnifocus_operator.contracts.shared.actions import MoveAction, NoteAction, TagAction
from omnifocus_operator.contracts.shared.dates import validate_date_string
from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.base import OmniFocusBaseModel


class EditTaskActions(CommandModel):
    __doc__ = EDIT_TASK_ACTIONS_DOC

    tags: Patch[TagAction] = UNSET
    move: Patch[MoveAction] = UNSET
    lifecycle: Patch[Literal["complete", "drop"]] = UNSET
    note: Patch[NoteAction] = UNSET

    @field_validator("lifecycle", mode="before")
    @classmethod
    def _validate_lifecycle(cls, v: object) -> object:
        if isinstance(v, str) and v not in ("complete", "drop"):
            raise ValueError(LIFECYCLE_INVALID_VALUE.format(value=v))
        return v


class EditTaskCommand(CommandModel):
    # Required -- which task to edit
    id: str = Field(description=ID_EDIT_COMMAND)

    # Value-only fields (no None -- these can't be "cleared")
    name: Patch[str] = Field(default=UNSET, description=NAME_EDIT_COMMAND)
    flagged: Patch[bool] = Field(default=UNSET, description=FLAGGED)

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: object) -> object:
        """Strip whitespace and reject empty names. Passes _Unset through."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError(TASK_NAME_EMPTY)
        return v

    # Clearable fields (None = clear the value)
    due_date: PatchOrClear[str] = Field(
        default=UNSET,
        description=DUE_DATE_WRITE,
        examples=[DATE_EXAMPLE],
    )
    defer_date: PatchOrClear[str] = Field(
        default=UNSET,
        description=DEFER_DATE_WRITE,
        examples=[DATE_EXAMPLE],
    )
    planned_date: PatchOrClear[str] = Field(
        default=UNSET,
        description=PLANNED_DATE_WRITE,
        examples=[DATE_EXAMPLE],
    )

    @field_validator("due_date", "defer_date", "planned_date", mode="before")
    @classmethod
    def _check_date_format(cls, v: object) -> object:
        """Validate date string syntax. UNSET and None pass through (patch semantics)."""
        return validate_date_string(v)

    estimated_minutes: PatchOrClear[float] = Field(
        default=UNSET, description=ESTIMATED_MINUTES_EDIT
    )

    # Repetition rule (nested spec with own patch semantics; null = clear, UNSET = no change)
    repetition_rule: PatchOrClear[RepetitionRuleEditSpec] = UNSET

    # Stateful operations
    actions: Patch[EditTaskActions] = UNSET


class EditTaskResult(OmniFocusBaseModel):
    __doc__ = EDIT_TASK_RESULT_DOC

    status: Literal["success", "error", "skipped"]
    id: str | None = None
    name: str | None = None
    error: str | None = None
    warnings: list[str] | None = None


class MoveToRepoPayload(CommandModel):
    """Bridge-ready move instruction. Service has resolved and validated."""

    position: Literal["beginning", "ending", "before", "after"]
    container_id: str | None = None
    anchor_id: str | None = None


class EditTaskRepoPayload(CommandModel):
    """Bridge-ready payload for task editing. Only changed fields are set."""

    id: str
    name: str | None = None
    note: str | None = None
    flagged: bool | None = None
    estimated_minutes: float | None = None
    due_date: str | None = None
    defer_date: str | None = None
    planned_date: str | None = None
    add_tag_ids: list[str] | None = None
    remove_tag_ids: list[str] | None = None
    move_to: MoveToRepoPayload | None = None
    lifecycle: Literal["complete", "drop"] | None = None
    repetition_rule: RepetitionRuleRepoPayload | None = None


class EditTaskRepoResult(OmniFocusBaseModel):
    """Minimal confirmation from bridge after task editing."""

    id: str
    name: str


__all__ = [
    "EditTaskActions",
    "EditTaskCommand",
    "EditTaskRepoPayload",
    "EditTaskRepoResult",
    "EditTaskResult",
    "MoveToRepoPayload",
]
