"""Tests for DateFilter contract model, date shortcut StrEnums, and query date fields."""

import re
from datetime import datetime
from typing import ClassVar

import pytest
from pydantic import BaseModel, TypeAdapter, ValidationError

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.config import get_week_start
from omnifocus_operator.contracts.use_cases.list import (
    AbsoluteRangeFilter,
    DateFilter,
    DateShortcut,
    DueDateShortcut,
    LastPeriodFilter,
    LifecycleDateShortcut,
    ListTasksQuery,
    ListTasksRepoQuery,
    NextPeriodFilter,
    ThisPeriodFilter,
)
from omnifocus_operator.contracts.use_cases.list._date_filter import (
    DateInput,
    DueDateInput,
    LifecycleDateInput,
    _make_date_input_validator,
)

_ta = TypeAdapter(DateFilter)

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
    def test_all(self) -> None:
        assert LifecycleDateShortcut("all") == LifecycleDateShortcut.ALL

    def test_today(self) -> None:
        assert LifecycleDateShortcut("today") == LifecycleDateShortcut.TODAY

    def test_invalid_value_raises(self) -> None:
        with pytest.raises(ValueError):
            LifecycleDateShortcut("invalid")

    def test_any_is_invalid(self) -> None:
        """'any' is no longer a valid shortcut -- renamed to 'all'."""
        with pytest.raises(ValueError):
            LifecycleDateShortcut("any")


# ---------------------------------------------------------------------------
# DateFilter: Valid shorthand (DATE-02, DATE-03)
# ---------------------------------------------------------------------------


class TestDateFilterValidShorthand:
    def test_this_day(self) -> None:
        f = ThisPeriodFilter(this="d")
        assert f.this == "d"

    def test_last_3d(self) -> None:
        f = LastPeriodFilter(last="3d")
        assert f.last == "3d"

    def test_next_week(self) -> None:
        f = NextPeriodFilter(next="w")
        assert f.next == "w"

    def test_last_2m(self) -> None:
        f = LastPeriodFilter(last="2m")
        assert f.last == "2m"

    def test_next_1y(self) -> None:
        f = NextPeriodFilter(next="1y")
        assert f.next == "1y"

    def test_count_defaults_to_1(self) -> None:
        """'w' is valid shorthand for last/next (same as '1w')."""
        f = LastPeriodFilter(last="w")
        assert f.last == "w"


# ---------------------------------------------------------------------------
# DateFilter: Valid absolute (DATE-02)
# ---------------------------------------------------------------------------


class TestDateFilterValidAbsolute:
    def test_before_date_only(self) -> None:
        f = AbsoluteRangeFilter(before="2026-04-14")
        assert f.before == "2026-04-14"

    def test_after_date_only(self) -> None:
        f = AbsoluteRangeFilter(after="2026-04-01")
        assert f.after == "2026-04-01"

    def test_before_now(self) -> None:
        f = AbsoluteRangeFilter(before="now")
        assert f.before == "now"

    def test_after_now(self) -> None:
        f = AbsoluteRangeFilter(after="now")
        assert f.after == "now"

    def test_both_absolute_with_aware_datetime(self) -> None:
        f = AbsoluteRangeFilter(after="2026-04-01T14:00:00Z", before="2026-04-14")
        assert f.after == "2026-04-01T14:00:00Z"
        assert f.before == "2026-04-14"

    def test_both_absolute_with_naive_datetime(self) -> None:
        """Naive datetime is now accepted (no timezone required)."""
        f = AbsoluteRangeFilter(after="2026-04-01T14:00:00", before="2026-04-14T18:00:00")
        assert f.after == "2026-04-01T14:00:00"
        assert f.before == "2026-04-14T18:00:00"

    def test_both_now_valid(self) -> None:
        """Both bounds as 'now' is valid (no ordering check needed)."""
        f = AbsoluteRangeFilter(after="now", before="now")
        assert f.after == "now"
        assert f.before == "now"


# ---------------------------------------------------------------------------
# DateFilter: Discriminator routing / mutual exclusion (DATE-04)
# ---------------------------------------------------------------------------


class TestDateFilterMutualExclusion:
    """With the union, mixed keys route to the first-matched branch which
    rejects the extra key via extra='forbid'."""

    def test_mixed_this_and_before_rejected(self) -> None:
        """Discriminator sees 'this', routes to ThisPeriodFilter which rejects 'before'."""
        with pytest.raises(ValidationError):
            _ta.validate_python({"this": "d", "before": "2026-04-14"})

    def test_mixed_last_and_after_rejected(self) -> None:
        """Discriminator sees 'last', routes to LastPeriodFilter which rejects 'after'."""
        with pytest.raises(ValidationError):
            _ta.validate_python({"last": "3d", "after": "2026-04-01"})

    def test_mixed_this_and_last_rejected(self) -> None:
        """Discriminator sees 'this' first, routes to ThisPeriodFilter which rejects 'last'."""
        with pytest.raises(ValidationError):
            _ta.validate_python({"this": "d", "last": "3d"})

    def test_all_three_shorthand_rejected(self) -> None:
        """Discriminator sees 'this' first, ThisPeriodFilter rejects 'last' and 'next'."""
        with pytest.raises(ValidationError):
            _ta.validate_python({"this": "d", "last": "3d", "next": "w"})


# ---------------------------------------------------------------------------
# DateFilter: Empty filter
# ---------------------------------------------------------------------------


class TestDateFilterEmpty:
    def test_empty_filter_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Date range filter requires at least one"):
            _ta.validate_python({})


# ---------------------------------------------------------------------------
# DateFilter: Null rejection on absolute bounds (Patch/UNSET)
# ---------------------------------------------------------------------------


class TestAbsoluteRangeNullRejection:
    """Null is not a valid value for before/after — omit the field instead."""

    def test_before_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AbsoluteRangeFilter(after="2026-04-01", before=None)

    def test_after_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AbsoluteRangeFilter(before="2026-04-14", after=None)

    def test_both_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            AbsoluteRangeFilter(before=None, after=None)


# ---------------------------------------------------------------------------
# DateFilter: One-sided absolute filters (Patch/UNSET)
# ---------------------------------------------------------------------------


class TestAbsoluteRangeOneSided:
    """Omitting one bound (UNSET) is valid — only the provided bound applies."""

    def test_before_only(self) -> None:
        f = AbsoluteRangeFilter(before="2024-01-01T00:00:00Z")
        assert f.before == "2024-01-01T00:00:00Z"

    def test_after_only(self) -> None:
        f = AbsoluteRangeFilter(after="now")
        assert f.after == "now"


# ---------------------------------------------------------------------------
# DateFilter: Duration validation (DATE-05)
# ---------------------------------------------------------------------------


class TestDateFilterDuration:
    def test_zero_count_rejected(self) -> None:
        with pytest.raises(ValidationError, match="must be positive"):
            LastPeriodFilter(last="0d")

    def test_invalid_unit_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Invalid duration"):
            LastPeriodFilter(last="3x")

    def test_negative_count_rejected(self) -> None:
        """Regex doesn't match negative, so it falls through to 'Invalid duration'."""
        with pytest.raises(ValidationError, match="Invalid duration"):
            NextPeriodFilter(next="-1d")

    def test_this_only_accepts_literal_units(self) -> None:
        """'this' uses Literal["d","w","m","y"] -- '3d' is rejected by Pydantic."""
        with pytest.raises(ValidationError):
            ThisPeriodFilter(this="3d")

    def test_this_valid_units(self) -> None:
        for unit in ("d", "w", "m", "y"):
            f = ThisPeriodFilter(this=unit)
            assert f.this == unit


# ---------------------------------------------------------------------------
# DateFilter: Absolute validation
# ---------------------------------------------------------------------------


class TestDateFilterAbsolute:
    def test_invalid_date_rejected(self) -> None:
        """'not-a-date' is rejected -- not a valid ISO date/datetime or 'now'."""
        with pytest.raises(ValidationError):
            AbsoluteRangeFilter(before="not-a-date")

    def test_aware_datetime_accepted(self) -> None:
        f = AbsoluteRangeFilter(after="2026-04-01T14:00:00Z")
        assert f.after == "2026-04-01T14:00:00Z"

    def test_naive_datetime_accepted_before(self) -> None:
        """Naive datetime is now accepted (naive-local principle)."""
        f = AbsoluteRangeFilter(before="2026-04-01T14:00:00")
        assert f.before == "2026-04-01T14:00:00"

    def test_naive_datetime_accepted_after(self) -> None:
        """Naive datetime is now accepted (naive-local principle)."""
        f = AbsoluteRangeFilter(after="2026-04-01T14:00:00")
        assert f.after == "2026-04-01T14:00:00"

    def test_date_only_accepted(self) -> None:
        """Date-only string is accepted."""
        f = AbsoluteRangeFilter(after="2026-04-01")
        assert f.after == "2026-04-01"


# ---------------------------------------------------------------------------
# DateFilter: Reversed bounds (DATE-09)
# ---------------------------------------------------------------------------


class TestDateFilterReversedBounds:
    def test_reversed_bounds_rejected(self) -> None:
        with pytest.raises(ValidationError, match="later than"):
            AbsoluteRangeFilter(after="2026-04-14", before="2026-04-01")

    def test_equal_date_only_bounds_valid(self) -> None:
        """Equal date-only bounds are valid (matches single day per DATE-09)."""
        f = AbsoluteRangeFilter(after="2026-04-14", before="2026-04-14")
        assert f.after == "2026-04-14"
        assert f.before == "2026-04-14"

    def test_reversed_datetime_bounds_rejected(self) -> None:
        with pytest.raises(ValidationError, match="later than"):
            AbsoluteRangeFilter(after="2026-04-14T12:00:00Z", before="2026-04-01T08:00:00Z")

    def test_reversed_naive_datetime_bounds_rejected(self) -> None:
        """Naive datetime bounds are also checked for ordering."""
        with pytest.raises(ValidationError, match="later than"):
            AbsoluteRangeFilter(after="2026-04-14T12:00:00", before="2026-04-01T08:00:00")


# ---------------------------------------------------------------------------
# DateFilter: Typed bound parsing
# ---------------------------------------------------------------------------


class TestDateFilterStringBounds:
    """Verify before/after are stored as validated strings (naive-local principle)."""

    def test_date_only_stored_as_string(self) -> None:
        f = AbsoluteRangeFilter(before="2026-04-14")
        assert isinstance(f.before, str)
        assert f.before == "2026-04-14"

    def test_aware_datetime_stored_as_string(self) -> None:
        f = AbsoluteRangeFilter(before="2026-04-14T14:00:00Z")
        assert isinstance(f.before, str)
        assert f.before == "2026-04-14T14:00:00Z"

    def test_naive_datetime_stored_as_string(self) -> None:
        f = AbsoluteRangeFilter(before="2026-04-14T14:00:00")
        assert isinstance(f.before, str)
        assert f.before == "2026-04-14T14:00:00"

    def test_now_literal_accepted(self) -> None:
        f = AbsoluteRangeFilter(before="now")
        assert f.before == "now"

    def test_offset_timezone_accepted(self) -> None:
        f = AbsoluteRangeFilter(after="2026-04-01T14:00:00+02:00")
        assert isinstance(f.after, str)
        assert f.after == "2026-04-01T14:00:00+02:00"


# ---------------------------------------------------------------------------
# DateFilter: Discriminator non-dict input
# ---------------------------------------------------------------------------


class TestDateFilterNonDictInput:
    """Non-dict input routes to AbsoluteRangeFilter for Pydantic rejection."""

    def test_integer_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _ta.validate_python(42)

    def test_string_rejected(self) -> None:
        with pytest.raises(ValidationError):
            _ta.validate_python("invalid")


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

    def test_dict_becomes_this_period_filter(self) -> None:
        class _Probe(BaseModel):
            due: DueDateShortcut | DateFilter

        probe = _Probe(due={"this": "d"})
        assert isinstance(probe.due, ThisPeriodFilter)
        assert probe.due.this == "d"

    def test_lifecycle_string_becomes_shortcut(self) -> None:
        class _Probe(BaseModel):
            completed: LifecycleDateShortcut | DateFilter

        probe = _Probe(completed="all")
        assert isinstance(probe.completed, LifecycleDateShortcut)
        assert probe.completed == LifecycleDateShortcut.ALL

    def test_lifecycle_dict_becomes_last_period_filter(self) -> None:
        class _Probe(BaseModel):
            completed: LifecycleDateShortcut | DateFilter

        probe = _Probe(completed={"last": "3d"})
        assert isinstance(probe.completed, LastPeriodFilter)
        assert probe.completed.last == "3d"


# ---------------------------------------------------------------------------
# ListTasksQuery: Date filter fields (Plan 02)
# ---------------------------------------------------------------------------


class TestListTasksQueryDateFields:
    """Verify ListTasksQuery accepts date filter fields with correct union types."""

    def test_due_overdue_shortcut(self) -> None:
        q = ListTasksQuery(due="overdue")
        assert isinstance(q.due, DueDateShortcut)
        assert q.due == DueDateShortcut.OVERDUE

    def test_due_soon_shortcut(self) -> None:
        q = ListTasksQuery(due="soon")
        assert isinstance(q.due, DueDateShortcut)
        assert q.due == DueDateShortcut.SOON

    def test_due_today_shortcut(self) -> None:
        q = ListTasksQuery(due="today")
        assert isinstance(q.due, DueDateShortcut)
        assert q.due == DueDateShortcut.TODAY

    def test_due_date_filter_object(self) -> None:
        q = ListTasksQuery(due={"this": "w"})
        assert isinstance(q.due, ThisPeriodFilter)
        assert q.due.this == "w"

    def test_completed_all_shortcut(self) -> None:
        q = ListTasksQuery(completed="all")
        assert isinstance(q.completed, LifecycleDateShortcut)
        assert q.completed == LifecycleDateShortcut.ALL

    def test_defer_today_shortcut(self) -> None:
        q = ListTasksQuery(defer="today")
        assert isinstance(q.defer, DateShortcut)
        assert q.defer == DateShortcut.TODAY
        assert q.defer == "today"

    def test_planned_today_shortcut(self) -> None:
        q = ListTasksQuery(planned="today")
        assert isinstance(q.planned, DateShortcut)
        assert q.planned == DateShortcut.TODAY
        assert q.planned == "today"

    def test_added_today_shortcut(self) -> None:
        q = ListTasksQuery(added="today")
        assert isinstance(q.added, DateShortcut)
        assert q.added == DateShortcut.TODAY
        assert q.added == "today"

    def test_modified_today_shortcut(self) -> None:
        q = ListTasksQuery(modified="today")
        assert isinstance(q.modified, DateShortcut)
        assert q.modified == DateShortcut.TODAY
        assert q.modified == "today"

    def test_defer_date_filter_object(self) -> None:
        q = ListTasksQuery(defer={"this": "w"})
        assert isinstance(q.defer, ThisPeriodFilter)
        assert q.defer.this == "w"

    def test_planned_date_filter_object(self) -> None:
        q = ListTasksQuery(planned={"last": "3d"})
        assert isinstance(q.planned, LastPeriodFilter)
        assert q.planned.last == "3d"

    def test_added_date_filter_object(self) -> None:
        q = ListTasksQuery(added={"next": "m"})
        assert isinstance(q.added, NextPeriodFilter)
        assert q.added.next == "m"

    def test_modified_date_filter_object(self) -> None:
        q = ListTasksQuery(modified={"before": "2026-04-14"})
        assert isinstance(q.modified, AbsoluteRangeFilter)
        assert q.modified.before == "2026-04-14"

    def test_dropped_all_shortcut(self) -> None:
        q = ListTasksQuery(dropped="all")
        assert isinstance(q.dropped, LifecycleDateShortcut)
        assert q.dropped == LifecycleDateShortcut.ALL


class TestListTasksQueryDateFieldRejection:
    """Verify invalid shortcuts are rejected on the correct fields."""

    def test_due_all_rejected(self) -> None:
        """'all' is not valid for due -- only for lifecycle fields."""
        with pytest.raises(ValidationError):
            ListTasksQuery(due="all")

    def test_defer_overdue_rejected(self) -> None:
        """'overdue' is not valid for defer -- only for due."""
        with pytest.raises(ValidationError):
            ListTasksQuery(defer="overdue")

    def test_due_null_rejected(self) -> None:
        """Null rejection covers date fields."""
        with pytest.raises(ValidationError):
            ListTasksQuery(due=None)

    def test_defer_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ListTasksQuery(defer=None)

    def test_completed_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ListTasksQuery(completed=None)

    def test_dropped_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ListTasksQuery(dropped=None)

    def test_planned_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ListTasksQuery(planned=None)

    def test_added_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ListTasksQuery(added=None)

    def test_modified_null_rejected(self) -> None:
        with pytest.raises(ValidationError):
            ListTasksQuery(modified=None)


# ---------------------------------------------------------------------------
# ListTasksRepoQuery: Resolved datetime fields (Plan 02)
# ---------------------------------------------------------------------------


class TestListTasksRepoQueryDatetimeFields:
    """Verify ListTasksRepoQuery has 14 _after/_before datetime fields."""

    _DATE_FIELD_PAIRS: ClassVar[list[tuple[str, str]]] = [
        ("due_after", "due_before"),
        ("defer_after", "defer_before"),
        ("planned_after", "planned_before"),
        ("completed_after", "completed_before"),
        ("dropped_after", "dropped_before"),
        ("added_after", "added_before"),
        ("modified_after", "modified_before"),
    ]

    def test_all_14_fields_exist_and_default_none(self) -> None:
        q = ListTasksRepoQuery()
        for after_field, before_field in self._DATE_FIELD_PAIRS:
            assert getattr(q, after_field) is None, f"{after_field} should default to None"
            assert getattr(q, before_field) is None, f"{before_field} should default to None"

    def test_datetime_values_accepted(self) -> None:
        dt = datetime(2026, 4, 7, 12, 0, 0)
        q = ListTasksRepoQuery(due_after=dt, due_before=dt)
        assert q.due_after == dt
        assert q.due_before == dt


# ---------------------------------------------------------------------------
# OPERATOR_WEEK_START config (Plan 02)
# ---------------------------------------------------------------------------


class TestGetWeekStart:
    """Verify get_week_start() reads OPERATOR_WEEK_START env var."""

    def test_default_is_monday(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.delenv("OPERATOR_WEEK_START", raising=False)
        assert get_week_start() == 0

    def test_sunday_returns_6(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_WEEK_START", "sunday")
        assert get_week_start() == 6

    def test_monday_returns_0(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_WEEK_START", "monday")
        assert get_week_start() == 0

    def test_case_insensitive(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_WEEK_START", "SUNDAY")
        assert get_week_start() == 6

    def test_invalid_value_raises(self, monkeypatch: pytest.MonkeyPatch) -> None:
        monkeypatch.setenv("OPERATOR_WEEK_START", "wednesday")
        with pytest.raises(ValueError, match="Invalid OPERATOR_WEEK_START"):
            get_week_start()


# ---------------------------------------------------------------------------
# Date input type-rejection validators
# ---------------------------------------------------------------------------

_lifecycle_ta = TypeAdapter(LifecycleDateInput)
_due_ta = TypeAdapter(DueDateInput)
_date_ta = TypeAdapter(DateInput)


class TestMakeDateInputValidator:
    """Unit tests for the _make_date_input_validator factory."""

    def test_passes_string_through(self) -> None:
        validate = _make_date_input_validator("all", "today")
        assert validate("today") == "today"

    def test_passes_dict_through(self) -> None:
        validate = _make_date_input_validator("all", "today")
        d = {"this": "d"}
        assert validate(d) is d

    def test_rejects_bool_with_shortcuts_in_message(self) -> None:
        validate = _make_date_input_validator("all", "today")
        with pytest.raises(ValueError, match="'all', 'today'"):
            validate(True)

    def test_rejects_int(self) -> None:
        validate = _make_date_input_validator("today")
        with pytest.raises(ValueError, match="date filter"):
            validate(42)

    def test_rejects_list(self) -> None:
        validate = _make_date_input_validator("overdue", "soon", "today")
        with pytest.raises(ValueError, match="'overdue', 'soon', 'today'"):
            validate([1, 2])

    def test_message_uses_error_constant(self) -> None:
        validate = _make_date_input_validator("all", "today")
        expected = err.DATE_INPUT_INVALID_TYPE.format(shortcuts="'all', 'today'")
        with pytest.raises(ValueError, match=re.escape(expected)):
            validate(True)


class TestLifecycleDateInput:
    """LifecycleDateInput accepts 'all'/'today', DateFilter objects, rejects invalid types."""

    def test_accepts_shortcut_string(self) -> None:
        result = _lifecycle_ta.validate_python("all")
        assert result == LifecycleDateShortcut.ALL

    def test_accepts_date_filter_dict(self) -> None:
        result = _lifecycle_ta.validate_python({"this": "d"})
        assert isinstance(result, ThisPeriodFilter)

    def test_rejects_bool(self) -> None:
        with pytest.raises(ValidationError, match="'all', 'today'"):
            _lifecycle_ta.validate_python(True)

    def test_rejects_int(self) -> None:
        with pytest.raises(ValidationError, match="date filter"):
            _lifecycle_ta.validate_python(99)


class TestDueDateInput:
    """DueDateInput accepts 'overdue'/'soon'/'today', DateFilter objects, rejects invalid types."""

    def test_accepts_shortcut_string(self) -> None:
        result = _due_ta.validate_python("soon")
        assert result == DueDateShortcut.SOON

    def test_accepts_date_filter_dict(self) -> None:
        result = _due_ta.validate_python({"last": "3d"})
        assert isinstance(result, LastPeriodFilter)

    def test_rejects_bool(self) -> None:
        with pytest.raises(ValidationError, match="'overdue', 'soon', 'today'"):
            _due_ta.validate_python(True)


class TestDateInput:
    """DateInput accepts 'today', DateFilter objects, rejects invalid types."""

    def test_accepts_shortcut_string(self) -> None:
        result = _date_ta.validate_python("today")
        assert result == DateShortcut.TODAY

    def test_accepts_date_filter_dict(self) -> None:
        result = _date_ta.validate_python({"next": "2w"})
        assert isinstance(result, NextPeriodFilter)

    def test_rejects_bool(self) -> None:
        with pytest.raises(ValidationError, match="'today'"):
            _date_ta.validate_python(True)
