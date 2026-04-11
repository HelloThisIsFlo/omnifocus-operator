"""Middleware module -- cross-cutting concerns for MCP tool calls."""

from __future__ import annotations

import time
from typing import TYPE_CHECKING, Any

from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from pydantic import ValidationError

from omnifocus_operator.agent_messages.errors import INVALID_INPUT, UNKNOWN_FIELD

if TYPE_CHECKING:
    import logging

__all__ = ["ToolLoggingMiddleware", "ValidationReformatterMiddleware"]


class ToolLoggingMiddleware(Middleware):
    """Log every tool call with name, arguments, timing, and errors.

    Receives an injected logger (per D-02) so all log lines appear under
    the server's namespace rather than a middleware-specific one.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        tool_name = context.message.name
        args = context.message.arguments
        # D-04: Log full arguments at INFO on entry
        if args:
            self._log.info(">>> %s(%s)", tool_name, args)
        else:
            self._log.info(">>> %s()", tool_name)
        start = time.monotonic()
        try:
            result = await call_next(context)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.info("<<< %s -- %.1fms OK", tool_name, elapsed_ms)
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.error("!!! %s -- %.1fms FAILED: %s", tool_name, elapsed_ms, e)
            raise


def _clean_loc(loc: tuple[str | int, ...]) -> tuple[str | int, ...]:
    """Strip Pydantic union-branch noise from a validation error loc path.

    ``Patch[T]`` expands to ``T | _Unset``, causing Pydantic to prefix each
    branch's errors with the model class name (``EditTaskActions``), validator
    wrapper (``function-after[...]``), or type check (``is-instance[...]``).
    This keeps only real field names and integer indices.
    """
    return tuple(
        part
        for part in loc
        if isinstance(part, int)
        or (
            isinstance(part, str)
            and not part[0].isupper()
            and not part.startswith("function-")
            and not part.startswith("is-instance")
            and not part.startswith("literal[")
            and not part.startswith("tagged-union[")
        )
    )


def _strip_items_prefix(loc: tuple[str | int, ...]) -> tuple[str | int, ...]:
    """Strip the ``items.<index>`` prefix injected by list-typed parameters.

    When FastMCP deserialises ``items: list[AddTaskCommand]``, Pydantic
    prepends ``('items', 0, ...)`` to each error location.  This helper
    removes that two-element prefix so downstream formatting sees only
    the field path within a single command object.
    """
    if len(loc) >= 2 and loc[0] == "items" and isinstance(loc[1], int):
        return loc[2:]
    return loc


def _extract_item_index(loc: tuple[str | int, ...]) -> int | None:
    """Extract the item index from an ``items.<index>`` loc prefix.

    Returns the integer index if present, ``None`` otherwise.
    """
    if len(loc) >= 2 and loc[0] == "items" and isinstance(loc[1], int):
        return loc[1]
    return None


def _extract_error_field_name(loc: tuple[str | int, ...]) -> str | None:
    """Extract the field that caused the validation error from a cleaned loc.

    Used to prefix error messages so agents know *which* field is wrong.
    Example: loc ("query", "completed") → "completed", producing
    "completed: Input should be 'all' or 'today'" instead of bare
    "Input should be 'all' or 'today'".

    Skips the first element when possible — it's typically the tool parameter
    wrapper (e.g. "query") which isn't meaningful to agents.
    """
    search = loc[1:] if len(loc) > 1 else loc
    for part in search:
        if isinstance(part, str):
            return part
    return None


def _format_validation_errors(exc: ValidationError) -> list[str]:
    """Extract clean, agent-friendly messages from a Pydantic ValidationError.

    Filters noise and rewrites common error patterns:
    - ``_Unset`` sentinel artefacts are suppressed (D-08a: ctx-based filtering)
    - ``missing`` errors are suppressed (union branch noise from non-matching types)
    - ``extra_forbidden`` -> "Unknown field '<path>'"
    - Everything else passes through (model validators produce clean messages at source)
    - D-08: Messages are prefixed with "Task N:" when the error originates from a list item
    """
    messages: list[str] = []
    for e in exc.errors():
        if e.get("ctx", {}).get("class") == "_Unset":
            continue
        if e["type"] == "missing":
            continue
        if e["type"] == "union_tag_not_found":
            continue
        raw_loc = e.get("loc", ())
        idx = _extract_item_index(raw_loc)
        cleaned_loc = _clean_loc(raw_loc)
        stripped_loc = _strip_items_prefix(cleaned_loc)
        if e["type"] == "extra_forbidden":
            field = ".".join(str(part) for part in stripped_loc)
            msg = UNKNOWN_FIELD.format(field=field)
        else:
            msg = e["msg"]
            if msg.startswith("Value error, "):
                msg = msg[len("Value error, ") :]
            field_name = _extract_error_field_name(stripped_loc)
            if field_name:
                msg = f"{field_name}: {msg}"
        if idx is not None:
            msg = f"Task {idx + 1}: {msg}"
        messages.append(msg)
    return messages


class ValidationReformatterMiddleware(Middleware):
    """Catch Pydantic ValidationError from typed tool params, reformat to clean ToolError.

    Registered INSIDE ToolLoggingMiddleware (added first = innermost) so that
    the logging middleware sees the reformatted ToolError and logs what the
    agent actually receives.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        try:
            return await call_next(context)
        except ValidationError as exc:
            messages = _format_validation_errors(exc)
            raise ToolError("; ".join(messages) or INVALID_INPUT) from None
