"""Tests for repetition rule validation -- model validators and agent messages.

With the flat Frequency model, all input validation has migrated to Pydantic
model validators on Frequency/FrequencyAddSpec. These tests verify:
- Model validator behavior (cross-type, day codes, ordinals, on_dates, interval)
- Agent message constants exist and contain expected content
"""

from __future__ import annotations

import pytest

from omnifocus_operator.agent_messages.errors import (
    REPETITION_INVALID_DAY_CODE,
    REPETITION_INVALID_ON_DATE,
    REPETITION_NO_EXISTING_RULE,
)
from omnifocus_operator.agent_messages.warnings import (
    REPETITION_EMPTY_ON_DATES,
    REPETITION_END_DATE_PAST,
    REPETITION_NO_OP,
)
from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.contracts.shared.repetition_rule import (
    FrequencyAddSpec,
    FrequencyEditSpec,
    RepetitionRuleAddSpec,
    RepetitionRuleEditSpec,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    EndByOccurrences,
    Frequency,
)


def _make_spec(
    frequency: object = None,
    schedule: Schedule = Schedule.REGULARLY,
    based_on: BasedOn = BasedOn.DUE_DATE,
    end: object = None,
) -> RepetitionRuleAddSpec:
    """Helper to create a spec with defaults."""
    if frequency is None:
        frequency = FrequencyAddSpec(type="daily")
    return RepetitionRuleAddSpec(
        frequency=frequency,
        schedule=schedule,
        based_on=based_on,
        end=end,
    )


class TestValidateInterval:
    """Tests for interval validation (>= 1) via model validators."""

    def test_valid_interval(self) -> None:
        freq = Frequency(type="daily", interval=3)
        assert freq.interval == 3

    def test_interval_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="Interval must be"):
            Frequency(type="daily", interval=0)

    def test_interval_zero_message_is_clean(self) -> None:
        """The error message itself must not contain pydantic internals."""
        try:
            Frequency(type="daily", interval=0)
        except ValueError as exc:
            msg = exc.errors()[0]["msg"]  # type: ignore[union-attr]
            assert "Interval must be" in msg
            assert "greater_than_equal" not in msg
            assert "type=" not in msg
            assert "input_value" not in msg

    def test_interval_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="Interval must be"):
            Frequency(type="daily", interval=-1)

    def test_interval_default_valid(self) -> None:
        freq = Frequency(type="daily")
        assert freq.interval == 1


class TestValidateOnDays:
    """Tests for day code validation via model field validators."""

    def test_valid_uppercase(self) -> None:
        freq = Frequency(type="weekly", on_days=["MO", "WE"])
        assert freq.on_days == ["MO", "WE"]

    def test_normalizes_lowercase_to_uppercase(self) -> None:
        freq = Frequency(type="weekly", on_days=["mo", "we"])
        assert freq.on_days == ["MO", "WE"]

    def test_invalid_day_code_rejected(self) -> None:
        with pytest.raises(ValueError, match="day code"):
            Frequency(type="weekly", on_days=["XX"])

    def test_mixed_case_valid(self) -> None:
        freq = Frequency(type="weekly", on_days=["Mo", "Fr"])
        assert freq.on_days == ["MO", "FR"]


class TestValidateMonthlyDayOfWeek:
    """Tests for on dict ordinal/day validation via model field validators."""

    def test_valid_on(self) -> None:
        freq = Frequency(type="monthly", on={"second": "tuesday"})
        assert freq.on == {"second": "tuesday"}

    def test_invalid_ordinal_rejected(self) -> None:
        with pytest.raises(ValueError, match="ordinal"):
            Frequency(type="monthly", on={"invalid": "tuesday"})

    def test_invalid_day_name_rejected(self) -> None:
        with pytest.raises(ValueError, match="day name"):
            Frequency(type="monthly", on={"first": "badday"})

    def test_last_weekday_valid(self) -> None:
        freq = Frequency(type="monthly", on={"last": "weekday"})
        assert freq.on == {"last": "weekday"}

    def test_none_on_valid(self) -> None:
        """Monthly with on=None is valid (bare monthly pattern)."""
        freq = Frequency(type="monthly", on=None)
        assert freq.on is None


class TestValidateMonthlyDayInMonth:
    """Tests for on_dates range validation via model field validators."""

    def test_valid_dates(self) -> None:
        freq = Frequency(type="monthly", on_dates=[-1, 15])
        assert freq.on_dates == [-1, 15]

    def test_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="date value"):
            Frequency(type="monthly", on_dates=[0])

    def test_out_of_range_rejected(self) -> None:
        with pytest.raises(ValueError, match="date value"):
            Frequency(type="monthly", on_dates=[32])

    def test_negative_one_valid(self) -> None:
        """on_dates=[-1] means last day of month, valid."""
        freq = Frequency(type="monthly", on_dates=[-1])
        assert freq.on_dates == [-1]

    def test_none_on_dates_valid(self) -> None:
        """on_dates=None is valid (bare monthly)."""
        freq = Frequency(type="monthly", on_dates=None)
        assert freq.on_dates is None


class TestValidateEnd:
    """Tests for end condition validation via model field constraints."""

    def test_valid_end_by_occurrences(self) -> None:
        end = EndByOccurrences(occurrences=10)
        assert end.occurrences == 10

    def test_occurrences_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="occurrences must be"):
            EndByOccurrences(occurrences=0)

    def test_occurrences_zero_message_is_clean(self) -> None:
        """The error message itself must not contain pydantic internals."""
        try:
            EndByOccurrences(occurrences=0)
        except ValueError as exc:
            msg = exc.errors()[0]["msg"]  # type: ignore[union-attr]
            assert "occurrences must be" in msg
            assert "greater_than_equal" not in msg
            assert "type=" not in msg
            assert "input_value" not in msg

    def test_occurrences_negative_rejected(self) -> None:
        with pytest.raises(ValueError, match="occurrences must be"):
            EndByOccurrences(occurrences=-1)

    def test_valid_interval_one(self) -> None:
        end = EndByOccurrences(occurrences=1)
        assert end.occurrences == 1


class TestCrossTypeDetection:
    """Tests for cross-type field detection via model validators (D-07)."""

    def test_daily_with_valid_fields(self) -> None:
        """Normal daily frequency passes validation."""
        freq = Frequency(type="daily", interval=2)
        assert freq.type == "daily"

    def test_on_days_on_daily_rejected(self) -> None:
        """on_days with type daily -> cross-type error."""
        with pytest.raises(ValueError, match="on_days is not valid"):
            Frequency(type="daily", on_days=["MO"])

    def test_on_on_weekly_rejected(self) -> None:
        """on dict with type weekly -> cross-type error."""
        with pytest.raises(ValueError, match="on is not valid"):
            Frequency(type="weekly", on={"first": "monday"})

    def test_on_dates_on_weekly_rejected(self) -> None:
        """on_dates with type weekly -> cross-type error."""
        with pytest.raises(ValueError, match="on_dates is not valid"):
            Frequency(type="weekly", on_dates=[1])

    def test_on_and_on_dates_mutually_exclusive(self) -> None:
        """on + on_dates on monthly -> mutual exclusion error."""
        with pytest.raises(ValueError, match="mutually exclusive"):
            Frequency(type="monthly", on={"first": "monday"}, on_dates=[1])


class TestFrequencyAddSpec:
    """Tests for FrequencyAddSpec model validators (same as Frequency)."""

    def test_valid_daily(self) -> None:
        spec = FrequencyAddSpec(type="daily")
        assert spec.type == "daily"
        assert spec.interval == 1

    def test_valid_weekly_with_days(self) -> None:
        spec = FrequencyAddSpec(type="weekly", on_days=["MO", "FR"])
        assert spec.on_days == ["MO", "FR"]

    def test_normalizes_day_codes(self) -> None:
        spec = FrequencyAddSpec(type="weekly", on_days=["mo", "fr"])
        assert spec.on_days == ["MO", "FR"]

    def test_cross_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="on_days is not valid"):
            FrequencyAddSpec(type="daily", on_days=["MO"])

    def test_interval_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="Interval must be"):
            FrequencyAddSpec(type="daily", interval=0)

    def test_used_in_spec(self) -> None:
        spec = _make_spec(frequency=FrequencyAddSpec(type="daily", interval=3))
        assert spec.frequency.interval == 3


class TestFrequencyAddSpecType:
    """Tests for frequency type validation on FrequencyAddSpec."""

    def test_invalid_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid frequency type"):
            FrequencyAddSpec(type="biweekly")

    def test_valid_type_passes(self) -> None:
        spec = FrequencyAddSpec(type="weekly")
        assert spec.type == "weekly"

    def test_message_includes_value_and_valid_types(self) -> None:
        try:
            FrequencyAddSpec(type="biweekly")
        except ValueError as exc:
            msg = exc.errors()[0]["msg"]  # type: ignore[union-attr]
            assert "biweekly" in msg
            assert "daily" in msg
            assert "weekly" in msg
            assert "monthly" in msg


class TestFrequencyEditSpecType:
    """Tests for frequency type validation on FrequencyEditSpec."""

    def test_invalid_type_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid frequency type"):
            FrequencyEditSpec(type="fortnightly")

    def test_valid_type_passes(self) -> None:
        spec = FrequencyEditSpec(type="daily")
        assert spec.type == "daily"

    def test_unset_default_passes(self) -> None:
        spec = FrequencyEditSpec()
        assert spec.type is UNSET


class TestFrequencyEditSpecInterval:
    """Tests for interval validation on FrequencyEditSpec (edit path)."""

    def test_interval_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="Interval must be"):
            FrequencyEditSpec(type="daily", interval=0)

    def test_interval_valid(self) -> None:
        spec = FrequencyEditSpec(type="daily", interval=3)
        assert spec.interval == 3

    def test_interval_unset_default(self) -> None:
        spec = FrequencyEditSpec()
        assert spec.interval is UNSET


class TestRepetitionRuleEditSpecEnd:
    """Tests for end validator on RepetitionRuleEditSpec."""

    def test_occurrences_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="occurrences must be"):
            RepetitionRuleEditSpec(end={"occurrences": 0})

    def test_empty_dict_rejected(self) -> None:
        with pytest.raises(ValueError, match="end requires either"):
            RepetitionRuleEditSpec(end={})

    def test_occurrences_valid(self) -> None:
        spec = RepetitionRuleEditSpec(end={"occurrences": 5})
        assert spec.end.occurrences == 5  # type: ignore[union-attr]

    def test_none_passes(self) -> None:
        spec = RepetitionRuleEditSpec(end=None)
        assert spec.end is None

    def test_unset_default(self) -> None:
        spec = RepetitionRuleEditSpec()
        assert spec.end is UNSET


class TestRepetitionRuleAddSpecEnd:
    """Tests for end validator on RepetitionRuleAddSpec."""

    def test_occurrences_zero_rejected(self) -> None:
        with pytest.raises(ValueError, match="occurrences must be"):
            _make_spec(end={"occurrences": 0})

    def test_empty_dict_rejected(self) -> None:
        with pytest.raises(ValueError, match="end requires either"):
            _make_spec(end={})

    def test_none_passes(self) -> None:
        spec = _make_spec(end=None)
        assert spec.end is None


class TestAgentMessages:
    """Tests for repetition rule agent message constants."""

    def test_error_constants_exist(self) -> None:
        assert "existing" in REPETITION_NO_EXISTING_RULE
        assert len(REPETITION_INVALID_DAY_CODE) > 0
        assert len(REPETITION_INVALID_ON_DATE) > 0

    def test_warning_constants_exist(self) -> None:
        assert len(REPETITION_END_DATE_PAST) > 0
        assert "monthly" in REPETITION_EMPTY_ON_DATES
        assert len(REPETITION_NO_OP) > 0
