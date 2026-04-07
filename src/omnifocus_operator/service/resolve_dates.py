"""Pure date filter resolution: converts input forms to absolute datetime bounds.

This module is intentionally free of I/O. The caller provides all configuration
(now timestamp, week_start, due-soon parameters). Phase 46 pipeline is responsible
for obtaining these from the database/environment.
"""

from __future__ import annotations

import re
from datetime import date, datetime, timedelta
from enum import StrEnum

from omnifocus_operator.contracts.use_cases.list._date_filter import DateFilter

_DATE_DURATION_PATTERN = re.compile(r"^(\d*)([dwmy])$")


def resolve_date_filter(
    value: StrEnum | DateFilter,
    field_name: str,
    now: datetime,
    *,
    week_start: int = 0,
    due_soon_interval: int | None = None,
    due_soon_granularity: int | None = None,
) -> tuple[datetime | None, datetime | None]:
    """Resolve a date filter input to (after_bound, before_bound) datetimes.

    A None in either position means "unbounded on that side".

    Args:
        value: A StrEnum shortcut or DateFilter object.
        field_name: The date field being filtered (e.g. "due", "completed").
        now: Current timestamp — caller ensures consistency across a single query.
        week_start: Python weekday value (0=Monday, 6=Sunday). Affects {this: "w"}.
        due_soon_interval: Threshold in seconds from OmniFocus Settings table.
        due_soon_granularity: 0=rolling from now, 1=calendar-aligned (snap to midnight).

    Returns:
        (after_bound, before_bound) tuple of datetime or None.

    Raises:
        ValueError: If "soon" is requested without both due_soon config params,
                    or if "any" shortcut is passed (not a date filter).
    """
    if isinstance(value, StrEnum):
        return _resolve_shortcut(
            value,
            field_name,
            now,
            due_soon_interval=due_soon_interval,
            due_soon_granularity=due_soon_granularity,
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
    due_soon_interval: int | None,
    due_soon_granularity: int | None,
) -> tuple[datetime | None, datetime | None]:
    value = shortcut.value

    if value == "today":
        return _resolve_this("d", now, week_start=0)

    if value == "overdue":
        return (None, now)

    if value == "soon":
        if due_soon_interval is None or due_soon_granularity is None:
            msg = (
                "Cannot resolve 'soon' without both due_soon_interval and "
                "due_soon_granularity configuration. The caller must provide "
                "these from the OmniFocus Settings table or environment."
            )
            raise ValueError(msg)
        threshold = _compute_soon_threshold(now, due_soon_interval, due_soon_granularity)
        return (None, threshold)

    if value == "any":
        msg = (
            f"'any' on field '{field_name}' is not a date filter — it expands "
            "availability. The pipeline handles this, not the date resolver."
        )
        raise ValueError(msg)

    msg = f"Unknown shortcut value: {value!r}"
    raise ValueError(msg)


# ---------------------------------------------------------------------------
# DateFilter object resolution
# ---------------------------------------------------------------------------


def _resolve_date_filter_obj(
    df: DateFilter,
    now: datetime,
    *,
    week_start: int,
) -> tuple[datetime | None, datetime | None]:
    if df.this is not None:
        return _resolve_this(df.this, now, week_start=week_start)
    if df.last is not None:
        return _resolve_last(df.last, now)
    if df.next is not None:
        return _resolve_next(df.next, now)
    # Absolute: before/after
    return _resolve_absolute(df, now)


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
    df: DateFilter,
    now: datetime,
) -> tuple[datetime | None, datetime | None]:
    after_dt = _parse_absolute_after(df.after, now) if df.after else None
    before_dt = _parse_absolute_before(df.before, now) if df.before else None
    return (after_dt, before_dt)


def _parse_absolute_after(value: str, now: datetime) -> datetime:
    """Parse 'after' value: date-only -> start of that day (RESOLVE-09)."""
    if value == "now":
        return now
    if _is_date_only(value):
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day)
    return datetime.fromisoformat(value)


def _parse_absolute_before(value: str, now: datetime) -> datetime:
    """Parse 'before' value: date-only -> start of NEXT day (RESOLVE-08)."""
    if value == "now":
        return now
    if _is_date_only(value):
        d = date.fromisoformat(value)
        return datetime(d.year, d.month, d.day) + timedelta(days=1)
    return datetime.fromisoformat(value)


def _is_date_only(value: str) -> bool:
    """Check if a string is date-only (YYYY-MM-DD) vs datetime (contains T or time)."""
    return "T" not in value and len(value) == 10


# ---------------------------------------------------------------------------
# "soon" threshold computation
# ---------------------------------------------------------------------------


def _compute_soon_threshold(
    now: datetime,
    interval: int,
    granularity: int,
) -> datetime:
    if granularity == 0:
        # Rolling: now + interval seconds
        return now + timedelta(seconds=interval)
    # Calendar-aligned: midnight_today + interval seconds
    return _midnight(now) + timedelta(seconds=interval)


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
