"""Tests for the RRULE validator spike."""

import pytest

from rrule_validator import RRuleComponents, validate_rrule


# ── Valid rules ──────────────────────────────────────────────────────────


class TestValidBasicFrequencies:
    def test_daily(self):
        r = validate_rrule("FREQ=DAILY")
        assert r.freq == "DAILY"

    def test_weekly(self):
        r = validate_rrule("FREQ=WEEKLY")
        assert r.freq == "WEEKLY"

    def test_monthly(self):
        r = validate_rrule("FREQ=MONTHLY")
        assert r.freq == "MONTHLY"

    def test_yearly(self):
        r = validate_rrule("FREQ=YEARLY")
        assert r.freq == "YEARLY"


class TestValidWithInterval:
    def test_daily_interval_3(self):
        r = validate_rrule("FREQ=DAILY;INTERVAL=3")
        assert r.freq == "DAILY"
        assert r.interval == 3

    def test_weekly_interval_2(self):
        r = validate_rrule("FREQ=WEEKLY;INTERVAL=2")
        assert r.interval == 2


class TestValidDayOfWeek:
    def test_single_day(self):
        r = validate_rrule("FREQ=WEEKLY;BYDAY=MO")
        assert r.byday == ["MO"]

    def test_multiple_days(self):
        r = validate_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR")
        assert r.byday == ["MO", "WE", "FR"]


class TestValidDayOfMonth:
    def test_first_day(self):
        r = validate_rrule("FREQ=MONTHLY;BYMONTHDAY=1")
        assert r.bymonthday == 1

    def test_last_day(self):
        r = validate_rrule("FREQ=MONTHLY;BYMONTHDAY=-1")
        assert r.bymonthday == -1

    def test_day_31(self):
        r = validate_rrule("FREQ=MONTHLY;BYMONTHDAY=31")
        assert r.bymonthday == 31


class TestValidNthWeekday:
    def test_second_tuesday(self):
        r = validate_rrule("FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2")
        assert r.byday == ["TU"]
        assert r.bysetpos == 2

    def test_first_friday(self):
        r = validate_rrule("FREQ=MONTHLY;BYDAY=FR;BYSETPOS=1")
        assert r.bysetpos == 1

    def test_last_monday(self):
        r = validate_rrule("FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-1")
        assert r.bysetpos == -1


class TestValidCountAndUntil:
    def test_with_count(self):
        r = validate_rrule("FREQ=WEEKLY;COUNT=10")
        assert r.count == 10

    def test_with_until(self):
        r = validate_rrule("FREQ=MONTHLY;UNTIL=20261231T000000Z")
        assert r.until == "20261231T000000Z"


class TestValidCombined:
    def test_weekly_biweekly_tu_th(self):
        r = validate_rrule("FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH")
        assert r.freq == "WEEKLY"
        assert r.interval == 2
        assert r.byday == ["TU", "TH"]

    def test_all_none_by_default(self):
        r = validate_rrule("FREQ=DAILY")
        assert r.interval is None
        assert r.byday is None
        assert r.bymonthday is None
        assert r.bysetpos is None
        assert r.count is None
        assert r.until is None


# ── Invalid rules ────────────────────────────────────────────────────────


class TestInvalidEmpty:
    def test_empty_string(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_rrule("")

    def test_whitespace_only(self):
        with pytest.raises(ValueError, match="must not be empty"):
            validate_rrule("   ")


class TestInvalidMissingFreq:
    def test_no_freq(self):
        with pytest.raises(ValueError, match="FREQ is required"):
            validate_rrule("INTERVAL=3")


class TestInvalidFreqValue:
    def test_secondly(self):
        with pytest.raises(ValueError, match="Invalid FREQ"):
            validate_rrule("FREQ=SECONDLY")

    def test_minutely(self):
        with pytest.raises(ValueError, match="Invalid FREQ"):
            validate_rrule("FREQ=MINUTELY")

    def test_lowercase(self):
        with pytest.raises(ValueError, match="Invalid FREQ"):
            validate_rrule("FREQ=daily")


class TestInvalidUnknownKey:
    def test_unknown_key(self):
        with pytest.raises(ValueError, match="Unknown key.*FOO"):
            validate_rrule("FREQ=WEEKLY;FOO=BAR")

    def test_wkst(self):
        with pytest.raises(ValueError, match="Unknown key.*WKST"):
            validate_rrule("FREQ=WEEKLY;WKST=MO")


class TestInvalidByday:
    def test_bad_day_code(self):
        with pytest.raises(ValueError, match="Invalid day code.*XX"):
            validate_rrule("FREQ=WEEKLY;BYDAY=XX")

    def test_lowercase_day(self):
        with pytest.raises(ValueError, match="Invalid day code.*mo"):
            validate_rrule("FREQ=WEEKLY;BYDAY=mo")


class TestInvalidInterval:
    def test_zero(self):
        with pytest.raises(ValueError, match="positive integer"):
            validate_rrule("FREQ=DAILY;INTERVAL=0")

    def test_negative(self):
        with pytest.raises(ValueError, match="positive integer"):
            validate_rrule("FREQ=DAILY;INTERVAL=-1")

    def test_non_numeric(self):
        with pytest.raises(ValueError, match="positive integer"):
            validate_rrule("FREQ=DAILY;INTERVAL=abc")


class TestInvalidStructure:
    def test_trailing_semicolon(self):
        with pytest.raises(ValueError, match="Trailing semicolon"):
            validate_rrule("FREQ=WEEKLY;")

    def test_empty_value(self):
        with pytest.raises(ValueError, match="Empty value"):
            validate_rrule("FREQ=WEEKLY;BYDAY=")

    def test_duplicate_keys(self):
        with pytest.raises(ValueError, match="Duplicate key"):
            validate_rrule("FREQ=WEEKLY;FREQ=DAILY")


class TestInvalidCountUntilExclusion:
    def test_both_present(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            validate_rrule("FREQ=WEEKLY;COUNT=10;UNTIL=20261231T000000Z")


class TestInvalidBymonthday:
    def test_32(self):
        with pytest.raises(ValueError, match="BYMONTHDAY must be"):
            validate_rrule("FREQ=MONTHLY;BYMONTHDAY=32")

    def test_zero(self):
        with pytest.raises(ValueError, match="BYMONTHDAY must be"):
            validate_rrule("FREQ=MONTHLY;BYMONTHDAY=0")

    def test_too_negative(self):
        with pytest.raises(ValueError, match="BYMONTHDAY must be"):
            validate_rrule("FREQ=MONTHLY;BYMONTHDAY=-32")


class TestInvalidUntilFormat:
    def test_iso_dashes(self):
        with pytest.raises(ValueError, match="UNTIL must match"):
            validate_rrule("FREQ=MONTHLY;UNTIL=2026-12-31")

    def test_no_z_suffix(self):
        with pytest.raises(ValueError, match="UNTIL must match"):
            validate_rrule("FREQ=MONTHLY;UNTIL=20261231T000000")

    def test_date_only(self):
        with pytest.raises(ValueError, match="UNTIL must match"):
            validate_rrule("FREQ=MONTHLY;UNTIL=20261231")


class TestInvalidBysetpos:
    def test_zero(self):
        with pytest.raises(ValueError, match="must not be zero"):
            validate_rrule("FREQ=MONTHLY;BYDAY=MO;BYSETPOS=0")
