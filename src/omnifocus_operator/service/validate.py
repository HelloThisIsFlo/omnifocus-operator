"""Input validation -- pure checks on user-provided values.

With the flat Frequency model, all repetition rule validation has migrated
to Pydantic model validators on Frequency/FrequencyAddSpec. This module
retains task name validation and list query validation helpers.
"""

from __future__ import annotations

import re

from omnifocus_operator.agent_messages import errors as err
from omnifocus_operator.contracts.base import is_set

__all__ = [
    "parse_review_due_within",
    "validate_offset_requires_limit",
    "validate_task_name",
    "validate_task_name_if_set",
]

# --- Task name validation ---


def validate_task_name(name: str | None) -> None:
    """Raise ValueError if name is empty or whitespace."""
    if not name or not name.strip():
        raise ValueError(err.TASK_NAME_REQUIRED)


def validate_task_name_if_set(name: object) -> None:
    """Raise ValueError if name is provided but empty/whitespace.

    Accepts ``_Unset`` (no-op) or a string. If string, validates
    it is non-empty.
    """
    if not is_set(name):
        return
    if not name or not str(name).strip():
        raise ValueError(err.TASK_NAME_EMPTY)


# --- List query validation ---

_DURATION_PATTERN = re.compile(r"^(\d+)([dwmy])$")


def validate_offset_requires_limit(limit: int | None, offset: int | None) -> None:
    """Raise ValueError if offset is set without limit."""
    if offset is not None and limit is None:
        raise ValueError(err.OFFSET_REQUIRES_LIMIT)


def parse_review_due_within(value: str) -> object:
    """Parse a duration string like '1w', '2m', 'now' into ReviewDueFilter.

    Raises ValueError with educational message on invalid format.
    """
    from omnifocus_operator.contracts.use_cases.list.projects import (
        DurationUnit,
        ReviewDueFilter,
    )

    if not value:
        raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=value))

    if value == "now":
        return ReviewDueFilter(amount=None, unit=None)

    match = _DURATION_PATTERN.match(value)
    if not match:
        raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=value))

    amount = int(match.group(1))
    unit_str = match.group(2)

    if amount <= 0:
        raise ValueError(err.REVIEW_DUE_WITHIN_INVALID.format(value=value))

    return ReviewDueFilter(amount=amount, unit=DurationUnit(unit_str))
