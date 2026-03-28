"""Tests for repetition rule validation functions.

Tests validate_repetition_rule_add and internal validators for interval,
day codes, ordinals, day names, on_dates ranges, and end occurrences.
"""

from __future__ import annotations

import pytest

from omnifocus_operator.contracts.use_cases.repetition_rule import RepetitionRuleAddSpec
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    DailyFrequency,
    EndByOccurrences,
    MonthlyDayInMonthFrequency,
    MonthlyDayOfWeekFrequency,
    WeeklyOnDaysFrequency,
)
from omnifocus_operator.service.validate import validate_repetition_rule_add


def _make_spec(
    frequency: object = None,
    schedule: Schedule = Schedule.REGULARLY,
    based_on: BasedOn = BasedOn.DUE_DATE,
    end: object = None,
) -> RepetitionRuleAddSpec:
    """Helper to create a spec with defaults."""
    if frequency is None:
        frequency = DailyFrequency()
    return RepetitionRuleAddSpec(
        frequency=frequency,
        schedule=schedule,
        based_on=based_on,
        end=end,
    )


class TestValidateInterval:
    """Tests for interval validation (>= 1)."""

    def test_valid_interval(self) -> None:
        spec = _make_spec(frequency=DailyFrequency(interval=3))
        result = validate_repetition_rule_add(spec)
        assert result.frequency.interval == 3

    def test_interval_zero_rejected(self) -> None:
        spec = _make_spec(frequency=DailyFrequency(interval=0))
        with pytest.raises(ValueError, match="[Ii]nterval"):
            validate_repetition_rule_add(spec)

    def test_interval_negative_rejected(self) -> None:
        spec = _make_spec(frequency=DailyFrequency(interval=-1))
        with pytest.raises(ValueError, match="[Ii]nterval"):
            validate_repetition_rule_add(spec)

    def test_interval_default_valid(self) -> None:
        spec = _make_spec(frequency=DailyFrequency())
        result = validate_repetition_rule_add(spec)
        assert result.frequency.interval == 1


class TestValidateOnDays:
    """Tests for WeeklyOnDaysFrequency day codes."""

    def test_valid_uppercase(self) -> None:
        spec = _make_spec(frequency=WeeklyOnDaysFrequency(on_days=["MO", "WE"]))
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on_days == ["MO", "WE"]

    def test_normalizes_lowercase_to_uppercase(self) -> None:
        spec = _make_spec(frequency=WeeklyOnDaysFrequency(on_days=["mo", "we"]))
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on_days == ["MO", "WE"]

    def test_invalid_day_code_rejected(self) -> None:
        spec = _make_spec(frequency=WeeklyOnDaysFrequency(on_days=["XX"]))
        with pytest.raises(ValueError, match="day code"):
            validate_repetition_rule_add(spec)

    def test_mixed_case_valid(self) -> None:
        spec = _make_spec(frequency=WeeklyOnDaysFrequency(on_days=["Mo", "Fr"]))
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on_days == ["MO", "FR"]


class TestValidateMonthlyDayOfWeek:
    """Tests for MonthlyDayOfWeekFrequency ordinal/day validation."""

    def test_valid_on(self) -> None:
        spec = _make_spec(
            frequency=MonthlyDayOfWeekFrequency(on={"second": "tuesday"})
        )
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on == {"second": "tuesday"}

    def test_invalid_ordinal_rejected(self) -> None:
        spec = _make_spec(
            frequency=MonthlyDayOfWeekFrequency(on={"invalid": "tuesday"})
        )
        with pytest.raises(ValueError, match="ordinal"):
            validate_repetition_rule_add(spec)

    def test_invalid_day_name_rejected(self) -> None:
        spec = _make_spec(
            frequency=MonthlyDayOfWeekFrequency(on={"first": "badday"})
        )
        with pytest.raises(ValueError, match="day name"):
            validate_repetition_rule_add(spec)

    def test_last_weekday_valid(self) -> None:
        spec = _make_spec(
            frequency=MonthlyDayOfWeekFrequency(on={"last": "weekday"})
        )
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on == {"last": "weekday"}

    def test_none_on_valid(self) -> None:
        """MonthlyDayOfWeekFrequency with on=None is valid (bare monthly pattern)."""
        spec = _make_spec(
            frequency=MonthlyDayOfWeekFrequency(on=None)
        )
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on is None


class TestValidateMonthlyDayInMonth:
    """Tests for MonthlyDayInMonthFrequency on_dates range validation."""

    def test_valid_dates(self) -> None:
        spec = _make_spec(
            frequency=MonthlyDayInMonthFrequency(on_dates=[-1, 15])
        )
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on_dates == [-1, 15]

    def test_zero_rejected(self) -> None:
        spec = _make_spec(
            frequency=MonthlyDayInMonthFrequency(on_dates=[0])
        )
        with pytest.raises(ValueError, match="date value"):
            validate_repetition_rule_add(spec)

    def test_out_of_range_rejected(self) -> None:
        spec = _make_spec(
            frequency=MonthlyDayInMonthFrequency(on_dates=[32])
        )
        with pytest.raises(ValueError, match="date value"):
            validate_repetition_rule_add(spec)

    def test_negative_one_valid(self) -> None:
        """on_dates=[-1] means last day of month, valid."""
        spec = _make_spec(
            frequency=MonthlyDayInMonthFrequency(on_dates=[-1])
        )
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on_dates == [-1]

    def test_none_on_dates_valid(self) -> None:
        """on_dates=None is valid (bare monthly_day_in_month)."""
        spec = _make_spec(
            frequency=MonthlyDayInMonthFrequency(on_dates=None)
        )
        result = validate_repetition_rule_add(spec)
        assert result.frequency.on_dates is None


class TestValidateEnd:
    """Tests for end condition validation."""

    def test_valid_end_by_occurrences(self) -> None:
        spec = _make_spec(end=EndByOccurrences(occurrences=10))
        result = validate_repetition_rule_add(spec)
        assert result.end.occurrences == 10

    def test_occurrences_zero_rejected(self) -> None:
        spec = _make_spec(end=EndByOccurrences(occurrences=0))
        with pytest.raises(ValueError, match="occurrences"):
            validate_repetition_rule_add(spec)

    def test_none_end_valid(self) -> None:
        spec = _make_spec(end=None)
        result = validate_repetition_rule_add(spec)
        assert result.end is None

    def test_valid_interval_one(self) -> None:
        spec = _make_spec(end=EndByOccurrences(occurrences=1))
        result = validate_repetition_rule_add(spec)
        assert result.end.occurrences == 1


class TestCrossTypeDetection:
    """Tests for cross-type field detection (D-05 gap: Pydantic won't reject)."""

    def test_daily_with_valid_fields(self) -> None:
        """Normal daily frequency passes validation."""
        spec = _make_spec(frequency=DailyFrequency(interval=2))
        result = validate_repetition_rule_add(spec)
        assert result.frequency.type == "daily"


class TestAgentMessages:
    """Tests for repetition rule agent message constants."""

    def test_error_constants_exist(self) -> None:
        from omnifocus_operator.agent_messages.errors import (
            REPETITION_INVALID_DAY_CODE,
            REPETITION_INVALID_END_OCCURRENCES,
            REPETITION_INVALID_INTERVAL,
            REPETITION_INVALID_ON_DATE,
            REPETITION_NO_EXISTING_RULE,
            REPETITION_TYPE_CHANGE_INCOMPLETE,
        )

        assert "type" in REPETITION_TYPE_CHANGE_INCOMPLETE
        assert "existing" in REPETITION_NO_EXISTING_RULE
        assert len(REPETITION_INVALID_INTERVAL) > 0
        assert len(REPETITION_INVALID_DAY_CODE) > 0
        assert len(REPETITION_INVALID_ON_DATE) > 0
        assert len(REPETITION_INVALID_END_OCCURRENCES) > 0

    def test_warning_constants_exist(self) -> None:
        from omnifocus_operator.agent_messages.warnings import (
            REPETITION_EMPTY_ON_DATES,
            REPETITION_END_DATE_PAST,
            REPETITION_NO_OP,
            REPETITION_ON_COMPLETED_TASK,
        )

        assert len(REPETITION_END_DATE_PAST) > 0
        assert "monthly" in REPETITION_EMPTY_ON_DATES
        assert len(REPETITION_NO_OP) > 0
        assert len(REPETITION_ON_COMPLETED_TASK) > 0
