"""Shared date-string validation for write contracts."""

from __future__ import annotations

from datetime import datetime as _datetime

from omnifocus_operator.agent_messages.errors import INVALID_DATE_FORMAT


def validate_date_string(v: object) -> object:
    """Validate that a string is a parseable ISO date or datetime (syntax only).

    Non-str values pass through unchanged — Pydantic handles type checking.
    """
    if not isinstance(v, str):
        return v
    try:
        _datetime.fromisoformat(v)
    except ValueError:
        raise ValueError(INVALID_DATE_FORMAT.format(value=v)) from None
    return v
