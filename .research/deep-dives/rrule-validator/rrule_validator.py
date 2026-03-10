"""
Standalone ICS RRULE validator for OmniFocus's RRULE subset.

Zero external dependencies. Validates structure, known keys, value formats,
and mutual exclusion rules per RFC 5545.

SPIKE ONLY — this is a research prototype to validate the approach.
In the real project:
- Use the existing ScheduleType and AnchorDateKey enums from models/enums.py
  instead of the RRuleComponents dataclass.
- The validate_rrule function itself (the parsing logic) is directly portable.
- Wire it into the service layer validation, not as a standalone module.
"""

from __future__ import annotations

import re
from dataclasses import dataclass

VALID_FREQS = {"DAILY", "WEEKLY", "MONTHLY", "YEARLY"}
VALID_DAYS = {"MO", "TU", "WE", "TH", "FR", "SA", "SU"}
KNOWN_KEYS = {"FREQ", "INTERVAL", "BYDAY", "BYMONTHDAY", "BYSETPOS", "COUNT", "UNTIL"}
UNTIL_PATTERN = re.compile(r"^\d{8}T\d{6}Z$")


@dataclass(frozen=True)
class RRuleComponents:
    freq: str
    interval: int | None = None
    byday: list[str] | None = None
    bymonthday: int | None = None
    bysetpos: int | None = None
    count: int | None = None
    until: str | None = None


def validate_rrule(rule_string: str) -> RRuleComponents:
    """Validate and parse an ICS RRULE string. Raises ValueError on invalid input."""
    if not rule_string or not rule_string.strip():
        raise ValueError("RRULE string must not be empty")

    if rule_string.endswith(";"):
        raise ValueError("Trailing semicolon is not allowed")

    parts = rule_string.split(";")
    seen_keys: set[str] = set()
    raw: dict[str, str] = {}

    for part in parts:
        if "=" not in part:
            raise ValueError(f"Invalid part (missing '='): {part!r}")
        key, _, value = part.partition("=")
        if not key:
            raise ValueError(f"Empty key in part: {part!r}")
        if not value:
            raise ValueError(f"Empty value for key {key!r}")
        if key in seen_keys:
            raise ValueError(f"Duplicate key: {key!r}")
        if key not in KNOWN_KEYS:
            raise ValueError(f"Unknown key: {key!r}")
        seen_keys.add(key)
        raw[key] = value

    # FREQ — required
    if "FREQ" not in raw:
        raise ValueError("FREQ is required")
    freq = raw["FREQ"]
    if freq not in VALID_FREQS:
        raise ValueError(f"Invalid FREQ: {freq!r} (must be one of {sorted(VALID_FREQS)})")

    # COUNT + UNTIL mutual exclusion
    if "COUNT" in raw and "UNTIL" in raw:
        raise ValueError("COUNT and UNTIL are mutually exclusive (RFC 5545)")

    # INTERVAL — positive integer
    interval: int | None = None
    if "INTERVAL" in raw:
        interval = _parse_positive_int(raw["INTERVAL"], "INTERVAL")

    # BYDAY — comma-separated day codes
    byday: list[str] | None = None
    if "BYDAY" in raw:
        byday = raw["BYDAY"].split(",")
        for day in byday:
            if day not in VALID_DAYS:
                raise ValueError(f"Invalid day code in BYDAY: {day!r} (must be one of {sorted(VALID_DAYS)})")

    # BYMONTHDAY — integer 1-31 or negative (-31 to -1)
    bymonthday: int | None = None
    if "BYMONTHDAY" in raw:
        try:
            bymonthday = int(raw["BYMONTHDAY"])
        except ValueError:
            raise ValueError(f"BYMONTHDAY must be an integer, got {raw['BYMONTHDAY']!r}")
        if bymonthday == 0 or bymonthday > 31 or bymonthday < -31:
            raise ValueError(f"BYMONTHDAY must be 1-31 or -31 to -1, got {bymonthday}")

    # BYSETPOS — any non-zero integer
    bysetpos: int | None = None
    if "BYSETPOS" in raw:
        try:
            bysetpos = int(raw["BYSETPOS"])
        except ValueError:
            raise ValueError(f"BYSETPOS must be an integer, got {raw['BYSETPOS']!r}")
        if bysetpos == 0:
            raise ValueError("BYSETPOS must not be zero")

    # COUNT — positive integer
    count: int | None = None
    if "COUNT" in raw:
        count = _parse_positive_int(raw["COUNT"], "COUNT")

    # UNTIL — ISO 8601 with Z suffix
    until: str | None = None
    if "UNTIL" in raw:
        until = raw["UNTIL"]
        if not UNTIL_PATTERN.match(until):
            raise ValueError(f"UNTIL must match YYYYMMDDTHHMMSSZ format, got {until!r}")

    return RRuleComponents(
        freq=freq,
        interval=interval,
        byday=byday,
        bymonthday=bymonthday,
        bysetpos=bysetpos,
        count=count,
        until=until,
    )


def build_rrule(
    freq: str,
    interval: int | None = None,
    byday: list[str] | None = None,
    bymonthday: int | None = None,
    bysetpos: int | None = None,
    count: int | None = None,
    until: str | None = None,
) -> str:
    """Build a validated ICS RRULE string from structured components.

    Validates all inputs, builds the semicolon-delimited string, and runs
    it through validate_rrule() as a round-trip sanity check.

    Raises ValueError on invalid input or invalid combinations.
    """
    # ── Validate inputs ──────────────────────────────────────────────────

    if freq not in VALID_FREQS:
        raise ValueError(f"Invalid FREQ: {freq!r} (must be one of {sorted(VALID_FREQS)})")

    if interval is not None:
        if not isinstance(interval, int) or interval <= 0:
            raise ValueError(f"INTERVAL must be a positive integer, got {interval!r}")

    if byday is not None:
        if not isinstance(byday, list) or len(byday) == 0:
            raise ValueError("BYDAY must be a non-empty list of day codes")
        for day in byday:
            if day not in VALID_DAYS:
                raise ValueError(
                    f"Invalid day code in BYDAY: {day!r} (must be one of {sorted(VALID_DAYS)})"
                )

    if bymonthday is not None:
        if not isinstance(bymonthday, int) or bymonthday == 0 or bymonthday > 31 or bymonthday < -31:
            raise ValueError(f"BYMONTHDAY must be 1-31 or -31 to -1, got {bymonthday!r}")

    if bysetpos is not None:
        if not isinstance(bysetpos, int) or bysetpos == 0:
            raise ValueError(f"BYSETPOS must be a non-zero integer, got {bysetpos!r}")
        if byday is None:
            raise ValueError("BYSETPOS requires BYDAY to be set")

    if count is not None and until is not None:
        raise ValueError("COUNT and UNTIL are mutually exclusive (RFC 5545)")

    if count is not None:
        if not isinstance(count, int) or count <= 0:
            raise ValueError(f"COUNT must be a positive integer, got {count!r}")

    if until is not None:
        if not UNTIL_PATTERN.match(until):
            raise ValueError(f"UNTIL must match YYYYMMDDTHHMMSSZ format, got {until!r}")

    # ── Build string ─────────────────────────────────────────────────────

    parts = [f"FREQ={freq}"]
    if interval is not None:
        parts.append(f"INTERVAL={interval}")
    if byday is not None:
        parts.append(f"BYDAY={','.join(byday)}")
    if bymonthday is not None:
        parts.append(f"BYMONTHDAY={bymonthday}")
    if bysetpos is not None:
        parts.append(f"BYSETPOS={bysetpos}")
    if count is not None:
        parts.append(f"COUNT={count}")
    if until is not None:
        parts.append(f"UNTIL={until}")

    result = ";".join(parts)

    # ── Round-trip validation ────────────────────────────────────────────
    validate_rrule(result)

    return result


def _parse_positive_int(value: str, key: str) -> int:
    try:
        n = int(value)
    except ValueError:
        raise ValueError(f"{key} must be a positive integer, got {value!r}")
    if n <= 0:
        raise ValueError(f"{key} must be a positive integer, got {n}")
    return n
