"""Edit-task contracts: command, actions, result, repo payload."""

from __future__ import annotations

from typing import Literal

from pydantic import AwareDatetime, Field, field_validator

from omnifocus_operator.agent_messages.descriptions import (
    DEFER_DATE_WRITE,
    DUE_DATE_WRITE,
    EDIT_TASK_ACTIONS_DOC,
    EDIT_TASK_RESULT_DOC,
    PLANNED_DATE_WRITE,
)
from omnifocus_operator.agent_messages.errors import LIFECYCLE_INVALID_VALUE
from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
)
from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
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

    @field_validator("lifecycle", mode="before")
    @classmethod
    def _validate_lifecycle(cls, v: object) -> object:
        if isinstance(v, str) and v not in ("complete", "drop"):
            raise ValueError(LIFECYCLE_INVALID_VALUE.format(value=v))
        return v


class EditTaskCommand(CommandModel):
    # Required -- which task to edit
    id: str

    # Value-only fields (no None -- these can't be "cleared")
    name: Patch[str] = UNSET
    flagged: Patch[bool] = UNSET

    @field_validator("name", mode="before")
    @classmethod
    def _validate_name(cls, v: object) -> object:
        """Strip whitespace and reject empty names. Passes _Unset through."""
        if isinstance(v, str):
            v = v.strip()
            if not v:
                raise ValueError("Task name cannot be empty")
        return v

    # Clearable fields (None = clear the value)
    note: PatchOrClear[str] = UNSET
    due_date: PatchOrClear[AwareDatetime] = Field(
        default=UNSET,
        description=DUE_DATE_WRITE,
    )
    defer_date: PatchOrClear[AwareDatetime] = Field(
        default=UNSET,
        description=DEFER_DATE_WRITE,
    )
    planned_date: PatchOrClear[AwareDatetime] = Field(
        default=UNSET,
        description=PLANNED_DATE_WRITE,
    )
    estimated_minutes: PatchOrClear[float] = UNSET

    # Repetition rule (nested spec with own patch semantics; null = clear, UNSET = no change)
    repetition_rule: PatchOrClear[RepetitionRuleEditSpec] = UNSET

    # Stateful operations
    actions: Patch[EditTaskActions] = UNSET


class EditTaskResult(OmniFocusBaseModel):
    __doc__ = EDIT_TASK_RESULT_DOC

    success: bool
    id: str
    name: str
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
