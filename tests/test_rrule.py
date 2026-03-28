"""Tests for repetition rule models, RRULE parser, and RRULE builder."""

from __future__ import annotations

import pytest

from omnifocus_operator.models.repetition_rule import (
    BasedOn,
    DailyFrequency,
    EndByDate,
    EndByOccurrences,
    HourlyFrequency,
    MinutelyFrequency,
    MonthlyDayInMonthFrequency,
    MonthlyDayOfWeekFrequency,
    MonthlyFrequency,
    RepetitionRule,
    Schedule,
    WeeklyFrequency,
    YearlyFrequency,
)


# ── FrequencySpec Discriminated Union ───────────────────────────────────


class TestFrequencySpecDiscriminatedUnion:
    """FrequencySpec validates via type discriminator."""

    def test_daily_validates(self):
        from pydantic import TypeAdapter

        from omnifocus_operator.models.repetition_rule import FrequencySpec

        ta = TypeAdapter(FrequencySpec)
        result = ta.validate_python({"type": "daily"})
        assert isinstance(result, DailyFrequency)

    def test_weekly_with_on_days_validates(self):
        from pydantic import TypeAdapter

        from omnifocus_operator.models.repetition_rule import FrequencySpec

        ta = TypeAdapter(FrequencySpec)
        result = ta.validate_python({"type": "weekly", "on_days": ["MO", "WE"]})
        assert isinstance(result, WeeklyFrequency)
        assert result.on_days == ["MO", "WE"]

    def test_monthly_day_of_week_validates(self):
        from pydantic import TypeAdapter

        from omnifocus_operator.models.repetition_rule import FrequencySpec

        ta = TypeAdapter(FrequencySpec)
        result = ta.validate_python(
            {"type": "monthly_day_of_week", "on": {"second": "tuesday"}}
        )
        assert isinstance(result, MonthlyDayOfWeekFrequency)
        assert result.on == {"second": "tuesday"}

    def test_monthly_day_in_month_validates(self):
        from pydantic import TypeAdapter

        from omnifocus_operator.models.repetition_rule import FrequencySpec

        ta = TypeAdapter(FrequencySpec)
        result = ta.validate_python(
            {"type": "monthly_day_in_month", "on_dates": [15, -1]}
        )
        assert isinstance(result, MonthlyDayInMonthFrequency)
        assert result.on_dates == [15, -1]


# ── Frequency Serialization ─────────────────────────────────────────────


class TestFrequencySerialization:
    """model_dump(by_alias=True) produces correct output."""

    def test_daily_interval_1_omits_interval(self):
        """D-08: interval=1 is the default, omitted from output."""
        d = DailyFrequency().model_dump(by_alias=True)
        assert "interval" not in d
        assert d == {"type": "daily"}

    def test_daily_interval_3_includes_interval(self):
        d = DailyFrequency(interval=3).model_dump(by_alias=True)
        assert d["interval"] == 3

    def test_weekly_on_days_serializes_as_camel_case(self):
        d = WeeklyFrequency(on_days=["MO"]).model_dump(by_alias=True)
        assert d == {"type": "weekly", "onDays": ["MO"]}

    def test_weekly_no_on_days_excludes_none(self):
        d = WeeklyFrequency().model_dump(by_alias=True)
        assert d == {"type": "weekly"}
        assert "onDays" not in d

    def test_monthly_day_of_week_type_stays_snake_case(self):
        """Pitfall 5: type value is a Literal, NOT camelCased."""
        d = MonthlyDayOfWeekFrequency().model_dump(by_alias=True)
        assert d["type"] == "monthly_day_of_week"
        # on=None should be excluded
        assert "on" not in d

    def test_monthly_day_in_month_on_dates_excluded_when_none(self):
        d = MonthlyDayInMonthFrequency().model_dump(by_alias=True)
        assert "onDates" not in d

    def test_minutely_with_interval(self):
        d = MinutelyFrequency(interval=30).model_dump(by_alias=True)
        assert d == {"type": "minutely", "interval": 30}

    def test_hourly_default_interval_omitted(self):
        d = HourlyFrequency().model_dump(by_alias=True)
        assert d == {"type": "hourly"}

    def test_monthly_plain(self):
        d = MonthlyFrequency().model_dump(by_alias=True)
        assert d == {"type": "monthly"}

    def test_yearly_plain(self):
        d = YearlyFrequency().model_dump(by_alias=True)
        assert d == {"type": "yearly"}


# ── End Condition Models ─────────────────────────────────────────────────


class TestEndConditionModels:
    def test_end_by_date_serializes(self):
        e = EndByDate(date="2026-12-31T00:00:00Z")
        d = e.model_dump(by_alias=True)
        assert d == {"date": "2026-12-31T00:00:00Z"}

    def test_end_by_occurrences_serializes(self):
        e = EndByOccurrences(occurrences=10)
        d = e.model_dump(by_alias=True)
        assert d == {"occurrences": 10}


# ── Schedule and BasedOn Enums ──────────────────────────────────────────


class TestScheduleEnum:
    def test_has_exactly_3_values(self):
        values = [v.value for v in Schedule]
        assert values == ["regularly", "regularly_with_catch_up", "from_completion"]


class TestBasedOnEnum:
    def test_has_exactly_3_values(self):
        values = [v.value for v in BasedOn]
        assert values == ["due_date", "defer_date", "planned_date"]


# ── RepetitionRule Model ─────────────────────────────────────────────────


class TestRepetitionRuleModel:
    def test_full_rule_validates(self):
        rule = RepetitionRule(
            frequency=DailyFrequency(interval=3),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
            end=EndByOccurrences(occurrences=10),
        )
        assert rule.frequency.type == "daily"
        assert rule.schedule == "regularly"
        assert rule.based_on == "due_date"
        assert isinstance(rule.end, EndByOccurrences)

    def test_no_end_serializes_without_end_key(self):
        rule = RepetitionRule(
            frequency=WeeklyFrequency(on_days=["MO", "FR"]),
            schedule=Schedule.FROM_COMPLETION,
            based_on=BasedOn.DEFER_DATE,
        )
        d = rule.model_dump(by_alias=True, exclude_none=True)
        assert "end" not in d

    def test_based_on_serializes_as_camel_case(self):
        rule = RepetitionRule(
            frequency=DailyFrequency(),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.PLANNED_DATE,
        )
        d = rule.model_dump(by_alias=True, exclude_none=True)
        assert "basedOn" in d
        assert d["basedOn"] == "planned_date"

    def test_frequency_interval_omission_in_nested_dump(self):
        """Verify interval=1 omission works through RepetitionRule serialization."""
        rule = RepetitionRule(
            frequency=DailyFrequency(),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        d = rule.model_dump(by_alias=True, exclude_none=True)
        assert "interval" not in d["frequency"]
