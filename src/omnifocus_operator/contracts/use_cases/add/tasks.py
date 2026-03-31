"""Create-task contracts: command, repo payload, repo result, result.

Defines the full typed contract for the create-task use case across
both the agent boundary (Command/Result) and the repository boundary
(RepoPayload/RepoResult).

Relocated from contracts/use_cases/add_task.py to per-use-case package.
"""

from __future__ import annotations

from pydantic import AwareDatetime

from omnifocus_operator.contracts.base import CommandModel
from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleAddSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.base import OmniFocusBaseModel


class AddTaskCommand(CommandModel):
    """Agent instruction to create a task."""

    name: str
    parent: str | None = None
    tags: list[str] | None = None
    due_date: AwareDatetime | None = None
    defer_date: AwareDatetime | None = None
    planned_date: AwareDatetime | None = None
    flagged: bool | None = None
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
    flagged: bool | None = None
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
