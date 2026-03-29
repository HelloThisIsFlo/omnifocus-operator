"""Input validation -- pure checks on user-provided values.

With the flat Frequency model, all repetition rule validation has migrated
to Pydantic model validators on Frequency/FrequencyAddSpec. This module
retains only task name validation.
"""

from __future__ import annotations

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.contracts.base import is_set

__all__ = [
    "validate_task_name",
    "validate_task_name_if_set",
]

# --- Task name validation ---


def validate_task_name(name: str | None) -> None:
    """Raise ValueError if name is empty or whitespace."""
    if not name or not name.strip():
        raise ValueError(err.TASK_NAME_REQUIRED)


def validate_task_name_if_set(name: object) -> None:
    """Raise ValueError if name is provided but empty/whitespace.

    Accepts ``_Unset`` (no-op) or a string. If string, validates
    it is non-empty.
    """
    if not is_set(name):
        return
    if not name or not str(name).strip():
        raise ValueError(err.TASK_NAME_EMPTY)
