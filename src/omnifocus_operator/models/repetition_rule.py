"""Structured repetition rule models for OmniFocus tasks and projects.

Flat frequency model with 6 types and optional specialization fields:
    Frequency -- type + interval + optional on_days/on/on_dates

    FrequencyType = Literal["minutely", "hourly", "daily", "weekly", "monthly", "yearly"]

    EndByDate / EndByOccurrences -- end condition models
    EndCondition = EndByDate | EndByOccurrences

    RepetitionRule -- frequency + schedule + based_on + end

Enums:
    Schedule -- from enums.py (regularly, regularly_with_catch_up, from_completion)
    BasedOn  -- from enums.py (due_date, defer_date, planned_date)
"""

from __future__ import annotations

from typing import Literal

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import BasedOn, Schedule

# -- Frequency Type -----------------------------------------------------------

FrequencyType = Literal["minutely", "hourly", "daily", "weekly", "monthly", "yearly"]

# Valid values for field validators
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


# -- Flat Frequency Model ----------------------------------------------------


class Frequency(OmniFocusBaseModel):
    """Flat frequency model with type discriminator and optional specialization fields.

    Cross-type validation:
    - on_days only valid for weekly
    - on/on_dates only valid for monthly
    - on and on_dates are mutually exclusive on monthly
    """

    type: FrequencyType
    interval: int = Field(default=1, ge=1)
    on_days: list[str] | None = None
    on: dict[str, str] | None = None
    on_dates: list[int] | None = None

    @field_validator("on_days", mode="before")
    @classmethod
    def _normalize_day_codes(cls, v: list[str] | None) -> list[str] | None:
        """Normalize day codes to uppercase and validate."""
        if v is None:
            return None
        normalized = []
        for code in v:
            upper = code.upper()
            if upper not in _VALID_DAY_CODES:
                raise ValueError(err.REPETITION_INVALID_DAY_CODE.format(code=code))
            normalized.append(upper)
        return normalized

    @field_validator("on", mode="before")
    @classmethod
    def _validate_on(cls, v: dict[str, str] | None) -> dict[str, str] | None:
        """Validate ordinal and day name in the on dict."""
        if v is None:
            return None
        for ordinal, day_name in v.items():
            if ordinal not in _VALID_ORDINALS:
                raise ValueError(err.REPETITION_INVALID_ORDINAL.format(ordinal=ordinal))
            if day_name not in _VALID_DAY_NAMES:
                raise ValueError(err.REPETITION_INVALID_DAY_NAME.format(day=day_name))
        return v

    @field_validator("on_dates", mode="before")
    @classmethod
    def _validate_on_dates(cls, v: list[int] | None) -> list[int] | None:
        """Validate on_dates values are in range (-1, 1-31)."""
        if v is None:
            return None
        for value in v:
            if value == 0 or value < -1 or value > 31:
                raise ValueError(err.REPETITION_INVALID_ON_DATE.format(value=value))
        return v

    @model_validator(mode="after")
    def _validate_cross_type(self) -> Frequency:
        """Validate specialization fields match the type."""
        if self.on_days is not None and self.type != "weekly":
            raise ValueError(
                f"on_days is not valid for type '{self.type}'. "
                "on_days is only valid for type 'weekly'."
            )
        if self.on is not None and self.type != "monthly":
            raise ValueError(
                f"on is not valid for type '{self.type}'. "
                "on is only valid for type 'monthly'."
            )
        if self.on_dates is not None and self.type != "monthly":
            raise ValueError(
                f"on_dates is not valid for type '{self.type}'. "
                "on_dates is only valid for type 'monthly'."
            )
        if self.on is not None and self.on_dates is not None:
            raise ValueError(
                "on and on_dates are mutually exclusive. "
                "Use on for day-of-week patterns (e.g., {\"second\": \"tuesday\"}) "
                "or on_dates for specific dates (e.g., [1, 15]), not both."
            )
        return self


# -- End Condition Models -----------------------------------------------------


class EndByDate(OmniFocusBaseModel):
    """End condition: repeat until a specific date."""

    date: str  # ISO-8601


class EndByOccurrences(OmniFocusBaseModel):
    """End condition: repeat a fixed number of times."""

    occurrences: int = Field(ge=1)


EndCondition = EndByDate | EndByOccurrences


# -- RepetitionRule -----------------------------------------------------------


class RepetitionRule(OmniFocusBaseModel):
    """Structured repetition rule for recurring tasks and projects.

    Replaces the old 4-field model (ruleString, scheduleType,
    anchorDateKey, catchUpAutomatically) with parsed, structured data.
    """

    frequency: Frequency
    schedule: Schedule
    based_on: BasedOn  # serializes as basedOn
    end: EndCondition | None = None
