"""Shared validation helpers for list query contracts."""

from __future__ import annotations

import re
from typing import TYPE_CHECKING

from omnifocus_operator.agent_messages import errors as err

if TYPE_CHECKING:
    from collections.abc import Sequence

DURATION_PATTERN = re.compile(r"^(\d*)([dwmy])$")


def parse_duration(value: str) -> tuple[int, str]:
    """Parse "[N]unit" -> (count, unit). Count defaults to 1.

    Raises ValueError if the string doesn't match the duration pattern.
    Contract-layer validation (validate_duration) runs first, so this
    is a defensive guard — callers should never hit this path.
    """
    match = DURATION_PATTERN.match(value)
    if not match:
        raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=value))
    count_str = match.group(1)
    count = int(count_str) if count_str else 1
    return (count, match.group(2))


def validate_duration(v: str) -> str:
    """Validate a duration string like '3d', '2w', 'm', '1y'."""
    try:
        count, _ = parse_duration(v)
    except ValueError:
        raise ValueError(err.DATE_FILTER_INVALID_DURATION.format(value=v)) from None
    if count <= 0:
        raise ValueError(err.DATE_FILTER_ZERO_NEGATIVE.format(value=v))
    return v


def reject_null_filters(data: dict[str, object], field_names: list[str]) -> None:
    """Reject null values on Patch filter fields before Pydantic sees them.

    Called from model_validator(mode="before") on each query model.
    Catches null early so the error message is clean (no _Unset leak).
    Checks both snake_case and camelCase variants of each field name.
    """
    for name in field_names:
        camel = _to_camel(name)
        if name in data and data[name] is None:
            raise ValueError(err.FILTER_NULL.format(field=camel))
        if camel != name and camel in data and data[camel] is None:
            raise ValueError(err.FILTER_NULL.format(field=camel))


def validate_non_empty_list(value: Sequence[object], field_name: str) -> None:
    """Raise ValueError if list is empty."""
    if len(value) == 0:
        alias = _to_camel(field_name)
        raise ValueError(err.TAGS_EMPTY.format(field=alias))


def validate_offset_requires_limit(limit: int | None, offset: int | None) -> None:
    """Raise ValueError if offset is set without limit."""
    if offset is not None and offset > 0 and limit is None:
        raise ValueError(err.OFFSET_REQUIRES_LIMIT)


def _to_camel(snake: str) -> str:
    """Convert snake_case to camelCase for agent-facing error messages."""
    parts = snake.split("_")
    return parts[0] + "".join(p.capitalize() for p in parts[1:])
