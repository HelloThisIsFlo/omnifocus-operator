"""Unit tests for ToolLoggingMiddleware and logging setup.

Tests verify that the middleware logs tool entry, exit (with timing),
and errors correctly. Uses mock MiddlewareContext and call_next to
isolate middleware behavior from the FastMCP server.

Also tests _configure_logging() dual-handler setup from __main__.py.
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from unittest.mock import AsyncMock, MagicMock

import pytest

from omnifocus_operator.__main__ import _configure_logging
from omnifocus_operator.middleware import ToolLoggingMiddleware


def _make_context(tool_name: str, arguments: dict[str, object] | None = None) -> MagicMock:
    """Create a mock MiddlewareContext with the given tool name and arguments."""
    ctx = MagicMock()
    ctx.message.name = tool_name
    ctx.message.arguments = arguments
    return ctx


@pytest.fixture
def logger() -> logging.Logger:
    """Create a named logger for test capture via caplog."""
    return logging.getLogger("test.middleware")


@pytest.fixture
def middleware(logger: logging.Logger) -> ToolLoggingMiddleware:
    return ToolLoggingMiddleware(logger)


# ── Test 1: logs entry with tool name and arguments ──────────────────


@pytest.mark.asyncio
async def test_logs_entry_with_arguments(
    middleware: ToolLoggingMiddleware, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _make_context("get_task", {"id": "abc123"})
    call_next = AsyncMock(return_value="result")

    with caplog.at_level(logging.INFO, logger="test.middleware"):
        await middleware.on_call_tool(ctx, call_next)

    entry_line = caplog.records[0].message
    assert ">>> get_task(" in entry_line
    assert "abc123" in entry_line


# ── Test 2: logs entry with no arguments ─────────────────────────────


@pytest.mark.asyncio
async def test_logs_entry_no_arguments(
    middleware: ToolLoggingMiddleware, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _make_context("get_all", arguments=None)
    call_next = AsyncMock(return_value="result")

    with caplog.at_level(logging.INFO, logger="test.middleware"):
        await middleware.on_call_tool(ctx, call_next)

    entry_line = caplog.records[0].message
    assert ">>> get_all()" in entry_line


# ── Test 3: logs exit with timing ────────────────────────────────────


@pytest.mark.asyncio
async def test_logs_exit_with_timing(
    middleware: ToolLoggingMiddleware, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _make_context("get_all")
    call_next = AsyncMock(return_value="result")

    with caplog.at_level(logging.INFO, logger="test.middleware"):
        await middleware.on_call_tool(ctx, call_next)

    exit_line = caplog.records[1].message
    assert "<<< get_all" in exit_line
    assert "ms OK" in exit_line
    # Timing should be a positive number
    assert re.search(r"\d+\.\d+ms OK", exit_line)


# ── Test 4: logs error with timing on exception ─────────────────────


@pytest.mark.asyncio
async def test_logs_error_with_timing(
    middleware: ToolLoggingMiddleware, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _make_context("add_tasks")
    call_next = AsyncMock(side_effect=ValueError("something broke"))

    with (
        caplog.at_level(logging.INFO, logger="test.middleware"),
        pytest.raises(ValueError, match="something broke"),
    ):
        await middleware.on_call_tool(ctx, call_next)

    error_line = caplog.records[1].message
    assert "!!! add_tasks" in error_line
    assert "ms FAILED" in error_line
    assert re.search(r"\d+\.\d+ms FAILED", error_line)


# ── Test 5: re-raises the original exception ─────────────────────────


@pytest.mark.asyncio
async def test_reraises_original_exception(
    middleware: ToolLoggingMiddleware, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _make_context("edit_tasks")
    original_error = RuntimeError("database connection lost")
    call_next = AsyncMock(side_effect=original_error)

    with (
        caplog.at_level(logging.INFO, logger="test.middleware"),
        pytest.raises(RuntimeError) as exc_info,
    ):
        await middleware.on_call_tool(ctx, call_next)

    assert exc_info.value is original_error


# ── Test 6: returns the result from call_next ─────────────────────────


@pytest.mark.asyncio
async def test_returns_result_from_call_next(
    middleware: ToolLoggingMiddleware, caplog: pytest.LogCaptureFixture
) -> None:
    ctx = _make_context("get_project")
    expected_result = {"id": "proj1", "name": "My Project"}
    call_next = AsyncMock(return_value=expected_result)

    with caplog.at_level(logging.INFO, logger="test.middleware"):
        result = await middleware.on_call_tool(ctx, call_next)

    assert result is expected_result


# ── Logging setup tests ──────────────────────────────────────────────


@pytest.fixture
def clean_root_logger():
    """Ensure omnifocus_operator root logger is clean before/after test."""
    root = logging.getLogger("omnifocus_operator")
    original_handlers = root.handlers[:]
    original_level = root.level
    original_propagate = root.propagate
    root.handlers.clear()

    yield root

    root.handlers.clear()
    root.handlers.extend(original_handlers)
    root.setLevel(original_level)
    root.propagate = original_propagate


def test_configure_logging_attaches_two_handlers(
    clean_root_logger: logging.Logger,
) -> None:
    _configure_logging()
    assert len(clean_root_logger.handlers) == 2


def test_configure_logging_first_handler_is_stream_handler(
    clean_root_logger: logging.Logger,
) -> None:
    _configure_logging()
    handler = clean_root_logger.handlers[0]
    assert isinstance(handler, logging.StreamHandler)
    # Must not be a RotatingFileHandler subclass -- it's the stderr handler
    assert not isinstance(handler, RotatingFileHandler)


def test_configure_logging_second_handler_is_rotating_file(
    clean_root_logger: logging.Logger,
) -> None:
    _configure_logging()
    handler = clean_root_logger.handlers[1]
    assert isinstance(handler, RotatingFileHandler)


def test_configure_logging_default_level_is_info(
    clean_root_logger: logging.Logger,
) -> None:
    _configure_logging()
    assert clean_root_logger.level == logging.INFO


def test_configure_logging_propagate_is_false(
    clean_root_logger: logging.Logger,
) -> None:
    _configure_logging()
    assert clean_root_logger.propagate is False
