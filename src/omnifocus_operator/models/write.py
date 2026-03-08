"""Write models for OmniFocus task creation.

These models define the input (spec) and output (result) contracts
for write operations. They are intentionally simpler than the rich
read models -- write specs contain only user-settable fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.base import OmniFocusBaseModel

if TYPE_CHECKING:
    from pydantic import AwareDatetime


class TaskCreateSpec(OmniFocusBaseModel):
    """Input model for task creation.

    Only ``name`` is required. All other fields default to ``None``,
    meaning OmniFocus will use its own defaults (e.g. unflagged, no
    due date, inbox placement).
    """

    name: str
    parent: str | None = None
    tags: list[str] | None = None
    due_date: AwareDatetime | None = None
    defer_date: AwareDatetime | None = None
    planned_date: AwareDatetime | None = None
    flagged: bool | None = None
    estimated_minutes: float | None = None
    note: str | None = None


class TaskCreateResult(OmniFocusBaseModel):
    """Result model returned after creating a task.

    Contains the minimal confirmation data: whether it succeeded,
    the OmniFocus-assigned ID, and the task name.
    """

    success: bool
    id: str
    name: str
