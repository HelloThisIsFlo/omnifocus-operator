"""Shared validation helpers for list query contracts."""

from __future__ import annotations

from omnifocus_operator.agent_messages import errors as err


def validate_offset_requires_limit(limit: int | None, offset: int | None) -> None:
    """Raise ValueError if offset is set without limit."""
    if offset is not None and limit is None:
        raise ValueError(err.OFFSET_REQUIRES_LIMIT)
