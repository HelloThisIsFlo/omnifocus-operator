"""RRULE builder for OmniFocus repetition rules.

Inverse of the parser: takes a flat Frequency model instance and produces
an RRULE string. Uses type string checks (not isinstance) for dispatch.

Public function:
    build_rrule(frequency, end=None) -> str
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    EndByOccurrences,
    Frequency,
    OrdinalWeekday,
)
from omnifocus_operator.rrule.parser import parse_rrule

if TYPE_CHECKING:
    from datetime import date as date_type

    from omnifocus_operator.contracts.shared.repetition_rule import FrequencyAddSpec

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

_DAY_GROUP_BYDAY: dict[str, str] = {
    "weekday": "MO,TU,WE,TH,FR",
    "weekend_day": "SU,SA",
}

_TYPE_TO_FREQ: dict[str, str] = {
    "minutely": "MINUTELY",
    "hourly": "HOURLY",
    "daily": "DAILY",
    "weekly": "WEEKLY",
    "monthly": "MONTHLY",
    "yearly": "YEARLY",
}


# ── Public API ───────────────────────────────────────────────────────────


def build_rrule(
    frequency: Frequency | FrequencyAddSpec,
    end: EndByDate | EndByOccurrences | None = None,
) -> str:
    """Build an RRULE string from a flat Frequency model and optional end condition.

    Includes round-trip validation: parse_rrule(result) must succeed.

    Args:
        frequency: Flat Frequency model instance (one of 6 types)
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
    if frequency.type == "weekly" and frequency.on_days:
        parts.append(f"BYDAY={','.join(frequency.on_days)}")
    elif frequency.type == "monthly" and frequency.on:
        parts.append(_build_byday_positional(frequency.on))  # type: ignore[arg-type]
    elif frequency.type == "monthly" and frequency.on_dates:
        parts.append(f"BYMONTHDAY={','.join(str(d) for d in frequency.on_dates)}")

    # End condition
    if isinstance(end, EndByOccurrences):
        parts.append(f"COUNT={end.occurrences}")
    elif isinstance(end, EndByDate):
        parts.append(f"UNTIL={_convert_date_to_until(end.date)}")

    result = ";".join(parts)

    # Round-trip validation: ensure the built string parses correctly
    parse_rrule(result)

    return result


# ── Internal Helpers ─────────────────────────────────────────────────────


def _build_byday_positional(on: OrdinalWeekday) -> str:
    """Build BYDAY from OrdinalWeekday model.

    For day group values (weekday, weekend_day), emits BYDAY=...;BYSETPOS=N.
    For single-day values (monday, tuesday, etc.), emits BYDAY=NXX prefix form.
    """
    ordinal, day_name = next(
        (name, val)
        for name, val in [
            ("first", on.first),
            ("second", on.second),
            ("third", on.third),
            ("fourth", on.fourth),
            ("fifth", on.fifth),
            ("last", on.last),
        ]
        if val is not None
    )
    pos = _ORDINAL_TO_POS.get(ordinal)
    if pos is None:
        raise ValueError(f"Unknown ordinal: {ordinal!r}. Valid: {sorted(_ORDINAL_TO_POS.keys())}")

    # Day group values use BYSETPOS form
    byday_group = _DAY_GROUP_BYDAY.get(day_name)
    if byday_group is not None:
        return f"BYDAY={byday_group};BYSETPOS={pos}"

    # Single-day values use prefix form
    day_code = _NAME_TO_DAY_CODE.get(day_name)
    if day_code is None:
        raise ValueError(
            f"Unknown day name: {day_name!r}. Valid: {sorted(_NAME_TO_DAY_CODE.keys())}"
        )
    return f"BYDAY={pos}{day_code}"


def _convert_date_to_until(d: date_type) -> str:
    """Convert a date object to RRULE compact UNTIL format.

    Input:  date(2026, 12, 31)
    Output: 20261231T000000Z
    """
    return d.strftime("%Y%m%dT000000Z")
