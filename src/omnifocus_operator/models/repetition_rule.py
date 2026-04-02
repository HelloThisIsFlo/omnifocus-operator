"""Structured repetition rule models for OmniFocus tasks and projects.

Flat model:
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

Type aliases (FrequencyType, DayCode, OnDate, DayName) live in
contracts/shared/repetition_rule.py -- they carry Literal/Annotated
constraints that belong on the agent-facing contract boundary, not on
core models. Core models use plain types with runtime validators.
"""

from __future__ import annotations

from datetime import date as date_type
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

from pydantic import ConfigDict, Field, field_serializer, field_validator, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    END_BY_DATE_DATE,
    END_BY_DATE_DOC,
    END_BY_OCCURRENCES_DOC,
    FREQUENCY_DOC,
    ON_DAYS,
    ORDINAL_WEEKDAY_DOC,
    REPETITION_RULE_DOC,
)
from omnifocus_operator.agent_messages.errors import (
    REPETITION_AT_MOST_ONE_ORDINAL,
    REPETITION_INVALID_DAY_CODE,
    REPETITION_INVALID_DAY_NAME,
    REPETITION_INVALID_END_OCCURRENCES,
    REPETITION_INVALID_FREQUENCY_TYPE,
    REPETITION_INVALID_INTERVAL,
    REPETITION_INVALID_ON_DATE,
)
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import BasedOn, Schedule

# -- Validation sets -----------------------------------------------------------

_VALID_DAY_CODES = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
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
_VALID_FREQUENCY_TYPES = {"minutely", "hourly", "daily", "weekly", "monthly", "yearly"}
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


def validate_frequency_type(v: str) -> str:
    """Validate a frequency type string against the known set."""
    if v not in _VALID_FREQUENCY_TYPES:
        raise ValueError(REPETITION_INVALID_FREQUENCY_TYPE.format(freq_type=v))
    return v


def check_at_most_one_ordinal(model: Any) -> Any:
    """Reject ordinal weekday model with more than one ordinal field set.

    Works with both OrdinalWeekday (core) and OrdinalWeekdaySpec (contract).
    """
    count = sum(1 for f in _ORDINAL_FIELDS if getattr(model, f) is not None)
    if count > 1:
        raise ValueError(REPETITION_AT_MOST_ONE_ORDINAL.format(count=count))
    return model


class OrdinalWeekday(OmniFocusBaseModel):
    __doc__ = ORDINAL_WEEKDAY_DOC

    model_config = ConfigDict(extra="forbid")

    first: str | None = None
    second: str | None = None
    third: str | None = None
    fourth: str | None = None
    fifth: str | None = None
    last: str | None = None

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
    __doc__ = FREQUENCY_DOC

    type: str  # required, NO default -- survives exclude_defaults
    interval: int = Field(default=1)
    on_days: list[str] | None = Field(default=None, description=ON_DAYS)
    on: OrdinalWeekday | None = None
    on_dates: list[int] | None = None

    @field_validator("type", mode="before")
    @classmethod
    def _validate_frequency_type(cls, v: str) -> str:
        return validate_frequency_type(v)

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
    __doc__ = END_BY_DATE_DOC

    date: date_type = Field(description=END_BY_DATE_DATE)


class EndByOccurrences(OmniFocusBaseModel):
    __doc__ = END_BY_OCCURRENCES_DOC

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
    __doc__ = REPETITION_RULE_DOC

    frequency: Frequency
    schedule: Schedule
    based_on: BasedOn  # serializes as basedOn
    end: EndCondition | None = None

    @field_serializer("frequency")
    def _serialize_frequency(self, freq: Frequency, _info: Any) -> dict[str, Any]:
        return freq.model_dump(exclude_defaults=True, by_alias=True)


__all__ = [
    "EndByDate",
    "EndByOccurrences",
    "EndCondition",
    "Frequency",
    "OrdinalWeekday",
    "RepetitionRule",
    "check_at_most_one_ordinal",
    "check_frequency_cross_type_fields",
    "normalize_day_codes",
    "normalize_day_name",
    "validate_frequency_type",
    "validate_interval",
    "validate_on_dates",
]
