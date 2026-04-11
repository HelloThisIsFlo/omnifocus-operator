"""Pure date filter resolution: converts input forms to absolute datetime bounds.

This module is intentionally free of I/O. The caller provides all configuration
(now timestamp, week_start, due-soon parameters). Phase 46 pipeline is responsible
for obtaining these from the database/environment.
"""

from __future__ import annotations

import re
from dataclasses import dataclass
from datetime import datetime, timedelta
from enum import StrEnum
from typing import TYPE_CHECKING

from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.contracts.use_cases.list._date_filter import (
    AbsoluteRangeFilter,
    LastPeriodFilter,
    NextPeriodFilter,
    ThisPeriodFilter,
)

if TYPE_CHECKING:
    from omnifocus_operator.models.enums import DueSoonSetting


@dataclass(frozen=True)
class ResolvedDateBounds:
    """Resolved date filter bounds, ready for the repository layer.

    Contracts:
    - Agent: inclusive-inclusive (both bounds include the boundary).
    - Repo: half-open (>= after, < before).

    Adjustments:
    - `after`: none needed (`>=` is naturally inclusive).
    - `before`: pre-bumped by the resolution step (+1 day for dates,
      +1 min for datetimes) so `< before` includes the agent's boundary.
    """

    after: datetime | None = None
    before: datetime | None = None


_DATE_DURATION_PATTERN = re.compile(r"^(\d*)([dwmy])$")


def resolve_date_filter(
    value: StrEnum | ThisPeriodFilter | LastPeriodFilter | NextPeriodFilter | AbsoluteRangeFilter,
    field_name: str,
    now: datetime,
    *,
    week_start: int = 0,
    due_soon_setting: DueSoonSetting | None = None,
) -> ResolvedDateBounds:
    """Resolve a date filter input to absolute datetime bounds.

    Args:
        value: A StrEnum shortcut or concrete filter object.
        field_name: The date field being filtered (e.g. "due", "completed").
        now: Current timestamp -- caller ensures consistency across a single query.
        week_start: Python weekday value (0=Monday, 6=Sunday). Affects {this: "w"}.
        due_soon_setting: OmniFocus due-soon threshold setting. Required when
            resolving the "soon" shortcut.

    Returns:
        ResolvedDateBounds with after/before datetimes.

    Raises:
        ValueError: If "all" shortcut is passed (not a date filter).
        AssertionError: If "soon" is passed without ``due_soon_setting``
            (domain must handle the fallback before calling this).
    """
    if isinstance(value, StrEnum):
        return _resolve_shortcut(
            value,
            field_name,
            now,
            due_soon_setting=due_soon_setting,
        )
    return _resolve_date_filter_obj(value, now, week_start=week_start)


# ---------------------------------------------------------------------------
# String shortcut resolution
# ---------------------------------------------------------------------------


def _resolve_shortcut(
    shortcut: StrEnum,
    field_name: str,
    now: datetime,
    *,
    due_soon_setting: DueSoonSetting | None,
) -> ResolvedDateBounds:
    value = shortcut.value

    if value == "today":
        after, before = _resolve_this("d", now, week_start=0)
        return ResolvedDateBounds(after=after, before=before)

    if value == "overdue":
        return ResolvedDateBounds(after=None, before=now)

    if value == "soon":
        assert due_soon_setting is not None, (
            f"'soon' on field '{field_name}' requires due_soon_setting "
            "but received None. The domain handles this fallback."
        )
        threshold = _compute_soon_threshold(
            now, due_soon_setting.days, due_soon_setting.calendar_aligned
        )
        return ResolvedDateBounds(after=None, before=threshold)

    if value == "all":
        msg = (
            f"'all' on field '{field_name}' is not a date filter — it expands "
            "availability. The pipeline handles this, not the date resolver."
        )
        raise ValueError(msg)

    msg = f"Unknown shortcut value: {value!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# DateFilter object resolution
# ---------------------------------------------------------------------------


def _resolve_date_filter_obj(
    df: ThisPeriodFilter | LastPeriodFilter | NextPeriodFilter | AbsoluteRangeFilter,
    now: datetime,
    *,
    week_start: int,
) -> ResolvedDateBounds:
    if isinstance(df, ThisPeriodFilter):
        after, before = _resolve_this(df.this, now, week_start=week_start)
        return ResolvedDateBounds(after=after, before=before)
    if isinstance(df, LastPeriodFilter):
        after, before = _resolve_last(df.last, now)
        return ResolvedDateBounds(after=after, before=before)
    if isinstance(df, NextPeriodFilter):
        after, before = _resolve_next(df.next, now)
        return ResolvedDateBounds(after=after, before=before)
    if isinstance(df, AbsoluteRangeFilter):
        after_dt, before_dt = _resolve_absolute(df, now)
        return ResolvedDateBounds(after=after_dt, before=before_dt)
    msg = f"Unknown date filter type: {type(df).__name__}"
    raise AssertionError(msg)


# ---------------------------------------------------------------------------
# {this: unit} — calendar-aligned period
# ---------------------------------------------------------------------------


def _resolve_this(
    unit: str,
    now: datetime,
    *,
    week_start: int,
) -> tuple[datetime, datetime]:
    today = _midnight(now)

    if unit == "d":
        return (today, today + timedelta(days=1))

    if unit == "w":
        days_since_start = (today.weekday() - week_start) % 7
        start = today - timedelta(days=days_since_start)
        return (start, start + timedelta(days=7))

    if unit == "m":
        start = today.replace(day=1)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return (start, end)

    if unit == "y":
        start = today.replace(month=1, day=1)
        end = start.replace(year=start.year + 1)
        return (start, end)

    msg = f"Unknown 'this' unit: {unit!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# {last: duration} — rolling past period
# ---------------------------------------------------------------------------


def _resolve_last(duration: str, now: datetime) -> tuple[datetime, datetime]:
    count, unit = _parse_duration(duration)
    delta = _duration_to_timedelta(count, unit)
    start = _midnight(now - delta)
    return (start, now)


# ---------------------------------------------------------------------------
# {next: duration} — rolling future period
# ---------------------------------------------------------------------------


def _resolve_next(duration: str, now: datetime) -> tuple[datetime, datetime]:
    count, unit = _parse_duration(duration)
    delta = _duration_to_timedelta(count, unit)
    # "rest of today + N full periods": midnight(now) + delta + 1 day
    end = _midnight(now) + delta + timedelta(days=1)
    return (now, end)


# ---------------------------------------------------------------------------
# Absolute {before/after}
# ---------------------------------------------------------------------------


def _resolve_absolute(
    df: AbsoluteRangeFilter,
    now: datetime,
) -> tuple[datetime | None, datetime | None]:
    after, before = df.after, df.before
    after_dt = _parse_absolute_after(after, now) if is_set(after) else None
    before_dt = _parse_absolute_before(before, now) if is_set(before) else None
    return (after_dt, before_dt)


def _parse_absolute_after(
    value: str,
    now: datetime,
) -> datetime:
    """Parse 'after' bound: date-only -> start of that day (RESOLVE-09).

    After Phase 49, values arrive as str (validated ISO date or datetime).
    """
    if value == "now":
        return now

    dt = datetime.fromisoformat(value)

    # Date-only string: no 'T' means just a date -> start of that day
    if "T" not in value and "t" not in value:
        return datetime(dt.year, dt.month, dt.day, tzinfo=now.tzinfo)

    # Datetime string: if naive, inherit now's tzinfo (local by contract)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=now.tzinfo)

    # Aware: use as-is (agent specified explicit timezone)
    return dt


def _parse_absolute_before(
    value: str,
    now: datetime,
) -> datetime:
    """Parse 'before' bound: date-only -> start of NEXT day (RESOLVE-08).

    After Phase 49, values arrive as str (validated ISO date or datetime).
    """
    if value == "now":
        return now

    dt = datetime.fromisoformat(value)

    # Date-only string: no 'T' means just a date -> start of next day (inclusive end)
    if "T" not in value and "t" not in value:
        return datetime(dt.year, dt.month, dt.day, tzinfo=now.tzinfo) + timedelta(days=1)

    # Datetime string: if naive, inherit now's tzinfo (local by contract)
    if dt.tzinfo is None:
        return dt.replace(tzinfo=now.tzinfo)

    # Aware: use as-is
    return dt


# ---------------------------------------------------------------------------
# "soon" threshold computation
# ---------------------------------------------------------------------------


def _compute_soon_threshold(
    now: datetime,
    days: int,
    calendar_aligned: bool,
) -> datetime:
    """Compute the "due soon" threshold from domain properties.

    Args:
        now: Current timestamp.
        days: Number of days in the threshold window.
        calendar_aligned: If True, snap to midnight (start of day). If False,
            use rolling N*24h from now.
    """
    if not calendar_aligned:
        # Rolling: now + days * 24h
        return now + timedelta(days=days)
    # Calendar-aligned: midnight_today + days
    return _midnight(now) + timedelta(days=days)


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _midnight(dt: datetime) -> datetime:
    """Truncate to midnight (start of day)."""
    return dt.replace(hour=0, minute=0, second=0, microsecond=0)


def _parse_duration(value: str) -> tuple[int, str]:
    """Parse "[N]unit" -> (count, unit). Count defaults to 1."""
    match = _DATE_DURATION_PATTERN.match(value)
    if not match:
        msg = f"Invalid duration format: {value!r}"
        raise ValueError(msg)
    count_str = match.group(1)
    count = int(count_str) if count_str else 1
    unit = match.group(2)
    return (count, unit)


def _duration_to_timedelta(count: int, unit: str) -> timedelta:
    """Convert (count, unit) to timedelta. Uses naive 30d/365d for m/y."""
    if unit == "d":
        return timedelta(days=count)
    if unit == "w":
        return timedelta(weeks=count)
    if unit == "m":
        return timedelta(days=count * 30)
    if unit == "y":
        return timedelta(days=count * 365)
    msg = f"Unknown duration unit: {unit!r}"
    raise ValueError(msg)
