"""Tests for repetition rule models, RRULE parser, and RRULE builder."""

from __future__ import annotations

import json
from datetime import date
from pathlib import Path

import pytest
from pydantic import ValidationError

from omnifocus_operator.models.repetition_rule import (
    BasedOn,
    EndByDate,
    EndByOccurrences,
    Frequency,
    OrdinalWeekday,
    RepetitionRule,
    Schedule,
)
from omnifocus_operator.rrule import build_rrule, derive_schedule, parse_end_condition, parse_rrule

# ── Frequency Flat Model ─────────────────────────────────────────────────


class TestFrequencyFlatModel:
    """Frequency validates with type field and optional specialization fields."""

    def test_daily_validates(self):
        result = Frequency(type="daily")
        assert result.type == "daily"
        assert result.interval == 1

    def test_weekly_with_on_days_validates(self):
        result = Frequency(type="weekly", on_days=["MO", "WE"])
        assert result.type == "weekly"
        assert result.on_days == ["MO", "WE"]

    def test_monthly_with_on_validates(self):
        result = Frequency(type="monthly", on={"second": "tuesday"})
        assert result.type == "monthly"
        assert result.on == OrdinalWeekday(second="tuesday")

    def test_monthly_with_on_dates_validates(self):
        result = Frequency(type="monthly", on_dates=[15, -1])
        assert result.type == "monthly"
        assert result.on_dates == [15, -1]


# ── Frequency Serialization ─────────────────────────────────────────────


class TestFrequencySerialization:
    """model_dump(by_alias=True) produces correct output."""

    def test_daily_default_interval(self):
        d = Frequency(type="daily").model_dump(by_alias=True)
        assert d == {"type": "daily", "interval": 1, "onDays": None, "on": None, "onDates": None}

    def test_daily_interval_3_includes_interval(self):
        d = Frequency(type="daily", interval=3).model_dump(by_alias=True)
        assert d["interval"] == 3

    def test_weekly_on_days_serializes_as_camel_case(self):
        d = Frequency(type="weekly", on_days=["MO"]).model_dump(by_alias=True)
        assert d["onDays"] == ["MO"]

    def test_weekly_bare_has_none_on_days(self):
        d = Frequency(type="weekly").model_dump(by_alias=True)
        assert d["onDays"] is None

    def test_monthly_with_on_type_stays_snake_case(self):
        """Type value is a Literal, NOT camelCased."""
        d = Frequency(type="monthly", on={"second": "tuesday"}).model_dump(
            by_alias=True, exclude_defaults=True
        )
        assert d["type"] == "monthly"
        assert d["on"] == {"second": "tuesday"}

    def test_monthly_with_on_dates(self):
        d = Frequency(type="monthly", on_dates=[15, -1]).model_dump(by_alias=True)
        assert d["onDates"] == [15, -1]

    def test_minutely_with_interval(self):
        d = Frequency(type="minutely", interval=30).model_dump(by_alias=True)
        assert d["type"] == "minutely"
        assert d["interval"] == 30

    def test_hourly_default_interval(self):
        d = Frequency(type="hourly").model_dump(by_alias=True)
        assert d["type"] == "hourly"
        assert d["interval"] == 1

    def test_monthly_plain(self):
        d = Frequency(type="monthly").model_dump(by_alias=True)
        assert d["type"] == "monthly"

    def test_yearly_plain(self):
        d = Frequency(type="yearly").model_dump(by_alias=True)
        assert d["type"] == "yearly"


# ── Frequency Cross-Type Validation ──────────────────────────────────────


class TestFrequencyCrossTypeValidation:
    """@model_validator rejects cross-type fields and mutual exclusion."""

    def test_on_days_with_daily_raises(self):
        with pytest.raises(ValidationError, match="on_days is not valid for type 'daily'"):
            Frequency(type="daily", on_days=["MO"])

    def test_on_with_weekly_raises(self):
        with pytest.raises(ValidationError, match="on is not valid for type 'weekly'"):
            Frequency(type="weekly", on={"first": "monday"})

    def test_on_dates_with_daily_raises(self):
        with pytest.raises(ValidationError, match="on_dates is not valid for type 'daily'"):
            Frequency(type="daily", on_dates=[1])

    def test_on_and_on_dates_mutual_exclusion(self):
        with pytest.raises(ValidationError, match="mutually exclusive"):
            Frequency(type="monthly", on={"first": "monday"}, on_dates=[1])

    def test_on_days_with_weekly_succeeds(self):
        f = Frequency(type="weekly", on_days=["MO"])
        assert f.on_days == ["MO"]

    def test_on_with_monthly_succeeds(self):
        f = Frequency(type="monthly", on={"first": "monday"})
        assert f.on == OrdinalWeekday(first="monday")

    def test_on_dates_with_monthly_succeeds(self):
        f = Frequency(type="monthly", on_dates=[1])
        assert f.on_dates == [1]


# ── RepetitionRule @field_serializer ──────────────────────────────────────


class TestRepetitionRuleFieldSerializer:
    """@field_serializer on RepetitionRule suppresses interval=1 via exclude_defaults."""

    def test_interval_1_omitted_from_serialized_frequency(self):
        rule = RepetitionRule(
            frequency=Frequency(type="daily", interval=1),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert d["frequency"] == {"type": "daily"}

    def test_interval_3_included_in_serialized_frequency(self):
        rule = RepetitionRule(
            frequency=Frequency(type="daily", interval=3),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert d["frequency"] == {"type": "daily", "interval": 3}

    def test_weekly_with_on_days_serialized(self):
        rule = RepetitionRule(
            frequency=Frequency(type="weekly", on_days=["MO", "FR"]),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert d["frequency"] == {"type": "weekly", "onDays": ["MO", "FR"]}


# ── EndByOccurrences ge=1 ────────────────────────────────────────────────


class TestEndByOccurrencesValidation:
    """Runtime validator on EndByOccurrences.occurrences rejects values < 1."""

    def test_zero_raises(self):
        with pytest.raises(ValidationError, match="End occurrences must be >= 1"):
            EndByOccurrences(occurrences=0)

    def test_one_is_valid(self):
        e = EndByOccurrences(occurrences=1)
        assert e.occurrences == 1


# ── Weekly Split (Flat Model) ────────────────────────────────────────────


class TestWeeklySplit:
    """Weekly bare vs weekly with on_days using flat model."""

    def test_bare_weekly_has_none_on_days(self):
        d = Frequency(type="weekly").model_dump(by_alias=True)
        assert d["onDays"] is None

    def test_weekly_with_on_days_serializes(self):
        d = Frequency(type="weekly", on_days=["MO"]).model_dump(by_alias=True)
        assert d["onDays"] == ["MO"]

    def test_parse_bare_weekly(self):
        result = parse_rrule("FREQ=WEEKLY")
        assert result.type == "weekly"
        assert result.on_days is None

    def test_parse_weekly_with_byday(self):
        result = parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE")
        assert result.type == "weekly"
        assert result.on_days == ["MO", "WE"]

    def test_build_bare_weekly(self):
        assert build_rrule(Frequency(type="weekly")) == "FREQ=WEEKLY"

    def test_build_weekly_on_days(self):
        result = build_rrule(Frequency(type="weekly", on_days=["MO", "WE"]))
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
        e = EndByDate(date=date(2026, 12, 31))
        d = e.model_dump(by_alias=True)
        assert d == {"date": date(2026, 12, 31)}

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
            frequency=Frequency(type="daily", interval=3),
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
            frequency=Frequency(type="weekly", on_days=["MO", "FR"]),
            schedule=Schedule.FROM_COMPLETION,
            based_on=BasedOn.DEFER_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert d["end"] is None

    def test_based_on_serializes_as_camel_case(self):
        rule = RepetitionRule(
            frequency=Frequency(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.PLANNED_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert "basedOn" in d
        assert d["basedOn"] == "planned_date"

    def test_frequency_interval_1_excluded_via_serializer(self):
        """@field_serializer uses exclude_defaults -- interval=1 omitted."""
        rule = RepetitionRule(
            frequency=Frequency(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        d = rule.model_dump(by_alias=True)
        assert "interval" not in d["frequency"]


# ── Parser: Frequency Types ──────────────────────────────────────────────


class TestParseRruleFrequencyTypes:
    """parse_rrule returns correct flat Frequency for each type."""

    def test_daily(self):
        result = parse_rrule("FREQ=DAILY")
        assert result == Frequency(type="daily")

    def test_weekly_bare(self):
        result = parse_rrule("FREQ=WEEKLY")
        assert result == Frequency(type="weekly")

    def test_weekly_with_byday(self):
        result = parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR")
        assert result == Frequency(type="weekly", on_days=["MO", "WE", "FR"])

    def test_monthly_plain(self):
        result = parse_rrule("FREQ=MONTHLY")
        assert result == Frequency(type="monthly")

    def test_monthly_day_of_week(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=2TU")
        assert result == Frequency(type="monthly", on={"second": "tuesday"})

    def test_monthly_last_friday(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=-1FR")
        assert result == Frequency(type="monthly", on={"last": "friday"})

    def test_monthly_day_in_month(self):
        result = parse_rrule("FREQ=MONTHLY;BYMONTHDAY=15")
        assert result == Frequency(type="monthly", on_dates=[15])

    def test_monthly_last_day(self):
        result = parse_rrule("FREQ=MONTHLY;BYMONTHDAY=-1")
        assert result == Frequency(type="monthly", on_dates=[-1])

    def test_monthly_bymonthday_multi_values(self):
        result = parse_rrule("FREQ=MONTHLY;BYMONTHDAY=1,15,-1")
        assert result == Frequency(type="monthly", on_dates=[1, 15, -1])

    def test_yearly(self):
        result = parse_rrule("FREQ=YEARLY")
        assert result == Frequency(type="yearly")

    def test_minutely(self):
        result = parse_rrule("FREQ=MINUTELY;INTERVAL=30")
        assert result == Frequency(type="minutely", interval=30)

    def test_hourly(self):
        result = parse_rrule("FREQ=HOURLY;INTERVAL=2")
        assert result == Frequency(type="hourly", interval=2)


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
        assert result == EndByDate(date=date(2026, 12, 31))

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

    def test_bysetpos_non_monthly_rejected(self):
        """BYSETPOS is only valid for MONTHLY frequency."""
        with pytest.raises(ValueError, match="BYSETPOS is only supported with FREQ=MONTHLY"):
            parse_rrule("FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2")

    def test_bysetpos_unknown_day_group_rejected(self):
        """Unknown multi-day BYSETPOS combos raise educational error."""
        with pytest.raises(ValueError, match="Unknown BYDAY day group"):
            parse_rrule("FREQ=MONTHLY;BYDAY=MO,WE;BYSETPOS=1")

    def test_count_and_until_mutually_exclusive(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            parse_rrule("FREQ=DAILY;COUNT=5;UNTIL=20261231T000000Z")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="must not be empty"):
            parse_rrule("   ")

    def test_missing_freq(self):
        with pytest.raises(ValueError, match="FREQ is required"):
            parse_rrule("INTERVAL=3")


# ── Parser: BYSETPOS (Multi-Day Positional) ─────────────────────────────


class TestParseRruleBysetpos:
    """BYSETPOS with multi-day groups parses to monthly with on field."""

    def test_first_weekend_day(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1")
        assert result == Frequency(type="monthly", on={"first": "weekend_day"})

    def test_second_weekday(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2")
        assert result == Frequency(type="monthly", on={"second": "weekday"})

    def test_last_weekend_day_sa_su_order(self):
        """SA,SU order also recognized as weekend_day group."""
        result = parse_rrule("FREQ=MONTHLY;BYDAY=SA,SU;BYSETPOS=-1")
        assert result == Frequency(type="monthly", on={"last": "weekend_day"})

    def test_fifth_weekday(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=5")
        assert result == Frequency(type="monthly", on={"fifth": "weekday"})

    def test_third_weekend_day(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=3")
        assert result == Frequency(type="monthly", on={"third": "weekend_day"})

    def test_fourth_weekday(self):
        result = parse_rrule("FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=4")
        assert result == Frequency(type="monthly", on={"fourth": "weekday"})

    def test_with_interval(self):
        result = parse_rrule("FREQ=MONTHLY;INTERVAL=2;BYDAY=SU,SA;BYSETPOS=1")
        assert result == Frequency(type="monthly", interval=2, on={"first": "weekend_day"})


# ── Builder: BYSETPOS ───────────────────────────────────────────────────


class TestBuildRruleBysetpos:
    """Builder emits BYSETPOS form for day group values (weekday/weekend_day)."""

    def test_first_weekend_day(self):
        result = build_rrule(Frequency(type="monthly", on={"first": "weekend_day"}))
        assert result == "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1"

    def test_second_weekday(self):
        result = build_rrule(Frequency(type="monthly", on={"second": "weekday"}))
        assert result == "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2"

    def test_last_weekend_day(self):
        result = build_rrule(Frequency(type="monthly", on={"last": "weekend_day"}))
        assert result == "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=-1"


# ── Builder ──────────────────────────────────────────────────────────────


class TestBuildRrule:
    def test_daily(self):
        assert build_rrule(Frequency(type="daily")) == "FREQ=DAILY"

    def test_daily_with_interval(self):
        assert build_rrule(Frequency(type="daily", interval=3)) == "FREQ=DAILY;INTERVAL=3"

    def test_weekly_with_byday(self):
        result = build_rrule(Frequency(type="weekly", on_days=["MO", "WE", "FR"]))
        assert result == "FREQ=WEEKLY;BYDAY=MO,WE,FR"

    def test_weekly_bare(self):
        assert build_rrule(Frequency(type="weekly")) == "FREQ=WEEKLY"

    def test_monthly_plain(self):
        assert build_rrule(Frequency(type="monthly")) == "FREQ=MONTHLY"

    def test_monthly_day_of_week(self):
        result = build_rrule(Frequency(type="monthly", on={"second": "tuesday"}))
        assert result == "FREQ=MONTHLY;BYDAY=2TU"

    def test_monthly_last_friday(self):
        result = build_rrule(Frequency(type="monthly", on={"last": "friday"}))
        assert result == "FREQ=MONTHLY;BYDAY=-1FR"

    def test_monthly_day_in_month(self):
        result = build_rrule(Frequency(type="monthly", on_dates=[15]))
        assert result == "FREQ=MONTHLY;BYMONTHDAY=15"

    def test_monthly_last_day(self):
        result = build_rrule(Frequency(type="monthly", on_dates=[-1]))
        assert result == "FREQ=MONTHLY;BYMONTHDAY=-1"

    def test_monthly_day_in_month_multi_values(self):
        result = build_rrule(Frequency(type="monthly", on_dates=[1, 15, -1]))
        assert result == "FREQ=MONTHLY;BYMONTHDAY=1,15,-1"

    def test_yearly(self):
        assert build_rrule(Frequency(type="yearly")) == "FREQ=YEARLY"

    def test_minutely(self):
        assert build_rrule(Frequency(type="minutely", interval=30)) == "FREQ=MINUTELY;INTERVAL=30"

    def test_hourly(self):
        assert build_rrule(Frequency(type="hourly", interval=2)) == "FREQ=HOURLY;INTERVAL=2"

    def test_with_end_count(self):
        result = build_rrule(Frequency(type="weekly"), end=EndByOccurrences(occurrences=10))
        assert result == "FREQ=WEEKLY;COUNT=10"

    def test_with_end_until(self):
        result = build_rrule(Frequency(type="monthly"), end=EndByDate(date=date(2026, 12, 31)))
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
            "FREQ=MONTHLY;BYMONTHDAY=1,15,-1",
            "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1",
            "FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2",
            "FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=-1",
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


# -- derive_schedule ----------------------------------------------------------


class TestDeriveSchedule:
    """derive_schedule maps (schedule_type, catch_up) to 3-value schedule string."""

    def test_from_completion_without_catch_up(self):
        assert derive_schedule("from_completion", False) == "from_completion"

    def test_from_completion_with_catch_up_true(self):
        """Critical regression: from_completion + catch_up=True must NOT raise."""
        assert derive_schedule("from_completion", True) == "from_completion"

    def test_regularly_without_catch_up(self):
        assert derive_schedule("regularly", False) == "regularly"

    def test_regularly_with_catch_up(self):
        assert derive_schedule("regularly", True) == "regularly_with_catch_up"
