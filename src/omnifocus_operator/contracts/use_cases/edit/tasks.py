"""Edit-task contracts: command, actions, repo payload, repo result, result.

Defines the full typed contract for the edit-task use case across
both the agent boundary (Command/Result) and the repository boundary
(RepoPayload/RepoResult).

Relocated from contracts/use_cases/edit_task.py to per-use-case package.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Literal

from pydantic import field_validator

from omnifocus_operator.agent_messages.errors import LIFECYCLE_INVALID_VALUE
from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
)
from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.base import OmniFocusBaseModel

if TYPE_CHECKING:
    from pydantic import AwareDatetime

    from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction


class EditTaskActions(CommandModel):
    """Stateful operations grouped under the actions block."""

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
    """Agent instruction to edit a task (patch semantics)."""

    # Required -- which task to edit
    id: str

    # Value-only fields (no None -- these can't be "cleared")
    name: Patch[str] = UNSET
    flagged: Patch[bool] = UNSET

    # Clearable fields (None = clear the value)
    note: PatchOrClear[str] = UNSET
    due_date: PatchOrClear[AwareDatetime] = UNSET
    defer_date: PatchOrClear[AwareDatetime] = UNSET
    planned_date: PatchOrClear[AwareDatetime] = UNSET
    estimated_minutes: PatchOrClear[float] = UNSET

    # Repetition rule (nested spec with own patch semantics; null = clear, UNSET = no change)
    repetition_rule: PatchOrClear[RepetitionRuleEditSpec] = UNSET

    # Stateful operations
    actions: Patch[EditTaskActions] = UNSET


class EditTaskResult(OmniFocusBaseModel):
    """Agent-facing outcome of task editing."""

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
