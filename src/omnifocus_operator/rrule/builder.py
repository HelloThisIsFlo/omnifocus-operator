"""RRULE builder for OmniFocus repetition rules.

Inverse of the parser: takes a Frequency model instance and produces
an RRULE string.

Public function:
    build_rrule(frequency, end=None) -> str
"""

from __future__ import annotations

from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    EndByOccurrences,
    Frequency,
    MonthlyDayInMonthFrequency,
    MonthlyDayOfWeekFrequency,
    WeeklyOnDaysFrequency,
)
from omnifocus_operator.rrule.parser import parse_rrule

# ── Reverse Mapping Tables ───────────────────────────────────────────────

_ORDINAL_TO_POS: dict[str, int] = {
    "first": 1,
    "second": 2,
    "third": 3,
    "fourth": 4,
    "fifth": 5,
    "last": -1,
}

_NAME_TO_DAY_CODE: dict[str, str] = {
    "monday": "MO",
    "tuesday": "TU",
    "wednesday": "WE",
    "thursday": "TH",
    "friday": "FR",
    "saturday": "SA",
    "sunday": "SU",
}

_TYPE_TO_FREQ: dict[str, str] = {
    "minutely": "MINUTELY",
    "hourly": "HOURLY",
    "daily": "DAILY",
    "weekly": "WEEKLY",
    "weekly_on_days": "WEEKLY",
    "monthly": "MONTHLY",
    "monthly_day_of_week": "MONTHLY",
    "monthly_day_in_month": "MONTHLY",
    "yearly": "YEARLY",
}


# ── Public API ───────────────────────────────────────────────────────────


def build_rrule(
    frequency: Frequency,
    end: EndByDate | EndByOccurrences | None = None,
) -> str:
    """Build an RRULE string from a Frequency model and optional end condition.

    Includes round-trip validation: parse_rrule(result) must succeed.

    Args:
        frequency: Frequency model instance (any of the 9 subtypes)
        end: Optional EndByDate or EndByOccurrences model

    Returns:
        RRULE string (e.g., "FREQ=DAILY;INTERVAL=3")

    Raises:
        ValueError: On invalid input or failed round-trip validation
    """
    freq_type = frequency.type
    freq_code = _TYPE_TO_FREQ.get(freq_type)
    if freq_code is None:
        raise ValueError(f"Unknown frequency type: {freq_type!r}")

    parts: list[str] = [f"FREQ={freq_code}"]

    # Interval (omit when 1)
    if frequency.interval != 1:
        parts.append(f"INTERVAL={frequency.interval}")

    # Type-specific parts
    if isinstance(frequency, WeeklyOnDaysFrequency):
        parts.append(f"BYDAY={','.join(frequency.on_days)}")
    elif isinstance(frequency, MonthlyDayOfWeekFrequency) and frequency.on:
        parts.append(_build_byday_positional(frequency.on))
    elif isinstance(frequency, MonthlyDayInMonthFrequency) and frequency.on_dates:
        parts.append(f"BYMONTHDAY={frequency.on_dates[0]}")

    # End condition
    if isinstance(end, EndByOccurrences):
        parts.append(f"COUNT={end.occurrences}")
    elif isinstance(end, EndByDate):
        parts.append(f"UNTIL={_convert_iso_to_until(end.date)}")

    result = ";".join(parts)

    # Round-trip validation: ensure the built string parses correctly
    parse_rrule(result)

    return result


# ── Internal Helpers ─────────────────────────────────────────────────────


def _build_byday_positional(on: dict[str, str]) -> str:
    """Build BYDAY=NXX from {ordinal: day_name} dict."""
    if len(on) != 1:
        raise ValueError(f"'on' dict must have exactly one key, got {len(on)}")
    ordinal, day_name = next(iter(on.items()))
    pos = _ORDINAL_TO_POS.get(ordinal)
    if pos is None:
        raise ValueError(f"Unknown ordinal: {ordinal!r}. Valid: {sorted(_ORDINAL_TO_POS.keys())}")
    day_code = _NAME_TO_DAY_CODE.get(day_name)
    if day_code is None:
        raise ValueError(
            f"Unknown day name: {day_name!r}. Valid: {sorted(_NAME_TO_DAY_CODE.keys())}"
        )
    return f"BYDAY={pos}{day_code}"


def _convert_iso_to_until(iso_date: str) -> str:
    """Convert ISO-8601 date to RRULE compact UNTIL format.

    Input:  YYYY-MM-DDTHH:MM:SSZ (e.g., 2026-12-31T00:00:00Z)
    Output: YYYYMMDDTHHMMSSZ (e.g., 20261231T000000Z)
    """
    # Strip dashes, colons; keep T and Z
    return iso_date.replace("-", "").replace(":", "")
