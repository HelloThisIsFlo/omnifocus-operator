"""Unit tests for ToolLoggingMiddleware, ValidationReformatterMiddleware helpers, and logging setup.

Tests verify that the middleware logs tool entry, exit (with timing),
and errors correctly. Uses mock MiddlewareContext and call_next to
isolate middleware behavior from the FastMCP server.

Also tests _configure_logging() dual-handler setup from __main__.py.

Additionally tests the middleware helper functions:
- _format_validation_errors (WRIT-04: "Task N:" format)
- _strip_items_prefix
- _extract_item_index
- _clean_loc
- UNSET sentinel filtering (WRIT-05: ctx-based, not string-based)
- Logging integration (WRIT-10: ToolError appears in captured logs)
"""

from __future__ import annotations

import logging
import re
from logging.handlers import RotatingFileHandler
from typing import Any
from unittest.mock import AsyncMock, MagicMock

import pytest
from fastmcp.exceptions import ToolError
from pydantic import BaseModel, ConfigDict, ValidationError

from omnifocus_operator.__main__ import _configure_logging
from omnifocus_operator.middleware import (
    ToolLoggingMiddleware,
    _clean_loc,
    _extract_item_index,
    _format_validation_errors,
    _strip_items_prefix,
)


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


# ── Helpers for constructing real ValidationErrors ─────────────────────


class _TestModel(BaseModel):
    """Minimal model for testing validation error formatting."""

    name: str
    model_config = ConfigDict(extra="forbid")


class _TestListWrapper(BaseModel):
    """Wrapper that mimics list-typed tool params (items: list[Model])."""

    items: list[_TestModel]


def _capture_validation_error(model: type[BaseModel], data: dict[str, Any]) -> Any:
    """Validate data against model, return the ValidationError."""
    try:
        model.model_validate(data)
    except ValidationError as exc:
        return exc
    raise AssertionError(f"Expected ValidationError, but {model.__name__} validated successfully")


# ── _strip_items_prefix ────────────────────────────────────────────────


class TestStripItemsPrefix:
    """Unit tests for _strip_items_prefix."""

    def test_strips_items_and_index(self) -> None:
        assert _strip_items_prefix(("items", 0, "name")) == ("name",)

    def test_strips_items_with_nested_path(self) -> None:
        assert _strip_items_prefix(("items", 1, "dueDate", "nested")) == ("dueDate", "nested")

    def test_no_items_prefix_unchanged(self) -> None:
        assert _strip_items_prefix(("name",)) == ("name",)

    def test_empty_tuple_unchanged(self) -> None:
        assert _strip_items_prefix(()) == ()


# ── _extract_item_index ────────────────────────────────────────────────


class TestExtractItemIndex:
    """Unit tests for _extract_item_index."""

    def test_extracts_index_zero(self) -> None:
        assert _extract_item_index(("items", 0, "name")) == 0

    def test_extracts_index_five(self) -> None:
        assert _extract_item_index(("items", 5, "field")) == 5

    def test_no_items_prefix_returns_none(self) -> None:
        assert _extract_item_index(("name",)) is None

    def test_empty_tuple_returns_none(self) -> None:
        assert _extract_item_index(()) is None


# ── _clean_loc ─────────────────────────────────────────────────────────


class TestCleanLoc:
    """Unit tests for _clean_loc -- strips Pydantic union-branch noise."""

    def test_keeps_field_names_and_integers(self) -> None:
        assert _clean_loc(("items", 0, "name")) == ("items", 0, "name")

    def test_strips_uppercase_class_names(self) -> None:
        # Pydantic injects model class names like "EditTaskActions"
        assert _clean_loc(("items", 0, "EditTaskActions", "tags")) == ("items", 0, "tags")

    def test_strips_function_prefix(self) -> None:
        assert _clean_loc(("function-after[validate]", "name")) == ("name",)

    def test_strips_is_instance_prefix(self) -> None:
        assert _clean_loc(("is-instance[str]", "value")) == ("value",)

    def test_strips_literal_prefix(self) -> None:
        assert _clean_loc(("literal[complete]",)) == ()

    def test_strips_tagged_union_prefix(self) -> None:
        """tagged-union[...] from discriminated unions should be stripped."""
        assert _clean_loc(
            ("tagged-union[ThisPeriodFilter,LastPeriodFilter]", "this_period", "after")
        ) == (
            "this_period",
            "after",
        )

    def test_empty_tuple(self) -> None:
        assert _clean_loc(()) == ()


# ── _format_validation_errors (WRIT-04) ───────────────────────────────


class TestFormatValidationErrors:
    """Unit tests for _format_validation_errors -- 'Task N:' format."""

    def test_single_error_produces_task_1_prefix(self) -> None:
        """WRIT-04: error at items.0 produces 'Task 1:' prefix."""
        exc = _capture_validation_error(_TestListWrapper, {"items": [{"bogus": "x"}]})
        messages = _format_validation_errors(exc)
        task_1_msgs = [m for m in messages if m.startswith("Task 1:")]
        assert len(task_1_msgs) >= 1, f"Expected 'Task 1:' prefix, got: {messages}"

    def test_third_item_produces_task_3_prefix(self) -> None:
        """WRIT-04: error at items.2 produces 'Task 3:' prefix."""
        exc = _capture_validation_error(
            _TestListWrapper,
            {"items": [{"name": "ok"}, {"name": "ok"}, {"bogus": "x"}]},
        )
        messages = _format_validation_errors(exc)
        task_3_msgs = [m for m in messages if m.startswith("Task 3:")]
        assert len(task_3_msgs) >= 1, f"Expected 'Task 3:' prefix, got: {messages}"

    def test_error_without_items_prefix_has_no_task_prefix(self) -> None:
        """Error on a non-list field has no 'Task N:' prefix."""
        exc = _capture_validation_error(_TestModel, {"bogus": "x"})
        messages = _format_validation_errors(exc)
        for msg in messages:
            assert not msg.startswith("Task "), f"Unexpected 'Task' prefix in: {msg}"

    def test_extra_forbidden_produces_unknown_field(self) -> None:
        """extra_forbidden error produces 'Unknown field' message."""
        exc = _capture_validation_error(_TestListWrapper, {"items": [{"bogus": "x"}]})
        messages = _format_validation_errors(exc)
        unknown_msgs = [m for m in messages if "Unknown field" in m]
        assert len(unknown_msgs) >= 1, f"Expected 'Unknown field' message, got: {messages}"
        # Should include the field name
        assert any("bogus" in m for m in unknown_msgs), (
            f"Expected field name 'bogus' in message, got: {unknown_msgs}"
        )


# ── UNSET filtering (WRIT-05) ─────────────────────────────────────────


class TestUnsetFiltering:
    """Unit tests for UNSET sentinel filtering -- ctx-based, not string-based (D-08a)."""

    def test_unset_ctx_class_errors_are_filtered_out(self) -> None:
        """WRIT-05: errors with ctx.class='_Unset' are excluded from output."""
        exc = _capture_validation_error(_TestModel, {"bogus": "x"})
        # Monkey-patch the errors to inject an _Unset ctx entry
        original_errors = exc.errors()
        patched = [
            *original_errors,
            {
                "type": "is_instance_of",
                "loc": ("items", 0, "name"),
                "msg": "Input should be an instance of _Unset",
                "input": "test",
                "ctx": {"class": "_Unset"},
            },
        ]
        # Replace the errors method
        exc.errors = lambda: patched  # type: ignore[assignment]
        messages = _format_validation_errors(exc)
        # The _Unset error should be filtered out
        for msg in messages:
            assert "_Unset" not in msg, f"_Unset error was not filtered: {msg}"

    def test_unset_in_msg_but_not_ctx_is_not_filtered(self) -> None:
        """WRIT-05: filtering uses ctx, not string matching (D-08a).

        An error mentioning '_Unset' in msg but without ctx.class='_Unset'
        should NOT be filtered out.
        """
        exc = _capture_validation_error(_TestModel, {"bogus": "x"})
        original_errors = exc.errors()
        # Add an error with _Unset in msg but no ctx.class
        patched = [
            *original_errors,
            {
                "type": "value_error",
                "loc": ("name",),
                "msg": "Something about _Unset is wrong",
                "input": "test",
                "ctx": {},  # No "class" key
            },
        ]
        exc.errors = lambda: patched  # type: ignore[assignment]
        messages = _format_validation_errors(exc)
        # The error mentioning _Unset should still appear (not filtered)
        assert any("_Unset" in m for m in messages), (
            f"Error with _Unset in msg was incorrectly filtered: {messages}"
        )

    def test_mix_of_unset_and_real_errors_returns_only_real(self) -> None:
        """WRIT-05: mix of UNSET and real errors returns only the real errors."""
        exc = _capture_validation_error(_TestModel, {"bogus": "x"})
        real_error = {
            "type": "value_error",
            "loc": ("name",),
            "msg": "Real validation failure",
            "input": "test",
        }
        unset_error = {
            "type": "is_instance_of",
            "loc": ("name",),
            "msg": "Input should be an instance of _Unset",
            "input": "test",
            "ctx": {"class": "_Unset"},
        }
        exc.errors = lambda: [unset_error, real_error]  # type: ignore[assignment]
        messages = _format_validation_errors(exc)
        assert len(messages) == 1
        assert "Real validation failure" in messages[0]


# ── union_tag_not_found suppression ─────────────────────────────────────


class TestUnionTagNotFoundSuppression:
    """union_tag_not_found from discriminated unions leaks function names -- suppress it."""

    def test_union_tag_not_found_is_suppressed(self) -> None:
        """Discriminator function name should not appear in agent-facing errors."""
        exc = _capture_validation_error(_TestModel, {"bogus": "x"})
        union_tag_error = {
            "type": "union_tag_not_found",
            "loc": ("completed",),
            "msg": "Unable to extract tag using discriminator _route_date_filter()",
            "input": True,
        }
        real_error = {
            "type": "value_error",
            "loc": ("completed",),
            "msg": "Input should be 'all' or 'today'",
            "input": True,
        }
        exc.errors = lambda: [union_tag_error, real_error]  # type: ignore[assignment]
        messages = _format_validation_errors(exc)
        assert len(messages) == 1
        assert "_route_date_filter" not in messages[0]
        assert "Input should be" in messages[0]

    def test_union_tag_not_found_alone_produces_fallback(self) -> None:
        """If union_tag_not_found is the only error, empty list triggers INVALID_INPUT fallback."""
        exc = _capture_validation_error(_TestModel, {"bogus": "x"})
        union_tag_error = {
            "type": "union_tag_not_found",
            "loc": ("field",),
            "msg": "Unable to extract tag using discriminator _route_date_filter()",
            "input": True,
        }
        exc.errors = lambda: [union_tag_error]  # type: ignore[assignment]
        messages = _format_validation_errors(exc)
        assert len(messages) == 0  # Middleware falls back to INVALID_INPUT


# ── Logging integration (WRIT-10) ─────────────────────────────────────


class TestLoggingIntegration:
    """WRIT-10: Validation ToolErrors appear in captured logs via logging middleware."""

    @pytest.mark.asyncio
    async def test_validation_error_appears_in_logs(
        self, client: Any, caplog: pytest.LogCaptureFixture
    ) -> None:
        """Trigger a validation error through the full middleware stack,
        verify the ToolError message appears in log output."""
        with (
            caplog.at_level(logging.DEBUG, logger="omnifocus_operator.server"),
            pytest.raises(ToolError),
        ):
            await client.call_tool("add_tasks", {"items": [{"bogus": "field"}]})

        # The logging middleware should have logged the error
        error_records = [r for r in caplog.records if r.levelno >= logging.ERROR]
        assert len(error_records) >= 1, "Expected at least one ERROR log record"
        error_text = " ".join(r.message for r in error_records)
        # The logged error should contain the reformatted ToolError content
        assert "add_tasks" in error_text, f"Expected 'add_tasks' in error log, got: {error_text}"
        assert "FAILED" in error_text, f"Expected 'FAILED' in error log, got: {error_text}"
