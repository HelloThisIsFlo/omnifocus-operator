"""Tests for DateFilter contract model and date shortcut StrEnums."""

import pytest
from pydantic import BaseModel

from omnifocus_operator.contracts.use_cases.list import (
    DateFilter,
    DueDateShortcut,
    LifecycleDateShortcut,
)

# ---------------------------------------------------------------------------
# DueDateShortcut StrEnum (DATE-06)
# ---------------------------------------------------------------------------


class TestDueDateShortcut:
    def test_overdue(self) -> None:
        assert DueDateShortcut("overdue") == DueDateShortcut.OVERDUE

    def test_soon(self) -> None:
        assert DueDateShortcut("soon") == DueDateShortcut.SOON

    def test_today(self) -> None:
        assert DueDateShortcut("today") == DueDateShortcut.TODAY

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            DueDateShortcut("invalid")


# ---------------------------------------------------------------------------
# LifecycleDateShortcut StrEnum (DATE-06)
# ---------------------------------------------------------------------------


class TestLifecycleDateShortcut:
    def test_any(self) -> None:
        assert LifecycleDateShortcut("any") == LifecycleDateShortcut.ANY

    def test_today(self) -> None:
        assert LifecycleDateShortcut("today") == LifecycleDateShortcut.TODAY

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            LifecycleDateShortcut("invalid")


# ---------------------------------------------------------------------------
# DateFilter: Valid shorthand (DATE-02, DATE-03)
# ---------------------------------------------------------------------------


class TestDateFilterValidShorthand:
    def test_this_day(self) -> None:
        f = DateFilter(this="d")
        assert f.this == "d"

    def test_last_3d(self) -> None:
        f = DateFilter(last="3d")
        assert f.last == "3d"

    def test_next_week(self) -> None:
        f = DateFilter(next="w")
        assert f.next == "w"

    def test_last_2m(self) -> None:
        f = DateFilter(last="2m")
        assert f.last == "2m"

    def test_next_1y(self) -> None:
        f = DateFilter(next="1y")
        assert f.next == "1y"

    def test_count_defaults_to_1(self) -> None:
        """'w' is valid shorthand for last/next (same as '1w')."""
        f = DateFilter(last="w")
        assert f.last == "w"


# ---------------------------------------------------------------------------
# DateFilter: Valid absolute (DATE-02)
# ---------------------------------------------------------------------------


class TestDateFilterValidAbsolute:
    def test_before_date_only(self) -> None:
        f = DateFilter(before="2026-04-14")
        assert f.before == "2026-04-14"

    def test_after_date_only(self) -> None:
        f = DateFilter(after="2026-04-01")
        assert f.after == "2026-04-01"

    def test_before_now(self) -> None:
        f = DateFilter(before="now")
        assert f.before == "now"

    def test_after_now(self) -> None:
        f = DateFilter(after="now")
        assert f.after == "now"

    def test_both_absolute_with_datetime(self) -> None:
        f = DateFilter(after="2026-04-01T14:00:00", before="2026-04-14")
        assert f.after == "2026-04-01T14:00:00"
        assert f.before == "2026-04-14"

    def test_both_now_valid(self) -> None:
        """Both bounds as 'now' is valid (no ordering check needed)."""
        f = DateFilter(after="now", before="now")
        assert f.after == "now"
        assert f.before == "now"


# ---------------------------------------------------------------------------
# DateFilter: Mutual exclusion (DATE-04)
# ---------------------------------------------------------------------------


class TestDateFilterMutualExclusion:
    def test_mixed_groups_rejected(self) -> None:
        with pytest.raises(ValueError, match="Cannot mix shorthand"):
            DateFilter(this="d", before="2026-04-14")

    def test_mixed_groups_last_and_after(self) -> None:
        with pytest.raises(ValueError, match="Cannot mix shorthand"):
            DateFilter(last="3d", after="2026-04-01")

    def test_multiple_shorthand_rejected(self) -> None:
        with pytest.raises(ValueError, match="Only one shorthand key"):
            DateFilter(this="d", last="3d")

    def test_all_three_shorthand_rejected(self) -> None:
        with pytest.raises(ValueError, match="Only one shorthand key"):
            DateFilter(this="d", last="3d", next="w")


# ---------------------------------------------------------------------------
# DateFilter: Empty filter
# ---------------------------------------------------------------------------


class TestDateFilterEmpty:
    def test_empty_filter_rejected(self) -> None:
        with pytest.raises(ValueError, match="must specify at least one key"):
            DateFilter()


# ---------------------------------------------------------------------------
# DateFilter: Duration validation (DATE-05)
# ---------------------------------------------------------------------------


class TestDateFilterDuration:
    def test_zero_count_rejected(self) -> None:
        with pytest.raises(ValueError, match="must be positive"):
            DateFilter(last="0d")

    def test_invalid_unit_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid duration"):
            DateFilter(last="3x")

    def test_negative_count_rejected(self) -> None:
        """Regex doesn't match negative, so it falls through to 'Invalid duration'."""
        with pytest.raises(ValueError, match="Invalid duration"):
            DateFilter(next="-1d")

    def test_this_only_accepts_single_unit(self) -> None:
        """'this' accepts only a bare unit char (d/w/m/y), not a count+unit."""
        with pytest.raises(ValueError, match="Invalid duration"):
            DateFilter(this="3d")

    def test_this_valid_units(self) -> None:
        for unit in ("d", "w", "m", "y"):
            f = DateFilter(this=unit)
            assert f.this == unit


# ---------------------------------------------------------------------------
# DateFilter: Absolute validation
# ---------------------------------------------------------------------------


class TestDateFilterAbsolute:
    def test_invalid_date_rejected(self) -> None:
        with pytest.raises(ValueError, match="Invalid date value"):
            DateFilter(before="not-a-date")

    def test_iso_datetime_accepted(self) -> None:
        f = DateFilter(after="2026-04-01T14:00:00")
        assert f.after == "2026-04-01T14:00:00"


# ---------------------------------------------------------------------------
# DateFilter: Reversed bounds (DATE-09)
# ---------------------------------------------------------------------------


class TestDateFilterReversedBounds:
    def test_reversed_bounds_rejected(self) -> None:
        with pytest.raises(ValueError, match="later than"):
            DateFilter(after="2026-04-14", before="2026-04-01")

    def test_equal_date_only_bounds_valid(self) -> None:
        """Equal date-only bounds are valid (matches single day per DATE-09)."""
        f = DateFilter(after="2026-04-14", before="2026-04-14")
        assert f.after == "2026-04-14"
        assert f.before == "2026-04-14"

    def test_reversed_datetime_bounds_rejected(self) -> None:
        with pytest.raises(ValueError, match="later than"):
            DateFilter(after="2026-04-14T12:00:00", before="2026-04-01T08:00:00")


# ---------------------------------------------------------------------------
# Union discrimination (preview for Plan 02)
# ---------------------------------------------------------------------------


class TestUnionDiscrimination:
    """Verify Pydantic v2 correctly discriminates string vs dict for union fields."""

    def test_string_becomes_shortcut(self) -> None:
        class _Probe(BaseModel):
            due: DueDateShortcut | DateFilter

        probe = _Probe(due="overdue")
        assert isinstance(probe.due, DueDateShortcut)
        assert probe.due == DueDateShortcut.OVERDUE

    def test_dict_becomes_date_filter(self) -> None:
        class _Probe(BaseModel):
            due: DueDateShortcut | DateFilter

        probe = _Probe(due={"this": "d"})
        assert isinstance(probe.due, DateFilter)
        assert probe.due.this == "d"

    def test_lifecycle_string_becomes_shortcut(self) -> None:
        class _Probe(BaseModel):
            completed: LifecycleDateShortcut | DateFilter

        probe = _Probe(completed="any")
        assert isinstance(probe.completed, LifecycleDateShortcut)
        assert probe.completed == LifecycleDateShortcut.ANY

    def test_lifecycle_dict_becomes_date_filter(self) -> None:
        class _Probe(BaseModel):
            completed: LifecycleDateShortcut | DateFilter

        probe = _Probe(completed={"last": "3d"})
        assert isinstance(probe.completed, DateFilter)
        assert probe.completed.last == "3d"
