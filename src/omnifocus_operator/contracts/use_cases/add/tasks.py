"""Create-task contracts: command, result, repo payload."""

from __future__ import annotations

from pydantic import AwareDatetime, Field, field_validator

from omnifocus_operator.contracts.base import CommandModel
from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleAddSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.base import OmniFocusBaseModel


class AddTaskCommand(CommandModel):
    name: str = Field(min_length=1)

    @field_validator("name", mode="before")
    @classmethod
    def _strip_name(cls, v: object) -> object:
        """Strip whitespace before min_length check."""
        return v.strip() if isinstance(v, str) else v

    parent: str | None = Field(
        default=None,
        description="Project or task ID to place this task under. Omit for inbox.",
    )
    tags: list[str] | None = Field(
        default=None,
        description="Tag names (case-insensitive) or IDs; you can mix both in one list. "
        "Non-existent names are rejected. "
        "Ambiguous names (case-insensitive collision) return an error.",
    )
    due_date: AwareDatetime | None = Field(
        default=None,
        description="Deadline with real consequences if missed. "
        "Not for intentions -- use plannedDate instead. "
        "Requires timezone (ISO 8601 with offset or Z); naive datetimes are rejected.",
    )
    defer_date: AwareDatetime | None = Field(
        default=None,
        description="Task cannot be acted on until this date. "
        "Hidden from most views until then. "
        "Not for 'I don't want to work on it yet' -- use plannedDate for that. "
        "Requires timezone (ISO 8601 with offset or Z); naive datetimes are rejected.",
    )
    planned_date: AwareDatetime | None = Field(
        default=None,
        description="When you intend to work on this task. "
        "No urgency signal, no visibility change, no penalty for missing it. "
        "Requires timezone (ISO 8601 with offset or Z); naive datetimes are rejected.",
    )
    flagged: bool = False
    estimated_minutes: float | None = None
    note: str | None = None
    repetition_rule: RepetitionRuleAddSpec | None = None


class AddTaskResult(OmniFocusBaseModel):
    """Agent-facing outcome of task creation."""

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
