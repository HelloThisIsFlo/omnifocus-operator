"""Comprehensive tests for the pure resolve_date_filter function.

Tests organized by input form:
1. String shortcuts (today, overdue, soon, any)
2. Shorthand {this: unit} -- calendar-aligned periods
3. Shorthand {last: duration} -- rolling past
4. Shorthand {next: duration} -- rolling future
5. Absolute {before/after} -- explicit date bounds
6. Edge cases and error paths
"""

from __future__ import annotations

from datetime import UTC, datetime

import pytest

from omnifocus_operator.contracts.use_cases.list._date_filter import (
    AbsoluteRangeFilter,
    LastPeriodFilter,
    NextPeriodFilter,
    ThisPeriodFilter,
)
from omnifocus_operator.contracts.use_cases.list._enums import (
    DateShortcut,
    DueDateShortcut,
    LifecycleDateShortcut,
)
from omnifocus_operator.models.enums import DueSoonSetting
from omnifocus_operator.service.resolve_dates import ResolvedDateBounds, resolve_date_filter

# Fixed "now" for all tests: Tuesday 2026-04-07 14:00:00 UTC (tz-aware)
NOW = datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# String shortcuts
# ---------------------------------------------------------------------------


class TestTodayShortcut:
    """'today' resolves to midnight-to-midnight of current day on all fields."""

    def test_today_on_due(self) -> None:
        resolved = resolve_date_filter(DueDateShortcut.TODAY, "due", NOW)
        assert resolved.after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)

    def test_today_on_completed(self) -> None:
        resolved = resolve_date_filter(LifecycleDateShortcut.TODAY, "completed", NOW)
        assert resolved.after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)

    def test_today_at_midnight(self) -> None:
        """Today at midnight still gives same-day boundaries."""
        midnight = datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        resolved = resolve_date_filter(DueDateShortcut.TODAY, "due", midnight)
        assert resolved.after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)

    def test_today_at_end_of_day(self) -> None:
        """Today at 23:59:59 still gives same-day boundaries."""
        late = datetime(2026, 4, 7, 23, 59, 59, tzinfo=UTC)
        resolved = resolve_date_filter(DueDateShortcut.TODAY, "due", late)
        assert resolved.after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)

    def test_date_field_shortcut_today(self) -> None:
        """DateShortcut.TODAY resolves to today's midnight bounds."""

        result = resolve_date_filter(DateShortcut.TODAY, "defer", NOW)
        assert result.after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert result.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)


class TestOverdueShortcut:
    """'overdue' resolves to (None, now) -- due before current moment."""

    def test_overdue_on_due(self) -> None:
        resolved = resolve_date_filter(DueDateShortcut.OVERDUE, "due", NOW)
        assert resolved.after is None
        assert resolved.before == NOW


class TestSoonShortcut:
    """'soon' resolves using DueSoonSetting enum."""

    def test_soon_calendar_aligned(self) -> None:
        """TWO_DAYS (calendar-aligned): midnight_today + 2 days."""
        resolved = resolve_date_filter(
            DueDateShortcut.SOON,
            "due",
            NOW,
            due_soon_setting=DueSoonSetting.TWO_DAYS,
        )
        assert resolved.after is None
        assert resolved.before == datetime(2026, 4, 9, 0, 0, 0, tzinfo=UTC)

    def test_soon_rolling(self) -> None:
        """TWENTY_FOUR_HOURS (rolling): now + 1 day."""
        resolved = resolve_date_filter(
            DueDateShortcut.SOON,
            "due",
            NOW,
            due_soon_setting=DueSoonSetting.TWENTY_FOUR_HOURS,
        )
        assert resolved.after is None
        assert resolved.before == datetime(2026, 4, 8, 14, 0, 0, tzinfo=UTC)

    def test_soon_without_config_raises(self) -> None:
        """'soon' without due_soon_setting asserts (domain handles fallback)."""
        with pytest.raises(AssertionError, match="soon"):
            resolve_date_filter(DueDateShortcut.SOON, "due", NOW)

    def test_soon_today_setting(self) -> None:
        """TODAY setting (calendar-aligned): midnight_today + 1 day."""
        resolved = resolve_date_filter(
            DueDateShortcut.SOON,
            "due",
            NOW,
            due_soon_setting=DueSoonSetting.TODAY,
        )
        assert resolved.after is None
        assert resolved.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)

    def test_soon_one_week_setting(self) -> None:
        """ONE_WEEK setting (calendar-aligned): midnight_today + 7 days."""
        resolved = resolve_date_filter(
            DueDateShortcut.SOON,
            "due",
            NOW,
            due_soon_setting=DueSoonSetting.ONE_WEEK,
        )
        assert resolved.after is None
        assert resolved.before == datetime(2026, 4, 14, 0, 0, 0, tzinfo=UTC)


class TestDueSoonSettingProperties:
    """Verify all 7 DueSoonSetting enum members have correct domain properties."""

    def test_today(self) -> None:
        assert DueSoonSetting.TODAY.days == 1
        assert DueSoonSetting.TODAY.calendar_aligned is True

    def test_twenty_four_hours(self) -> None:
        assert DueSoonSetting.TWENTY_FOUR_HOURS.days == 1
        assert DueSoonSetting.TWENTY_FOUR_HOURS.calendar_aligned is False

    def test_two_days(self) -> None:
        assert DueSoonSetting.TWO_DAYS.days == 2
        assert DueSoonSetting.TWO_DAYS.calendar_aligned is True

    def test_three_days(self) -> None:
        assert DueSoonSetting.THREE_DAYS.days == 3
        assert DueSoonSetting.THREE_DAYS.calendar_aligned is True

    def test_four_days(self) -> None:
        assert DueSoonSetting.FOUR_DAYS.days == 4
        assert DueSoonSetting.FOUR_DAYS.calendar_aligned is True

    def test_five_days(self) -> None:
        assert DueSoonSetting.FIVE_DAYS.days == 5
        assert DueSoonSetting.FIVE_DAYS.calendar_aligned is True

    def test_one_week(self) -> None:
        assert DueSoonSetting.ONE_WEEK.days == 7
        assert DueSoonSetting.ONE_WEEK.calendar_aligned is True

    def test_exactly_seven_members(self) -> None:
        assert len(DueSoonSetting) == 7

    def test_only_twenty_four_hours_is_rolling(self) -> None:
        """Only TWENTY_FOUR_HOURS has calendar_aligned=False."""
        rolling = [s for s in DueSoonSetting if not s.calendar_aligned]
        assert rolling == [DueSoonSetting.TWENTY_FOUR_HOURS]


class TestAllShortcut:
    """'all' is not a date filter -- resolver should raise ValueError."""

    def test_all_raises(self) -> None:
        with pytest.raises(ValueError, match="all"):
            resolve_date_filter(LifecycleDateShortcut.ALL, "completed", NOW)


# ---------------------------------------------------------------------------
# Shorthand: {this: unit}
# ---------------------------------------------------------------------------


class TestThisDay:
    """{this: 'd'} = today boundaries (same as 'today' shortcut)."""

    def test_this_day(self) -> None:
        resolved = resolve_date_filter(ThisPeriodFilter(this="d"), "due", NOW)
        assert resolved.after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)


class TestThisWeek:
    """{this: 'w'} = calendar-aligned week boundaries respecting week_start."""

    def test_this_week_monday_start(self) -> None:
        """Now is Tuesday; Monday start -> Mon Apr 6 to Mon Apr 13? No: Apr 7 is Tuesday.
        week_start=0 (Monday). weekday() of Tuesday = 1. days_since = (1-0)%7 = 1.
        start = Apr 7 - 1 day = Apr 6. end = Apr 6 + 7 = Apr 13.

        Wait, Apr 7 2026 is a Tuesday. Previous Monday is Apr 6.
        """
        resolved = resolve_date_filter(ThisPeriodFilter(this="w"), "due", NOW, week_start=0)
        assert resolved.after == datetime(2026, 4, 6, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 13, 0, 0, 0, tzinfo=UTC)

    def test_this_week_sunday_start(self) -> None:
        """week_start=6 (Sunday). Now is Tuesday Apr 7.
        weekday() of Tuesday = 1. days_since = (1-6)%7 = 2.
        start = Apr 7 - 2 = Apr 5. end = Apr 5 + 7 = Apr 12.

        Wait, let me check: Apr 5 2026 is a Sunday. Apr 12 is also Sunday. Correct.
        """
        resolved = resolve_date_filter(ThisPeriodFilter(this="w"), "due", NOW, week_start=6)
        assert resolved.after == datetime(2026, 4, 5, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 12, 0, 0, 0, tzinfo=UTC)

    def test_this_week_on_start_day(self) -> None:
        """When now IS the week start day."""
        monday = datetime(2026, 4, 6, 10, 0, 0, tzinfo=UTC)  # Monday
        resolved = resolve_date_filter(ThisPeriodFilter(this="w"), "due", monday, week_start=0)
        assert resolved.after == datetime(2026, 4, 6, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 13, 0, 0, 0, tzinfo=UTC)


class TestThisMonth:
    """{this: 'm'} = calendar month boundaries (first of month to first of next)."""

    def test_this_month(self) -> None:
        resolved = resolve_date_filter(ThisPeriodFilter(this="m"), "due", NOW)
        assert resolved.after == datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)

    def test_this_month_december(self) -> None:
        """December wraps to January of next year."""
        dec = datetime(2026, 12, 15, 10, 0, 0, tzinfo=UTC)
        resolved = resolve_date_filter(ThisPeriodFilter(this="m"), "due", dec)
        assert resolved.after == datetime(2026, 12, 1, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2027, 1, 1, 0, 0, 0, tzinfo=UTC)

    def test_this_month_first_day(self) -> None:
        """On the first day of the month."""
        first = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        resolved = resolve_date_filter(ThisPeriodFilter(this="m"), "due", first)
        assert resolved.after == datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 5, 1, 0, 0, 0, tzinfo=UTC)


class TestThisYear:
    """{this: 'y'} = calendar year boundaries."""

    def test_this_year(self) -> None:
        resolved = resolve_date_filter(ThisPeriodFilter(this="y"), "due", NOW)
        assert resolved.after == datetime(2026, 1, 1, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2027, 1, 1, 0, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Shorthand: {last: duration}
# ---------------------------------------------------------------------------


class TestLastDuration:
    """{last: 'Nd'} = N days ago midnight through now."""

    def test_last_3_days(self) -> None:
        resolved = resolve_date_filter(LastPeriodFilter(last="3d"), "due", NOW)
        assert resolved.after == datetime(2026, 4, 4, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == NOW

    def test_last_1_week(self) -> None:
        """{last: 'w'} = 7 days ago midnight through now."""
        resolved = resolve_date_filter(LastPeriodFilter(last="w"), "due", NOW)
        assert resolved.after == datetime(2026, 3, 31, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == NOW

    def test_last_1_week_explicit(self) -> None:
        """{last: '1w'} same as {last: 'w'}."""
        resolved = resolve_date_filter(LastPeriodFilter(last="1w"), "due", NOW)
        assert resolved.after == datetime(2026, 3, 31, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == NOW

    def test_last_1_month_naive(self) -> None:
        """{last: '1m'} = 30 days ago midnight through now (RESOLVE-07 naive)."""
        resolved = resolve_date_filter(LastPeriodFilter(last="m"), "due", NOW)
        # 30 days before Apr 7 = Mar 8
        assert resolved.after == datetime(2026, 3, 8, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == NOW

    def test_last_1_year_naive(self) -> None:
        """{last: '1y'} = 365 days ago midnight through now."""
        resolved = resolve_date_filter(LastPeriodFilter(last="y"), "due", NOW)
        # 365 days before 2026-04-07 = 2025-04-07
        assert resolved.after == datetime(2025, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == NOW


# ---------------------------------------------------------------------------
# Shorthand: {next: duration}
# ---------------------------------------------------------------------------


class TestNextDuration:
    """{next: 'Nd'} = now through rest of today + N full future days."""

    def test_next_2_days(self) -> None:
        """{next: '2d'} -> now through midnight 3 days from today (rest of today + 2)."""
        resolved = resolve_date_filter(NextPeriodFilter(next="2d"), "due", NOW)
        assert resolved.after == NOW
        # midnight(now) + timedelta(days=2+1) = Apr 7 00:00 + 3d = Apr 10 00:00
        assert resolved.before == datetime(2026, 4, 10, 0, 0, 0, tzinfo=UTC)

    def test_next_1_week(self) -> None:
        """{next: '1w'} -> now through midnight 8 days from today."""
        resolved = resolve_date_filter(NextPeriodFilter(next="w"), "due", NOW)
        assert resolved.after == NOW
        # midnight(now) + 7d + 1d = Apr 7 00:00 + 8d = Apr 15 00:00
        assert resolved.before == datetime(2026, 4, 15, 0, 0, 0, tzinfo=UTC)

    def test_next_1_month_naive(self) -> None:
        """{next: '1m'} -> now through 31 days from today midnight (30d + rest of today)."""
        resolved = resolve_date_filter(NextPeriodFilter(next="m"), "due", NOW)
        assert resolved.after == NOW
        # midnight(now) + 30d + 1d = Apr 7 00:00 + 31d = May 8 00:00
        assert resolved.before == datetime(2026, 5, 8, 0, 0, 0, tzinfo=UTC)

    def test_next_1_year_naive(self) -> None:
        resolved = resolve_date_filter(NextPeriodFilter(next="y"), "due", NOW)
        assert resolved.after == NOW
        # midnight(now) + 365d + 1d = Apr 7 00:00 + 366d = Apr 8 2027 00:00
        assert resolved.before == datetime(2027, 4, 8, 0, 0, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Absolute: {before/after}
# ---------------------------------------------------------------------------


class TestAbsoluteBefore:
    """Absolute 'before' field handling."""

    def test_before_date_only(self) -> None:
        """Date-only before -> start of NEXT day (end-of-day inclusive per RESOLVE-08)."""
        resolved = resolve_date_filter(AbsoluteRangeFilter(before="2026-04-14"), "due", NOW)
        assert resolved.before == datetime(2026, 4, 15, 0, 0, 0, tzinfo=UTC)

    def test_before_datetime(self) -> None:
        """Full datetime before -> +1 minute (inclusive bound for half-open < comparison)."""
        resolved = resolve_date_filter(
            AbsoluteRangeFilter(before="2026-04-14T18:00:00Z"), "due", NOW
        )
        assert resolved.before == datetime(2026, 4, 14, 18, 1, 0, tzinfo=UTC)

    def test_before_datetime_naive(self) -> None:
        """Naive datetime before -> inherits tzinfo from NOW, then +1 minute bump."""
        resolved = resolve_date_filter(
            AbsoluteRangeFilter(before="2026-04-14T18:00:00"), "due", NOW
        )
        assert resolved.before == datetime(2026, 4, 14, 18, 1, 0, tzinfo=UTC)

    def test_before_now(self) -> None:
        """'now' -> the passed-in now timestamp."""
        resolved = resolve_date_filter(AbsoluteRangeFilter(before="now"), "due", NOW)
        assert resolved.before == NOW

    def test_before_only_after_is_none(self) -> None:
        """When only 'before' is set, after is None."""
        resolved = resolve_date_filter(AbsoluteRangeFilter(before="2026-04-14"), "due", NOW)
        assert resolved.after is None


class TestAbsoluteAfter:
    """Absolute 'after' field handling."""

    def test_after_date_only(self) -> None:
        """Date-only after -> start of that day (start-of-day inclusive per RESOLVE-09)."""
        resolved = resolve_date_filter(AbsoluteRangeFilter(after="2026-04-01"), "due", NOW)
        assert resolved.after == datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)

    def test_after_datetime(self) -> None:
        """Full datetime after -> exact value."""
        resolved = resolve_date_filter(
            AbsoluteRangeFilter(after="2026-04-01T09:00:00Z"), "due", NOW
        )
        assert resolved.after == datetime(2026, 4, 1, 9, 0, 0, tzinfo=UTC)

    def test_after_now(self) -> None:
        """'now' -> the passed-in now timestamp."""
        resolved = resolve_date_filter(AbsoluteRangeFilter(after="now"), "due", NOW)
        assert resolved.after == NOW

    def test_after_only_before_is_none(self) -> None:
        """When only 'after' is set, before is None."""
        resolved = resolve_date_filter(AbsoluteRangeFilter(after="2026-04-01"), "due", NOW)
        assert resolved.before is None


class TestAbsoluteBoth:
    """Both after and before specified."""

    def test_both_date_only(self) -> None:
        """Both date-only: after=start-of-day, before=start-of-next-day."""
        resolved = resolve_date_filter(
            AbsoluteRangeFilter(after="2026-04-01", before="2026-04-14"), "due", NOW
        )
        assert resolved.after == datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 15, 0, 0, 0, tzinfo=UTC)

    def test_both_datetime(self) -> None:
        resolved = resolve_date_filter(
            AbsoluteRangeFilter(after="2026-04-01T09:00:00Z", before="2026-04-14T18:00:00Z"),
            "due",
            NOW,
        )
        assert resolved.after == datetime(2026, 4, 1, 9, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 14, 18, 1, 0, tzinfo=UTC)


# ---------------------------------------------------------------------------
# Pure function contract
# ---------------------------------------------------------------------------


class TestPureFunctionContract:
    """Resolver is a pure function with no I/O."""

    def test_same_inputs_same_outputs(self) -> None:
        """Calling twice with same inputs produces same outputs."""
        result1 = resolve_date_filter(DueDateShortcut.TODAY, "due", NOW)
        result2 = resolve_date_filter(DueDateShortcut.TODAY, "due", NOW)
        assert result1 == result2

    def test_different_now_different_outputs(self) -> None:
        """Different 'now' values produce different 'today' boundaries."""
        r1 = resolve_date_filter(
            DueDateShortcut.TODAY, "due", datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)
        )
        r2 = resolve_date_filter(
            DueDateShortcut.TODAY, "due", datetime(2026, 4, 8, 14, 0, 0, tzinfo=UTC)
        )
        assert r1 != r2


# ---------------------------------------------------------------------------
# ResolvedDateBounds return type
# ---------------------------------------------------------------------------


class TestResolvedDateBoundsReturnType:
    """resolve_date_filter returns ResolvedDateBounds with .after and .before."""

    def test_overdue_returns_resolved_date_bounds(self) -> None:
        resolved = resolve_date_filter(DueDateShortcut.OVERDUE, "due", NOW)
        assert isinstance(resolved, ResolvedDateBounds)
        assert resolved.after is None
        assert resolved.before == NOW

    def test_soon_with_setting_returns_resolved_date_bounds(self) -> None:
        resolved = resolve_date_filter(
            DueDateShortcut.SOON,
            "due",
            NOW,
            due_soon_setting=DueSoonSetting.TWO_DAYS,
        )
        assert isinstance(resolved, ResolvedDateBounds)
        assert resolved.after is None
        assert resolved.before == datetime(2026, 4, 9, 0, 0, 0, tzinfo=UTC)

    def test_date_filter_obj_returns_resolved_date_bounds(self) -> None:
        resolved = resolve_date_filter(ThisPeriodFilter(this="d"), "due", NOW)
        assert isinstance(resolved, ResolvedDateBounds)
        assert resolved.after == datetime(2026, 4, 7, 0, 0, 0, tzinfo=UTC)
        assert resolved.before == datetime(2026, 4, 8, 0, 0, 0, tzinfo=UTC)
