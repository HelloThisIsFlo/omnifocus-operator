"""Input validation -- pure checks on user-provided values."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.models.repetition_rule import (
    EndByOccurrences,
    EndCondition,
    Frequency,
    MonthlyDayInMonthFrequency,
    MonthlyDayOfWeekFrequency,
    WeeklyOnDaysFrequency,
)

if TYPE_CHECKING:
    from omnifocus_operator.contracts.use_cases.repetition_rule import RepetitionRuleAddSpec

__all__ = [
    "validate_repetition_rule_add",
    "validate_task_name",
    "validate_task_name_if_set",
]

# --- Task name validation ---


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


# --- Repetition rule validation ---

_VALID_DAY_CODES = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
_VALID_ORDINALS = {"first", "second", "third", "fourth", "fifth", "last"}
_VALID_DAY_NAMES = {
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "weekday",
    "weekend_day",
}


def validate_repetition_rule_add(spec: RepetitionRuleAddSpec) -> RepetitionRuleAddSpec:
    """Validate and normalize a repetition rule add spec. Returns the (possibly modified) spec.

    Validates:
    - interval >= 1
    - WeeklyOnDaysFrequency: on_days are valid day codes (MO-SU), normalizes to uppercase
    - MonthlyDayOfWeekFrequency: on dict has valid ordinal and day name
    - MonthlyDayInMonthFrequency: on_dates values in valid range (-1, 1-31)
    - EndByOccurrences: occurrences >= 1

    Raises ValueError with educational error messages on invalid input.
    """
    spec = _validate_and_normalize_frequency(spec)
    if spec.end is not None:
        _validate_end(spec.end)
    return spec


def _validate_and_normalize_frequency(spec: RepetitionRuleAddSpec) -> RepetitionRuleAddSpec:
    """Validate frequency fields and normalize day codes. Returns possibly modified spec."""
    frequency = spec.frequency
    _validate_interval(frequency)

    if isinstance(frequency, WeeklyOnDaysFrequency):
        spec = _normalize_on_days(spec, frequency)
    elif isinstance(frequency, MonthlyDayOfWeekFrequency) and frequency.on is not None:
        _validate_monthly_day_of_week(frequency.on)
    elif isinstance(frequency, MonthlyDayInMonthFrequency) and frequency.on_dates is not None:
        _validate_monthly_day_in_month(frequency.on_dates)

    return spec


def _validate_interval(frequency: Frequency) -> None:
    """Validate interval >= 1."""
    if frequency.interval < 1:
        raise ValueError(err.REPETITION_INVALID_INTERVAL.format(value=frequency.interval))


def _normalize_on_days(
    spec: RepetitionRuleAddSpec, frequency: WeeklyOnDaysFrequency
) -> RepetitionRuleAddSpec:
    """Validate and normalize day codes to uppercase."""
    normalized = []
    for code in frequency.on_days:
        upper = code.upper()
        if upper not in _VALID_DAY_CODES:
            raise ValueError(err.REPETITION_INVALID_DAY_CODE.format(code=code))
        normalized.append(upper)

    if normalized != frequency.on_days:
        # Create new frequency with normalized days and rebuild spec
        new_freq = frequency.model_copy(update={"on_days": normalized})
        spec = spec.model_copy(update={"frequency": new_freq})

    return spec


def _validate_monthly_day_of_week(on: dict[str, str]) -> None:
    """Validate ordinal and day name in the on dict."""
    for ordinal, day_name in on.items():
        if ordinal not in _VALID_ORDINALS:
            raise ValueError(err.REPETITION_INVALID_ORDINAL.format(ordinal=ordinal))
        if day_name not in _VALID_DAY_NAMES:
            raise ValueError(err.REPETITION_INVALID_DAY_NAME.format(day=day_name))


def _validate_monthly_day_in_month(on_dates: list[int]) -> None:
    """Validate on_dates values are in range (-1, 1-31)."""
    for value in on_dates:
        if value == 0 or value < -1 or value > 31:
            raise ValueError(err.REPETITION_INVALID_ON_DATE.format(value=value))


def _validate_end(end: EndCondition) -> None:
    """Validate end condition."""
    if isinstance(end, EndByOccurrences) and end.occurrences < 1:
        raise ValueError(err.REPETITION_INVALID_END_OCCURRENCES.format(value=end.occurrences))
