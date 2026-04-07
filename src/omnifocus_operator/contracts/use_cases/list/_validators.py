"""Shared validation helpers for list query contracts."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.agent_messages import errors as err

if TYPE_CHECKING:
    from collections.abc import Sequence


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
