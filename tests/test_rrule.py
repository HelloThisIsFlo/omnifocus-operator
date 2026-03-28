"""Tests for repetition rule models, RRULE parser, and RRULE builder."""

from __future__ import annotations

import json
from pathlib import Path

import pytest
from pydantic import TypeAdapter

from omnifocus_operator.models.repetition_rule import (
    BasedOn,
    DailyFrequency,
    EndByDate,
    EndByOccurrences,
    Frequency,
    HourlyFrequency,
    MinutelyFrequency,
    MonthlyDayInMonthFrequency,
    MonthlyDayOfWeekFrequency,
    MonthlyFrequency,
    RepetitionRule,
    Schedule,
    WeeklyFrequency,
    WeeklyOnDaysFrequency,
    YearlyFrequency,
)
from omnifocus_operator.rrule import build_rrule, parse_end_condition, parse_rrule

# ── Frequency Discriminated Union ─────────────────────────────────────


class TestFrequencyDiscriminatedUnion:
    """Frequency validates via type discriminator."""

    def test_daily_validates(self):
        ta = TypeAdapter(Frequency)
        result = ta.validate_python({"type": "daily"})
        assert isinstance(result, DailyFrequency)

    def test_weekly_with_on_days_validates(self):
        ta = TypeAdapter(Frequency)
        result = ta.validate_python({"type": "weekly", "on_days": ["MO", "WE"]})
        assert isinstance(result, WeeklyFrequency)
        assert result.on_days == ["MO", "WE"]

    def test_monthly_day_of_week_validates(self):
        ta = TypeAdapter(Frequency)
        result = ta.validate_python({"type": "monthly_day_of_week", "on": {"second": "tuesday"}})
        assert isinstance(result, MonthlyDayOfWeekFrequency)
        assert result.on == {"second": "tuesday"}

    def test_monthly_day_in_month_validates(self):
        ta = TypeAdapter(Frequency)
        result = ta.validate_python({"type": "monthly_day_in_month", "on_dates": [15, -1]})
        assert isinstance(result, MonthlyDayInMonthFrequency)
        assert result.on_dates == [15, -1]


# ── Frequency Serialization ─────────────────────────────────────────────


class TestFrequencySerialization:
    """model_dump(by_alias=True) produces correct output."""

    def test_daily_interval_1_included(self):
        d = DailyFrequency().model_dump(by_alias=True)
        assert d["interval"] == 1
        assert d == {"type": "daily", "interval": 1}

    def test_daily_interval_3_includes_interval(self):
        d = DailyFrequency(interval=3).model_dump(by_alias=True)
        assert d["interval"] == 3

    def test_weekly_on_days_serializes_as_camel_case(self):
        d = WeeklyFrequency(on_days=["MO"]).model_dump(by_alias=True)
        assert d == {"type": "weekly", "interval": 1, "onDays": ["MO"]}

    def test_weekly_no_on_days_is_none(self):
        d = WeeklyFrequency().model_dump(by_alias=True)
        assert d["onDays"] is None

    def test_monthly_day_of_week_type_stays_snake_case(self):
        """Pitfall 5: type value is a Literal, NOT camelCased."""
        d = MonthlyDayOfWeekFrequency().model_dump(by_alias=True)
        assert d["type"] == "monthly_day_of_week"
        assert d["on"] is None

    def test_monthly_day_in_month_on_dates_is_none(self):
        d = MonthlyDayInMonthFrequency().model_dump(by_alias=True)
        assert d["onDates"] is None

    def test_minutely_with_interval(self):
        d = MinutelyFrequency(interval=30).model_dump(by_alias=True)
        assert d == {"type": "minutely", "interval": 30}

    def test_hourly_default_interval_included(self):
        d = HourlyFrequency().model_dump(by_alias=True)
        assert d == {"type": "hourly", "interval": 1}

    def test_monthly_plain(self):
        d = MonthlyFrequency().model_dump(by_alias=True)
        assert d == {"type": "monthly", "interval": 1}

    def test_yearly_plain(self):
        d = YearlyFrequency().model_dump(by_alias=True)
        assert d == {"type": "yearly", "interval": 1}


# ── Weekly Split (Gap Closure) ──────────────────────────────────────────


class TestWeeklySplit:
    """WeeklyFrequency (bare) vs WeeklyOnDaysFrequency (with days)."""

    def test_bare_weekly_has_no_on_days_field(self):
        """Critical regression test: bare weekly must NOT serialize onDays."""
        d = WeeklyFrequency().model_dump(by_alias=True)
        assert d == {"type": "weekly", "interval": 1}
        assert "onDays" not in d

    def test_weekly_on_days_serializes(self):
        d = WeeklyOnDaysFrequency(on_days=["MO"]).model_dump(by_alias=True)
        assert d == {"type": "weekly_on_days", "interval": 1, "onDays": ["MO"]}

    def test_parse_bare_weekly(self):
        result = parse_rrule("FREQ=WEEKLY")
        assert isinstance(result, WeeklyFrequency)
        assert not isinstance(result, WeeklyOnDaysFrequency)

    def test_parse_weekly_with_byday(self):
        result = parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE")
        assert isinstance(result, WeeklyOnDaysFrequency)
        assert result.on_days == ["MO", "WE"]

    def test_build_bare_weekly(self):
        assert build_rrule(WeeklyFrequency()) == "FREQ=WEEKLY"

    def test_build_weekly_on_days(self):
        result = build_rrule(WeeklyOnDaysFrequency(on_days=["MO", "WE"]))
        assert result == "FREQ=WEEKLY;BYDAY=MO,WE"

    def test_round_trip_bare(self):
        freq = parse_rrule("FREQ=WEEKLY")
        rebuilt = build_rrule(freq)
        assert rebuilt == "FREQ=WEEKLY"
        re_parsed = parse_rrule(rebuilt)
        assert re_parsed == freq

    def test_round_trip_with_days(self):
        freq = parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR")
        rebuilt = build_rrule(freq)
        assert rebuilt == "FREQ=WEEKLY;BYDAY=MO,WE,FR"
        re_parsed = parse_rrule(rebuilt)
        assert re_parsed == freq


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

    def test_no_end_serializes_as_none(self):
        rule = RepetitionRule(
            frequency=WeeklyFrequency(on_days=["MO", "FR"]),
            schedule=Schedule.FROM_COMPLETION,
            based_on=BasedOn.DEFER_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert d["end"] is None

    def test_based_on_serializes_as_camel_case(self):
        rule = RepetitionRule(
            frequency=DailyFrequency(),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.PLANNED_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert "basedOn" in d
        assert d["basedOn"] == "planned_date"

    def test_frequency_interval_1_included_in_nested_dump(self):
        rule = RepetitionRule(
            frequency=DailyFrequency(),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert d["frequency"]["interval"] == 1


# ── Parser: Frequency Types ──────────────────────────────────────────────


class TestParseRruleFrequencyTypes:
    """parse_rrule returns correct Frequency model for each frequency type."""

    def test_daily(self):
        result = parse_rrule("FREQ=DAILY")
        assert result == DailyFrequency()

    def test_weekly_bare(self):
        result = parse_rrule("FREQ=WEEKLY")
        assert result == WeeklyFrequency()

    def test_weekly_with_byday(self):
        result = parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR")
        assert result == WeeklyFrequency(on_days=["MO", "WE", "FR"])

    def test_monthly_plain(self):
        result = parse_rrule("FREQ=MONTHLY")
        assert result == MonthlyFrequency()

    def test_monthly_day_of_week(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=2TU")
        assert result == MonthlyDayOfWeekFrequency(on={"second": "tuesday"})

    def test_monthly_last_friday(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=-1FR")
        assert result == MonthlyDayOfWeekFrequency(on={"last": "friday"})

    def test_monthly_day_in_month(self):
        result = parse_rrule("FREQ=MONTHLY;BYMONTHDAY=15")
        assert result == MonthlyDayInMonthFrequency(on_dates=[15])

    def test_monthly_last_day(self):
        result = parse_rrule("FREQ=MONTHLY;BYMONTHDAY=-1")
        assert result == MonthlyDayInMonthFrequency(on_dates=[-1])

    def test_yearly(self):
        result = parse_rrule("FREQ=YEARLY")
        assert result == YearlyFrequency()

    def test_minutely(self):
        result = parse_rrule("FREQ=MINUTELY;INTERVAL=30")
        assert result == MinutelyFrequency(interval=30)

    def test_hourly(self):
        result = parse_rrule("FREQ=HOURLY;INTERVAL=2")
        assert result == HourlyFrequency(interval=2)


# ── Parser: Interval ─────────────────────────────────────────────────────


class TestParseRruleInterval:
    def test_interval_1_present_on_model(self):
        result = parse_rrule("FREQ=DAILY")
        assert result.interval == 1

    def test_interval_greater_than_1(self):
        result = parse_rrule("FREQ=DAILY;INTERVAL=3")
        assert result.interval == 3

    def test_explicit_interval_1(self):
        result = parse_rrule("FREQ=DAILY;INTERVAL=1")
        assert result.interval == 1


# ── Parser: End Conditions ───────────────────────────────────────────────


class TestParseRruleEndConditions:
    def test_count(self):
        result = parse_end_condition("FREQ=WEEKLY;COUNT=10")
        assert result == EndByOccurrences(occurrences=10)

    def test_until(self):
        result = parse_end_condition("FREQ=MONTHLY;UNTIL=20261231T000000Z")
        assert result == EndByDate(date="2026-12-31T00:00:00Z")

    def test_no_end_condition(self):
        result = parse_end_condition("FREQ=DAILY")
        assert result is None


# ── Parser: Errors ───────────────────────────────────────────────────────


class TestParseRruleErrors:
    def test_empty_string(self):
        with pytest.raises(ValueError, match="must not be empty"):
            parse_rrule("")

    def test_invalid_freq(self):
        with pytest.raises(ValueError, match="Unsupported FREQ"):
            parse_rrule("FREQ=INVALID")

    def test_monthly_byday_without_prefix(self):
        """D-05: plain BYDAY in monthly context must raise."""
        with pytest.raises(ValueError, match="positional prefix"):
            parse_rrule("FREQ=MONTHLY;BYDAY=TU")

    def test_bysetpos_rejected(self):
        """D-05: BYSETPOS raises educational error."""
        with pytest.raises(ValueError, match="BYSETPOS is not supported"):
            parse_rrule("FREQ=WEEKLY;BYSETPOS=2")

    def test_count_and_until_mutually_exclusive(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            parse_rrule("FREQ=DAILY;COUNT=5;UNTIL=20261231T000000Z")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="must not be empty"):
            parse_rrule("   ")

    def test_missing_freq(self):
        with pytest.raises(ValueError, match="FREQ is required"):
            parse_rrule("INTERVAL=3")


# ── Builder ──────────────────────────────────────────────────────────────


class TestBuildRrule:
    def test_daily(self):
        assert build_rrule(DailyFrequency()) == "FREQ=DAILY"

    def test_daily_with_interval(self):
        assert build_rrule(DailyFrequency(interval=3)) == "FREQ=DAILY;INTERVAL=3"

    def test_weekly_with_byday(self):
        result = build_rrule(WeeklyFrequency(on_days=["MO", "WE", "FR"]))
        assert result == "FREQ=WEEKLY;BYDAY=MO,WE,FR"

    def test_weekly_bare(self):
        assert build_rrule(WeeklyFrequency()) == "FREQ=WEEKLY"

    def test_monthly_plain(self):
        assert build_rrule(MonthlyFrequency()) == "FREQ=MONTHLY"

    def test_monthly_day_of_week(self):
        result = build_rrule(MonthlyDayOfWeekFrequency(on={"second": "tuesday"}))
        assert result == "FREQ=MONTHLY;BYDAY=2TU"

    def test_monthly_last_friday(self):
        result = build_rrule(MonthlyDayOfWeekFrequency(on={"last": "friday"}))
        assert result == "FREQ=MONTHLY;BYDAY=-1FR"

    def test_monthly_day_in_month(self):
        result = build_rrule(MonthlyDayInMonthFrequency(on_dates=[15]))
        assert result == "FREQ=MONTHLY;BYMONTHDAY=15"

    def test_monthly_last_day(self):
        result = build_rrule(MonthlyDayInMonthFrequency(on_dates=[-1]))
        assert result == "FREQ=MONTHLY;BYMONTHDAY=-1"

    def test_yearly(self):
        assert build_rrule(YearlyFrequency()) == "FREQ=YEARLY"

    def test_minutely(self):
        assert build_rrule(MinutelyFrequency(interval=30)) == "FREQ=MINUTELY;INTERVAL=30"

    def test_hourly(self):
        assert build_rrule(HourlyFrequency(interval=2)) == "FREQ=HOURLY;INTERVAL=2"

    def test_with_end_count(self):
        result = build_rrule(WeeklyFrequency(), end=EndByOccurrences(occurrences=10))
        assert result == "FREQ=WEEKLY;COUNT=10"

    def test_with_end_until(self):
        result = build_rrule(MonthlyFrequency(), end=EndByDate(date="2026-12-31T00:00:00Z"))
        assert result == "FREQ=MONTHLY;UNTIL=20261231T000000Z"


# ── Round Trip ───────────────────────────────────────────────────────────


class TestRoundTrip:
    """parse -> build -> parse produces identical results for all frequency types."""

    @pytest.mark.parametrize(
        "rrule_string",
        [
            "FREQ=MINUTELY;INTERVAL=30",
            "FREQ=HOURLY;INTERVAL=2",
            "FREQ=DAILY",
            "FREQ=DAILY;INTERVAL=3",
            "FREQ=WEEKLY",
            "FREQ=WEEKLY;BYDAY=MO,WE,FR",
            "FREQ=MONTHLY",
            "FREQ=MONTHLY;BYDAY=2TU",
            "FREQ=MONTHLY;BYDAY=-1FR",
            "FREQ=MONTHLY;BYMONTHDAY=15",
            "FREQ=MONTHLY;BYMONTHDAY=-1",
            "FREQ=YEARLY",
        ],
    )
    def test_round_trip_frequency(self, rrule_string: str):
        freq = parse_rrule(rrule_string)
        rebuilt = build_rrule(freq)
        re_parsed = parse_rrule(rebuilt)
        assert re_parsed == freq

    @pytest.mark.parametrize(
        "rrule_string",
        [
            "FREQ=WEEKLY;COUNT=10",
            "FREQ=MONTHLY;UNTIL=20261231T000000Z",
        ],
    )
    def test_round_trip_with_end_condition(self, rrule_string: str):
        freq = parse_rrule(rrule_string)
        end = parse_end_condition(rrule_string)
        rebuilt = build_rrule(freq, end=end)
        re_parsed_freq = parse_rrule(rebuilt)
        re_parsed_end = parse_end_condition(rebuilt)
        assert re_parsed_freq == freq
        assert re_parsed_end == end


# ── Golden Master RRULE Strings ──────────────────────────────────────────

GOLDEN_MASTER_DIR = Path(__file__).parent / "golden_master" / "snapshots" / "08-repetition"


def _collect_rule_strings() -> list[str]:
    """Extract all unique ruleString values from golden master snapshots."""
    rule_strings: set[str] = set()
    if not GOLDEN_MASTER_DIR.exists():
        return []
    for json_file in sorted(GOLDEN_MASTER_DIR.glob("*.json")):
        data = json.loads(json_file.read_text())
        _extract_rule_strings(data, rule_strings)
    return sorted(rule_strings)


def _extract_rule_strings(obj: object, collector: set[str]) -> None:
    """Recursively find ruleString values in nested JSON."""
    if isinstance(obj, dict):
        if "ruleString" in obj and isinstance(obj["ruleString"], str):
            collector.add(obj["ruleString"])
        for v in obj.values():
            _extract_rule_strings(v, collector)
    elif isinstance(obj, list):
        for item in obj:
            _extract_rule_strings(item, collector)


_GOLDEN_MASTER_RULES = _collect_rule_strings()


class TestGoldenMasterRuleStrings:
    """Every RRULE string found in golden master snapshots must parse without error."""

    @pytest.mark.parametrize("rule_string", _GOLDEN_MASTER_RULES)
    def test_golden_master_parses(self, rule_string: str):
        result = parse_rrule(rule_string)
        assert hasattr(result, "type")
