"""Structured repetition rule models for OmniFocus tasks and projects.

Flat model:
    FrequencyType   -- Literal type alias for 6 frequency types
    Frequency       -- flat model with type + optional specialization fields
                       @model_validator for cross-type checks
                       @field_validator for day code / ordinal / on_dates normalization

    EndByDate / EndByOccurrences -- end condition models
    EndCondition = EndByDate | EndByOccurrences

    RepetitionRule  -- frequency + schedule + based_on + end
                       @field_serializer for interval=1 suppression via exclude_defaults

Enums:
    Schedule -- from enums.py (regularly, regularly_with_catch_up, from_completion)
    BasedOn  -- from enums.py (due_date, defer_date, planned_date)
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Annotated, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

from pydantic import Field, field_serializer, field_validator, model_validator

from omnifocus_operator.agent_messages.errors import (
    REPETITION_INVALID_DAY_CODE,
    REPETITION_INVALID_DAY_NAME,
    REPETITION_INVALID_END_OCCURRENCES,
    REPETITION_INVALID_INTERVAL,
    REPETITION_INVALID_ON_DATE,
    REPETITION_INVALID_ORDINAL,
)
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import BasedOn, Schedule

# -- Frequency Type -----------------------------------------------------------

FrequencyType = Literal["minutely", "hourly", "daily", "weekly", "monthly", "yearly"]
DayCode = Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
OnDate = Annotated[int, Field(ge=-1, le=31, description="Days of the month. Use -1 for last day.")]

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


# -- Shared validation functions ----------------------------------------------
# Standalone logic shared by Frequency (read model) and FrequencyAddSpec /
# FrequencyEditSpec (write contracts). Pydantic validators can't be inherited
# across unrelated class hierarchies, so each class wires thin decorator
# delegates that call these functions.


def validate_interval(v: int) -> int:
    if isinstance(v, int) and v < 1:
        raise ValueError(REPETITION_INVALID_INTERVAL.format(value=v))
    return v


def normalize_day_codes(value: list[str] | None) -> list[str] | None:
    if value is None:
        return None
    normalized = []
    for code in value:
        upper = code.upper()
        if upper not in _VALID_DAY_CODES:
            raise ValueError(REPETITION_INVALID_DAY_CODE.format(code=code))
        normalized.append(upper)
    return normalized


def normalize_on(value: dict[str, str] | None) -> dict[str, str] | None:
    if value is None:
        return None
    normalized = {}
    for ordinal, day_name in value.items():
        lower_ordinal = ordinal.lower()
        lower_day = day_name.lower()
        if lower_ordinal not in _VALID_ORDINALS:
            raise ValueError(REPETITION_INVALID_ORDINAL.format(ordinal=ordinal))
        if lower_day not in _VALID_DAY_NAMES:
            raise ValueError(REPETITION_INVALID_DAY_NAME.format(day=day_name))
        normalized[lower_ordinal] = lower_day
    return normalized


def validate_on_dates(value: list[int] | None) -> list[int] | None:
    if value is None:
        return None
    for v in value:
        if v == 0 or v < -1 or v > 31:
            raise ValueError(REPETITION_INVALID_ON_DATE.format(value=v))
    return value


def check_frequency_cross_type_fields(
    type_: str,
    on_days: Sequence[str] | None,
    on: dict[str, str] | None,
    on_dates: list[int] | None,
) -> None:
    if on_days is not None and type_ != "weekly":
        raise ValueError(
            f"on_days is not valid for type '{type_}'. on_days can only be used with type 'weekly'."
        )
    if on is not None and type_ != "monthly":
        raise ValueError(
            f"on is not valid for type '{type_}'. on can only be used with type 'monthly'."
        )
    if on_dates is not None and type_ != "monthly":
        raise ValueError(
            f"on_dates is not valid for type '{type_}'. "
            "on_dates can only be used with type 'monthly'."
        )
    if on is not None and on_dates is not None:
        raise ValueError(
            "on and on_dates are mutually exclusive on monthly frequency. "
            "Use on for day-of-week patterns (e.g., {'second': 'tuesday'}) "
            "or onDates for specific dates (e.g., [1, 15])."
        )


# -- Frequency Model ---------------------------------------------------------
# Cross-type rules: on_days only with weekly, on/on_dates only with monthly.
# on and on_dates are mutually exclusive. Enforced by check_frequency_cross_type_fields().


class Frequency(OmniFocusBaseModel):
    """How often the task repeats: type + interval, with optional day/date refinements."""

    type: FrequencyType  # required, NO default -- survives exclude_defaults
    interval: int = Field(default=1)
    on_days: list[str] | None = Field(
        default=None, description="Days of the week for weekly recurrence."
    )
    on: dict[str, str] | None = Field(
        default=None,
        description=(
            "Ordinal weekday as {ordinal: day}. "
            "Ordinal: first, second, third, fourth, fifth, last. "
            "Day: monday-sunday, weekday, weekend_day."
        ),
    )
    on_dates: list[int] | None = None

    @model_validator(mode="after")
    def _check_cross_type_fields(self) -> Frequency:
        check_frequency_cross_type_fields(self.type, self.on_days, self.on, self.on_dates)
        return self

    @field_validator("interval", mode="before")
    @classmethod
    def _validate_interval(cls, v: int) -> int:
        return validate_interval(v)

    @field_validator("on_days", mode="before")
    @classmethod
    def _normalize_day_codes(cls, value: list[str] | None) -> list[str] | None:
        return normalize_day_codes(value)

    @field_validator("on", mode="before")
    @classmethod
    def _normalize_on(cls, value: dict[str, str] | None) -> dict[str, str] | None:
        return normalize_on(value)

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, value: list[int] | None) -> list[int] | None:
        return validate_on_dates(value)


# -- End Condition Models -----------------------------------------------------


class EndByDate(OmniFocusBaseModel):
    """End condition: repeat until a specific date."""

    date: str = Field(description="Repeat until this date. ISO 8601 with timezone (offset or Z).")


class EndByOccurrences(OmniFocusBaseModel):
    """End condition: repeat a fixed number of times."""

    occurrences: int

    @field_validator("occurrences", mode="before")
    @classmethod
    def _validate_occurrences(cls, v: int) -> int:
        if isinstance(v, int) and v < 1:
            raise ValueError(REPETITION_INVALID_END_OCCURRENCES.format(value=v))
        return v


EndCondition = EndByDate | EndByOccurrences


# -- RepetitionRule -----------------------------------------------------------


class RepetitionRule(OmniFocusBaseModel):
    """Structured repetition rule for recurring tasks and projects."""

    frequency: Frequency
    schedule: Schedule
    based_on: BasedOn  # serializes as basedOn
    end: EndCondition | None = None

    @field_serializer("frequency")
    def _serialize_frequency(self, freq: Frequency, _info: Any) -> dict[str, Any]:
        return freq.model_dump(exclude_defaults=True, by_alias=True)


__all__ = [
    "DayCode",
    "EndByDate",
    "EndByOccurrences",
    "EndCondition",
    "Frequency",
    "FrequencyType",
    "OnDate",
    "RepetitionRule",
    "check_frequency_cross_type_fields",
    "normalize_day_codes",
    "normalize_on",
    "validate_interval",
    "validate_on_dates",
]
