"""Input validation -- pure checks on user-provided values."""

from __future__ import annotations

from omnifocus_operator.contracts.base import is_set

__all__ = ["validate_task_name", "validate_task_name_if_set"]


def validate_task_name(name: str | None) -> None:
    """Raise ValueError if name is empty or whitespace."""
    if not name or not name.strip():
        msg = "Task name is required"
        raise ValueError(msg)


def validate_task_name_if_set(name: object) -> None:
    """Raise ValueError if name is provided but empty/whitespace.

    Accepts ``_Unset`` (no-op) or a string. If string, validates
    it is non-empty.
    """
    if not is_set(name):
        return
    if not name or not str(name).strip():
        msg = "Task name cannot be empty"
        raise ValueError(msg)
