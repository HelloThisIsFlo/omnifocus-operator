"""Structured repetition rule models for OmniFocus tasks and projects.

Type hierarchy:
    _FrequencyBase          -- interval field
    +-- MinutelyFrequency   -- type="minutely"
    +-- HourlyFrequency     -- type="hourly"
    +-- DailyFrequency      -- type="daily"
    +-- WeeklyFrequency     -- type="weekly", on_days
    +-- MonthlyFrequency    -- type="monthly"
    +-- MonthlyDayOfWeekFrequency  -- type="monthly_day_of_week", on
    +-- MonthlyDayInMonthFrequency -- type="monthly_day_in_month", on_dates
    +-- YearlyFrequency     -- type="yearly"

    Frequency = Annotated[Union[...], Field(discriminator="type")]

    EndByDate / EndByOccurrences -- end condition models
    EndCondition = EndByDate | EndByOccurrences

    RepetitionRule -- frequency + schedule + based_on + end

Enums:
    Schedule -- from enums.py (regularly, regularly_with_catch_up, from_completion)
    BasedOn  -- from enums.py (due_date, defer_date, planned_date)
"""

from __future__ import annotations

from typing import Annotated, Literal

from pydantic import Field

from omnifocus_operator.models.base import OmniFocusBaseModel
from omnifocus_operator.models.enums import BasedOn, Schedule

# -- Frequency Base -----------------------------------------------------------


class _FrequencyBase(OmniFocusBaseModel):
    """Base class for all frequency subtypes."""

    interval: int = 1


# -- 8 Frequency Subtypes ----------------------------------------------------


class MinutelyFrequency(_FrequencyBase):
    type: Literal["minutely"] = "minutely"


class HourlyFrequency(_FrequencyBase):
    type: Literal["hourly"] = "hourly"


class DailyFrequency(_FrequencyBase):
    type: Literal["daily"] = "daily"


class WeeklyFrequency(_FrequencyBase):
    type: Literal["weekly"] = "weekly"
    on_days: list[str] | None = None  # serializes as onDays


class MonthlyFrequency(_FrequencyBase):
    type: Literal["monthly"] = "monthly"


class MonthlyDayOfWeekFrequency(_FrequencyBase):
    type: Literal["monthly_day_of_week"] = "monthly_day_of_week"
    on: dict[str, str] | None = None  # {"second": "tuesday"}


class MonthlyDayInMonthFrequency(_FrequencyBase):
    type: Literal["monthly_day_in_month"] = "monthly_day_in_month"
    on_dates: list[int] | None = None  # serializes as onDates


class YearlyFrequency(_FrequencyBase):
    type: Literal["yearly"] = "yearly"


# -- Frequency Discriminated Union --------------------------------------------

Frequency = Annotated[
    MinutelyFrequency
    | HourlyFrequency
    | DailyFrequency
    | WeeklyFrequency
    | MonthlyFrequency
    | MonthlyDayOfWeekFrequency
    | MonthlyDayInMonthFrequency
    | YearlyFrequency,
    Field(discriminator="type"),
]


# -- End Condition Models -----------------------------------------------------


class EndByDate(OmniFocusBaseModel):
    """End condition: repeat until a specific date."""

    date: str  # ISO-8601


class EndByOccurrences(OmniFocusBaseModel):
    """End condition: repeat a fixed number of times."""

    occurrences: int


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
