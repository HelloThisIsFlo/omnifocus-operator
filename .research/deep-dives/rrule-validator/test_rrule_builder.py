"""Tests for the RRULE builder."""

import pytest

from rrule_validator import build_rrule, validate_rrule


# -- Basic builds ------------------------------------------------------------


class TestBasicBuilds:
    def test_weekly(self):
        assert build_rrule("WEEKLY") == "FREQ=WEEKLY"

    def test_daily(self):
        assert build_rrule("DAILY") == "FREQ=DAILY"

    def test_monthly(self):
        assert build_rrule("MONTHLY") == "FREQ=MONTHLY"

    def test_yearly(self):
        assert build_rrule("YEARLY") == "FREQ=YEARLY"


# -- With interval ------------------------------------------------------------


class TestWithInterval:
    def test_daily_interval_3(self):
        assert build_rrule("DAILY", interval=3) == "FREQ=DAILY;INTERVAL=3"

    def test_weekly_interval_2(self):
        assert build_rrule("WEEKLY", interval=2) == "FREQ=WEEKLY;INTERVAL=2"


# -- With byday ---------------------------------------------------------------


class TestWithByday:
    def test_single_day(self):
        assert build_rrule("WEEKLY", byday=["MO"]) == "FREQ=WEEKLY;BYDAY=MO"

    def test_multiple_days(self):
        assert build_rrule("WEEKLY", byday=["MO", "WE", "FR"]) == "FREQ=WEEKLY;BYDAY=MO,WE,FR"


# -- Monthly by day -----------------------------------------------------------


class TestMonthlyByDay:
    def test_bymonthday_15(self):
        assert build_rrule("MONTHLY", bymonthday=15) == "FREQ=MONTHLY;BYMONTHDAY=15"

    def test_bymonthday_last(self):
        assert build_rrule("MONTHLY", bymonthday=-1) == "FREQ=MONTHLY;BYMONTHDAY=-1"


# -- Nth weekday (bysetpos) ---------------------------------------------------


class TestNthWeekday:
    def test_second_tuesday(self):
        assert build_rrule("MONTHLY", byday=["TU"], bysetpos=2) == "FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2"

    def test_last_monday(self):
        assert (
            build_rrule("MONTHLY", byday=["MO"], bysetpos=-1) == "FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-1"
        )


# -- With count ---------------------------------------------------------------


class TestWithCount:
    def test_count_10(self):
        assert build_rrule("WEEKLY", count=10) == "FREQ=WEEKLY;COUNT=10"


# -- With until ---------------------------------------------------------------


class TestWithUntil:
    def test_until(self):
        assert build_rrule("MONTHLY", until="20261231T000000Z") == "FREQ=MONTHLY;UNTIL=20261231T000000Z"


# -- Complex combinations -----------------------------------------------------


class TestComplex:
    def test_biweekly_tu_th(self):
        assert (
            build_rrule("WEEKLY", interval=2, byday=["TU", "TH"])
            == "FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH"
        )

    def test_monthly_15th_with_count(self):
        assert (
            build_rrule("MONTHLY", bymonthday=15, count=6)
            == "FREQ=MONTHLY;BYMONTHDAY=15;COUNT=6"
        )


# -- Round-trip validation -----------------------------------------------------


class TestRoundTrip:
    """Verify that validate_rrule(build_rrule(...)) returns matching components."""

    def test_simple(self):
        result = build_rrule("WEEKLY")
        c = validate_rrule(result)
        assert c.freq == "WEEKLY"
        assert c.interval is None

    def test_with_all_fields(self):
        result = build_rrule("WEEKLY", interval=2, byday=["MO", "FR"], count=12)
        c = validate_rrule(result)
        assert c.freq == "WEEKLY"
        assert c.interval == 2
        assert c.byday == ["MO", "FR"]
        assert c.count == 12
        assert c.until is None

    def test_nth_weekday_round_trip(self):
        result = build_rrule("MONTHLY", byday=["TU"], bysetpos=2)
        c = validate_rrule(result)
        assert c.freq == "MONTHLY"
        assert c.byday == ["TU"]
        assert c.bysetpos == 2

    def test_until_round_trip(self):
        result = build_rrule("YEARLY", until="20301231T235959Z")
        c = validate_rrule(result)
        assert c.freq == "YEARLY"
        assert c.until == "20301231T235959Z"


# -- Error cases ---------------------------------------------------------------


class TestInvalidFreq:
    def test_invalid_freq(self):
        with pytest.raises(ValueError, match="Invalid FREQ"):
            build_rrule("SECONDLY")

    def test_lowercase_freq(self):
        with pytest.raises(ValueError, match="Invalid FREQ"):
            build_rrule("daily")


class TestInvalidDayCodes:
    def test_bad_day_code(self):
        with pytest.raises(ValueError, match="Invalid day code"):
            build_rrule("WEEKLY", byday=["XX"])

    def test_lowercase_day(self):
        with pytest.raises(ValueError, match="Invalid day code"):
            build_rrule("WEEKLY", byday=["mo"])

    def test_empty_byday_list(self):
        with pytest.raises(ValueError, match="non-empty list"):
            build_rrule("WEEKLY", byday=[])


class TestInvalidBysetpos:
    def test_bysetpos_without_byday(self):
        with pytest.raises(ValueError, match="BYSETPOS requires BYDAY"):
            build_rrule("MONTHLY", bysetpos=2)

    def test_bysetpos_zero(self):
        with pytest.raises(ValueError, match="non-zero integer"):
            build_rrule("MONTHLY", byday=["MO"], bysetpos=0)


class TestInvalidCountUntil:
    def test_count_and_until(self):
        with pytest.raises(ValueError, match="mutually exclusive"):
            build_rrule("WEEKLY", count=10, until="20261231T000000Z")


class TestInvalidInterval:
    def test_zero_interval(self):
        with pytest.raises(ValueError, match="positive integer"):
            build_rrule("DAILY", interval=0)

    def test_negative_interval(self):
        with pytest.raises(ValueError, match="positive integer"):
            build_rrule("DAILY", interval=-1)


class TestInvalidCount:
    def test_zero_count(self):
        with pytest.raises(ValueError, match="positive integer"):
            build_rrule("WEEKLY", count=0)

    def test_negative_count(self):
        with pytest.raises(ValueError, match="positive integer"):
            build_rrule("WEEKLY", count=-5)


class TestInvalidBymonthday:
    def test_zero(self):
        with pytest.raises(ValueError, match="BYMONTHDAY"):
            build_rrule("MONTHLY", bymonthday=0)

    def test_too_high(self):
        with pytest.raises(ValueError, match="BYMONTHDAY"):
            build_rrule("MONTHLY", bymonthday=32)

    def test_too_negative(self):
        with pytest.raises(ValueError, match="BYMONTHDAY"):
            build_rrule("MONTHLY", bymonthday=-32)


class TestInvalidUntil:
    def test_bad_format(self):
        with pytest.raises(ValueError, match="UNTIL must match"):
            build_rrule("MONTHLY", until="2026-12-31")

    def test_no_z_suffix(self):
        with pytest.raises(ValueError, match="UNTIL must match"):
            build_rrule("MONTHLY", until="20261231T000000")
