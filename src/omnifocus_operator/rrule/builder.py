"""RRULE builder for OmniFocus repetition rules.

Inverse of the parser: takes a frequency dict (or FrequencySpec model
instance) and produces an RRULE string.

Public function:
    build_rrule(frequency, end=None) -> str
"""

from __future__ import annotations

from typing import Any

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
    "monthly": "MONTHLY",
    "monthly_day_of_week": "MONTHLY",
    "monthly_day_in_month": "MONTHLY",
    "yearly": "YEARLY",
}


# ── Public API ───────────────────────────────────────────────────────────


def build_rrule(
    frequency: dict[str, Any],
    end: dict[str, Any] | None = None,
) -> str:
    """Build an RRULE string from a frequency dict and optional end condition.

    Accepts both raw dicts and model .model_dump() output.
    Includes round-trip validation: parse_rrule(result) must succeed.

    Args:
        frequency: Dict matching FrequencySpec shapes (must have "type" key)
        end: Optional end condition dict ({"occurrences": N} or {"date": "ISO-8601"})

    Returns:
        RRULE string (e.g., "FREQ=DAILY;INTERVAL=3")

    Raises:
        ValueError: On invalid input or failed round-trip validation
    """
    freq_type = frequency.get("type", "")
    freq_code = _TYPE_TO_FREQ.get(freq_type)
    if freq_code is None:
        raise ValueError(f"Unknown frequency type: {freq_type!r}")

    parts: list[str] = [f"FREQ={freq_code}"]

    # Interval (omit when 1 or absent)
    interval = frequency.get("interval", 1)
    if interval != 1:
        parts.append(f"INTERVAL={interval}")

    # Type-specific parts
    if freq_type == "weekly" and frequency.get("on_days"):
        parts.append(f"BYDAY={','.join(frequency['on_days'])}")
    elif freq_type == "monthly_day_of_week" and frequency.get("on"):
        parts.append(_build_byday_positional(frequency["on"]))
    elif freq_type == "monthly_day_in_month" and frequency.get("on_dates"):
        # BYMONTHDAY supports single value
        parts.append(f"BYMONTHDAY={frequency['on_dates'][0]}")

    # End condition
    if end is not None:
        if "occurrences" in end:
            parts.append(f"COUNT={end['occurrences']}")
        elif "date" in end:
            parts.append(f"UNTIL={_convert_iso_to_until(end['date'])}")

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
        raise ValueError(
            f"Unknown ordinal: {ordinal!r}. "
            f"Valid: {sorted(_ORDINAL_TO_POS.keys())}"
        )
    day_code = _NAME_TO_DAY_CODE.get(day_name)
    if day_code is None:
        raise ValueError(
            f"Unknown day name: {day_name!r}. "
            f"Valid: {sorted(_NAME_TO_DAY_CODE.keys())}"
        )
    return f"BYDAY={pos}{day_code}"


def _convert_iso_to_until(iso_date: str) -> str:
    """Convert ISO-8601 date to RRULE compact UNTIL format.

    Input:  YYYY-MM-DDTHH:MM:SSZ (e.g., 2026-12-31T00:00:00Z)
    Output: YYYYMMDDTHHMMSSZ (e.g., 20261231T000000Z)
    """
    # Strip dashes, colons; keep T and Z
    return iso_date.replace("-", "").replace(":", "")
