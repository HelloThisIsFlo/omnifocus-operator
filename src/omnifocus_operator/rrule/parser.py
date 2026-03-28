"""RRULE parser for OmniFocus repetition rule strings.

Parses the OmniFocus RRULE subset into Pydantic model instances matching
the Frequency union type. Supports all 8 frequency types including
MINUTELY, HOURLY, and BYDAY positional prefix parsing.

Public functions:
    parse_rrule(rule_string) -> Frequency model instance
    parse_end_condition(rule_string) -> EndByDate | EndByOccurrences | None
"""

from __future__ import annotations

import re

from omnifocus_operator.models.repetition_rule import (
    DailyFrequency,
    EndByDate,
    EndByOccurrences,
    Frequency,
    HourlyFrequency,
    MinutelyFrequency,
    MonthlyDayInMonthFrequency,
    MonthlyDayOfWeekFrequency,
    MonthlyFrequency,
    WeeklyFrequency,
    YearlyFrequency,
)

# ── Mapping Tables ───────────────────────────────────────────────────────

_BYDAY_PATTERN = re.compile(r"^(-?\d+)?(MO|TU|WE|TH|FR|SA|SU)$")
_UNTIL_PATTERN = re.compile(r"^(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})(\d{2})Z$")

_POS_TO_ORDINAL: dict[int, str] = {
    1: "first",
    2: "second",
    3: "third",
    4: "fourth",
    5: "fifth",
    -1: "last",
}

_DAY_CODE_TO_NAME: dict[str, str] = {
    "MO": "monday",
    "TU": "tuesday",
    "WE": "wednesday",
    "TH": "thursday",
    "FR": "friday",
    "SA": "saturday",
    "SU": "sunday",
}

_VALID_FREQS = {
    "MINUTELY",
    "HOURLY",
    "DAILY",
    "WEEKLY",
    "MONTHLY",
    "YEARLY",
}


# ── Public API ───────────────────────────────────────────────────────────


def parse_rrule(rule_string: str) -> Frequency:
    """Parse an RRULE string into a Frequency model instance.

    Returns a Pydantic model matching one of the 8 frequency subtypes.
    Raises ValueError with an educational message on invalid input.

    Examples:
        >>> parse_rrule("FREQ=DAILY")
        DailyFrequency(interval=1)
        >>> parse_rrule("FREQ=WEEKLY;BYDAY=MO,WE,FR")
        WeeklyFrequency(interval=1, on_days=["MO", "WE", "FR"])
    """
    if not rule_string or not rule_string.strip():
        raise ValueError("RRULE string must not be empty")

    parts = _parse_parts(rule_string)
    _validate_no_bysetpos(parts, rule_string)
    _validate_end_exclusion(parts)

    freq = parts.get("FREQ", "").upper()
    if freq not in _VALID_FREQS:
        if not freq:
            raise ValueError(f"FREQ is required in RRULE string: {rule_string!r}")
        raise ValueError(f"Unsupported FREQ: {freq!r}. Valid values: {sorted(_VALID_FREQS)}")

    interval = int(parts.get("INTERVAL", "1"))

    if freq == "MINUTELY":
        return MinutelyFrequency(interval=interval)
    elif freq == "HOURLY":
        return HourlyFrequency(interval=interval)
    elif freq == "DAILY":
        return DailyFrequency(interval=interval)
    elif freq == "WEEKLY":
        on_days = parts["BYDAY"].split(",") if "BYDAY" in parts else None
        return WeeklyFrequency(interval=interval, on_days=on_days)
    elif freq == "MONTHLY":
        return _parse_monthly(parts, interval)
    else:  # YEARLY
        return YearlyFrequency(interval=interval)


def parse_end_condition(rule_string: str) -> EndByDate | EndByOccurrences | None:
    """Extract end condition from an RRULE string.

    Returns:
        EndByOccurrences for COUNT=N
        EndByDate for UNTIL=...
        None if no end condition present
    """
    if not rule_string or not rule_string.strip():
        raise ValueError("RRULE string must not be empty")

    parts = _parse_parts(rule_string)
    _validate_end_exclusion(parts)

    if "COUNT" in parts:
        return EndByOccurrences(occurrences=int(parts["COUNT"]))
    if "UNTIL" in parts:
        return EndByDate(date=_convert_until_to_iso(parts["UNTIL"]))
    return None


# ── Internal Helpers ─────────────────────────────────────────────────────


def _parse_parts(rule_string: str) -> dict[str, str]:
    """Split RRULE string into key=value dict."""
    result: dict[str, str] = {}
    for part in rule_string.strip().split(";"):
        if "=" not in part:
            raise ValueError(f"Invalid RRULE part (missing '='): {part!r}")
        key, _, value = part.partition("=")
        if not key or not value:
            raise ValueError(f"Empty key or value in RRULE part: {part!r}")
        result[key] = value
    return result


def _validate_no_bysetpos(parts: dict[str, str], rule_string: str) -> None:
    """D-05: Reject BYSETPOS with educational error."""
    if "BYSETPOS" in parts:
        raise ValueError(
            "BYSETPOS is not supported. OmniFocus uses positional BYDAY format "
            f"(e.g., BYDAY=2TU for 'second Tuesday'). "
            f"Please report this rule string: {rule_string}"
        )


def _validate_end_exclusion(parts: dict[str, str]) -> None:
    """COUNT and UNTIL are mutually exclusive (RFC 5545)."""
    if "COUNT" in parts and "UNTIL" in parts:
        raise ValueError("COUNT and UNTIL are mutually exclusive (RFC 5545)")


def _parse_monthly(
    parts: dict[str, str],
    interval: int,
) -> MonthlyFrequency | MonthlyDayOfWeekFrequency | MonthlyDayInMonthFrequency:
    """Parse MONTHLY frequency with optional BYDAY or BYMONTHDAY."""
    if "BYDAY" in parts:
        return _parse_monthly_byday(parts["BYDAY"], interval)
    if "BYMONTHDAY" in parts:
        return _parse_monthly_bymonthday(parts["BYMONTHDAY"], interval)
    return MonthlyFrequency(interval=interval)


def _parse_monthly_byday(
    byday_value: str,
    interval: int,
) -> MonthlyDayOfWeekFrequency:
    """Parse BYDAY with required positional prefix for MONTHLY context.

    D-05: Only positional prefix form accepted (e.g., 2TU, -1FR).
    Plain day codes without prefix (e.g., TU) raise ValueError.
    """
    m = _BYDAY_PATTERN.match(byday_value)
    if not m:
        raise ValueError(
            f"Invalid BYDAY value: {byday_value!r}. "
            "Expected format like 2TU (second Tuesday) or -1FR (last Friday)"
        )
    pos_str = m.group(1)
    day_code = m.group(2)

    if pos_str is None:
        raise ValueError(
            f"MONTHLY BYDAY must use positional prefix (e.g., 2TU for "
            f"'second Tuesday'), got plain day code: {byday_value!r}"
        )

    pos = int(pos_str)
    ordinal = _POS_TO_ORDINAL.get(pos)
    if ordinal is None:
        raise ValueError(
            f"Invalid BYDAY position {pos}. Valid positions: 1-5 (first-fifth) or -1 (last)"
        )

    day_name = _DAY_CODE_TO_NAME[day_code]
    return MonthlyDayOfWeekFrequency(
        interval=interval,
        on={ordinal: day_name},
    )


def _parse_monthly_bymonthday(
    bymonthday_value: str,
    interval: int,
) -> MonthlyDayInMonthFrequency:
    """Parse BYMONTHDAY for monthly_day_in_month frequency."""
    try:
        day = int(bymonthday_value)
    except ValueError as err:
        raise ValueError(f"BYMONTHDAY must be an integer, got {bymonthday_value!r}") from err
    return MonthlyDayInMonthFrequency(interval=interval, on_dates=[day])


def _convert_until_to_iso(raw: str) -> str:
    """Convert RRULE compact UNTIL format to ISO-8601.

    Input:  YYYYMMDDTHHMMSSZ (e.g., 20261231T000000Z)
    Output: YYYY-MM-DDTHH:MM:SSZ (e.g., 2026-12-31T00:00:00Z)
    """
    m = _UNTIL_PATTERN.match(raw)
    if not m:
        raise ValueError(f"UNTIL must match YYYYMMDDTHHMMSSZ format, got {raw!r}")
    return f"{m.group(1)}-{m.group(2)}-{m.group(3)}T{m.group(4)}:{m.group(5)}:{m.group(6)}Z"
