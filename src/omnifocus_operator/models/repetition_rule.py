"""Structured repetition rule models for OmniFocus tasks and projects.

Type hierarchy:
    _FrequencyBase          -- interval field, model_dump override for D-08
    +-- MinutelyFrequency   -- type="minutely"
    +-- HourlyFrequency     -- type="hourly"
    +-- DailyFrequency      -- type="daily"
    +-- WeeklyFrequency     -- type="weekly", on_days
    +-- MonthlyFrequency    -- type="monthly"
    +-- MonthlyDayOfWeekFrequency  -- type="monthly_day_of_week", on
    +-- MonthlyDayInMonthFrequency -- type="monthly_day_in_month", on_dates
    +-- YearlyFrequency     -- type="yearly"

    FrequencySpec = Annotated[Union[...], Field(discriminator="type")]

    EndByDate / EndByOccurrences -- end condition models
    EndCondition = EndByDate | EndByOccurrences

    RepetitionRule -- frequency + schedule + based_on + end

Enums defined here (will be reconciled with enums.py in Plan 02):
    Schedule -- regularly, regularly_with_catch_up, from_completion
    BasedOn  -- due_date, defer_date, planned_date
"""

from __future__ import annotations

from enum import StrEnum
from typing import Annotated, Any, Literal, Union

from pydantic import Field, model_serializer

from omnifocus_operator.models.base import OmniFocusBaseModel


# ── Enums ────────────────────────────────────────────────────────────────


class Schedule(StrEnum):
    """Repetition schedule type (3-value, derived from scheduleType + catchUp)."""

    REGULARLY = "regularly"
    REGULARLY_WITH_CATCH_UP = "regularly_with_catch_up"
    FROM_COMPLETION = "from_completion"


class BasedOn(StrEnum):
    """Anchor date for repetition rules (renamed from AnchorDateKey)."""

    DUE_DATE = "due_date"
    DEFER_DATE = "defer_date"
    PLANNED_DATE = "planned_date"


# ── Frequency Base ───────────────────────────────────────────────────────


class _FrequencyBase(OmniFocusBaseModel):
    """Base class for all frequency subtypes.

    Handles D-08 (interval=1 omission) and None-field exclusion in model_dump.
    """

    interval: int = 1

    @model_serializer
    def _serialize(self) -> dict[str, Any]:
        """Custom serializer for D-08 (interval=1 omission) and None exclusion.

        Uses @model_serializer so custom logic applies both when calling
        model_dump() directly AND when serialized as a nested model.
        """
        d: dict[str, Any] = {}
        for field_name, field_info in type(self).model_fields.items():
            value = getattr(self, field_name)
            if value is None:
                continue
            # Use alias if available
            alias = field_info.alias
            if alias is None and self.model_config.get("alias_generator"):
                from pydantic.alias_generators import to_camel

                alias = to_camel(field_name)
            key = alias if alias else field_name
            d[key] = value
        # D-08: omit interval when it equals the default (1)
        if d.get("interval") == 1:
            d.pop("interval", None)
        return d


# ── 8 Frequency Subtypes ────────────────────────────────────────────────


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


# ── FrequencySpec Discriminated Union ────────────────────────────────────

FrequencySpec = Annotated[
    Union[
        MinutelyFrequency,
        HourlyFrequency,
        DailyFrequency,
        WeeklyFrequency,
        MonthlyFrequency,
        MonthlyDayOfWeekFrequency,
        MonthlyDayInMonthFrequency,
        YearlyFrequency,
    ],
    Field(discriminator="type"),
]


# ── End Condition Models ─────────────────────────────────────────────────


class EndByDate(OmniFocusBaseModel):
    """End condition: repeat until a specific date."""

    date: str  # ISO-8601


class EndByOccurrences(OmniFocusBaseModel):
    """End condition: repeat a fixed number of times."""

    occurrences: int


EndCondition = EndByDate | EndByOccurrences


# ── RepetitionRule ───────────────────────────────────────────────────────


class RepetitionRule(OmniFocusBaseModel):
    """Structured repetition rule for recurring tasks and projects.

    Replaces the old 4-field model (ruleString, scheduleType,
    anchorDateKey, catchUpAutomatically) with parsed, structured data.
    """

    frequency: FrequencySpec
    schedule: Schedule
    based_on: BasedOn  # serializes as basedOn
    end: EndCondition | None = None
