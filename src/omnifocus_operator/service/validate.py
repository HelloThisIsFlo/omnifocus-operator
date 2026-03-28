"""Input validation -- pure checks on user-provided values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.models.repetition_rule import WeeklyOnDaysFrequency

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.repetition_rule import RepetitionRuleAddSpec

__all__ = ["validate_repetition_rule_add", "validate_task_name", "validate_task_name_if_set"]


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


def validate_repetition_rule_add(spec: RepetitionRuleAddSpec) -> RepetitionRuleAddSpec:
    """Validate and normalize a repetition rule add spec.

    - Normalizes on_days to uppercase (WeeklyOnDaysFrequency)
    - Validates interval >= 1

    Returns the (possibly normalized) spec.
    """
    if spec.frequency.interval < 1:
        msg = f"Frequency interval must be >= 1, got {spec.frequency.interval}"
        raise ValueError(msg)

    # Normalize on_days to uppercase for WeeklyOnDaysFrequency
    if isinstance(spec.frequency, WeeklyOnDaysFrequency):
        normalized_days = [d.upper() for d in spec.frequency.on_days]
        if normalized_days != spec.frequency.on_days:
            new_freq = spec.frequency.model_copy(update={"on_days": normalized_days})
            spec = spec.model_copy(update={"frequency": new_freq})

    return spec
