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

from datetime import date as date_type
from typing import TYPE_CHECKING, Annotated, Any, Literal

if TYPE_CHECKING:
    from collections.abc import Sequence

from pydantic import ConfigDict, Field, field_serializer, field_validator, model_validator

from omnifocus_operator.agent_messages.errors import (
    REPETITION_AT_MOST_ONE_ORDINAL,
    REPETITION_INVALID_DAY_CODE,
    REPETITION_INVALID_DAY_NAME,
    REPETITION_INVALID_END_OCCURRENCES,
    REPETITION_INVALID_INTERVAL,
    REPETITION_INVALID_ON_DATE,
)
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import BasedOn, Schedule

# -- Frequency Type -----------------------------------------------------------

FrequencyType = Literal["minutely", "hourly", "daily", "weekly", "monthly", "yearly"]
DayCode = Literal["MO", "TU", "WE", "TH", "FR", "SA", "SU"]
OnDate = Annotated[int, Field(ge=-1, le=31, description="Days of the month. Use -1 for last day.")]

DayName = Literal[
    "monday",
    "tuesday",
    "wednesday",
    "thursday",
    "friday",
    "saturday",
    "sunday",
    "weekday",
    "weekend_day",
]

_VALID_DAY_CODES = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
_VALID_DAY_NAMES = set(DayName.__args__)  # type: ignore[attr-defined]
_ORDINAL_FIELDS = ("first", "second", "third", "fourth", "fifth", "last")


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


def normalize_day_name(value: str) -> str:
    """Lowercase and validate a day name against the DayName literal values."""
    lower = value.lower()
    if lower not in _VALID_DAY_NAMES:
        raise ValueError(REPETITION_INVALID_DAY_NAME.format(day=value))
    return lower


def check_at_most_one_ordinal(model: Any) -> Any:
    """Reject ordinal weekday model with more than one ordinal field set.

    Works with both OrdinalWeekday (core) and OrdinalWeekdaySpec (contract).
    """
    count = sum(1 for f in _ORDINAL_FIELDS if getattr(model, f) is not None)
    if count > 1:
        raise ValueError(REPETITION_AT_MOST_ONE_ORDINAL.format(count=count))
    return model


class OrdinalWeekday(OmniFocusBaseModel):
    """Typed ordinal-weekday model for monthly day-of-week patterns.

    Exactly one of the 6 ordinal fields should be set (at-most-one validator).
    Each field holds a DayName or None.
    """

    model_config = ConfigDict(extra="forbid")

    first: DayName | None = None
    second: DayName | None = None
    third: DayName | None = None
    fourth: DayName | None = None
    fifth: DayName | None = None
    last: DayName | None = None

    @field_validator("first", "second", "third", "fourth", "fifth", "last", mode="before")
    @classmethod
    def _normalize_day_name(cls, v: str | None) -> str | None:
        if v is None:
            return None
        return normalize_day_name(v)

    @model_validator(mode="after")
    def _check_at_most_one(self) -> OrdinalWeekday:
        check_at_most_one_ordinal(self)
        return self


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
    on: OrdinalWeekday | None,
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
    on: OrdinalWeekday | None = None
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

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, value: list[int] | None) -> list[int] | None:
        return validate_on_dates(value)


# -- End Condition Models -----------------------------------------------------


class EndByDate(OmniFocusBaseModel):
    """End condition: repeat until a specific date."""

    date: date_type = Field(description="Repeat until this date.")


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
    "DayName",
    "EndByDate",
    "EndByOccurrences",
    "EndCondition",
    "Frequency",
    "FrequencyType",
    "OnDate",
    "OrdinalWeekday",
    "RepetitionRule",
    "check_at_most_one_ordinal",
    "check_frequency_cross_type_fields",
    "normalize_day_codes",
    "normalize_day_name",
    "validate_interval",
    "validate_on_dates",
]
