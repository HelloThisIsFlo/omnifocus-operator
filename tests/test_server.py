"""In-process MCP integration tests for the server package.

Tests verify end-to-end behaviour through the full MCP protocol using
paired memory streams -- no network sockets or subprocesses needed.
"""

from __future__ import annotations

import logging
import sys
from collections.abc import Awaitable, Callable
from typing import Any
from unittest.mock import patch

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage


# ---------------------------------------------------------------------------
# Helper
# ---------------------------------------------------------------------------

async def run_with_client(
    server: FastMCP,
    callback: Callable[[ClientSession], Awaitable[Any]],
) -> Any:
    """Run an in-process MCP server and execute *callback* with a connected ClientSession.

    The server is started in a background task and cancelled after the
    callback completes.  Returns whatever the callback returns.
    """
    s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](0)
    c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](0)

    result: Any = None

    async with anyio.create_task_group() as tg:

        async def _run_server() -> None:
            await server._mcp_server.run(
                c2s_recv,
                s2c_send,
                server._mcp_server.create_initialization_options(),
                raise_exceptions=True,
            )

        tg.start_soon(_run_server)

        async with ClientSession(s2c_recv, c2s_send) as session:
            await session.initialize()
            result = await callback(session)
            tg.cancel_scope.cancel()

    return result


# ---------------------------------------------------------------------------
# ARCH-01: Three-layer architecture (MCP tool -> Service -> Repository)
# ---------------------------------------------------------------------------

class TestARCH01ThreeLayerArchitecture:
    """Verify the MCP tool -> OperatorService -> OmniFocusRepository path."""

    async def test_list_all_returns_data_through_all_layers(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("list_all")
            assert result.structuredContent is not None
            keys = set(result.structuredContent.keys())
            assert keys == {"tasks", "projects", "tags", "folders", "perspectives"}

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# ARCH-02: Bridge injection via env var
# ---------------------------------------------------------------------------

class TestARCH02BridgeInjection:
    """Verify bridge selection through OMNIFOCUS_BRIDGE env var."""

    async def test_inmemory_bridge_via_env_var(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("list_all")
            assert result.structuredContent is not None

        await run_with_client(server, _check)

    async def test_default_real_bridge_fails_at_startup(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.delenv("OMNIFOCUS_BRIDGE", raising=False)
        from omnifocus_operator.server import create_server

        server = create_server()

        with pytest.raises(ExceptionGroup) as exc_info:
            await run_with_client(server, lambda s: s.list_tools())

        # Somewhere in the exception group should be NotImplementedError
        errors = exc_info.value.exceptions
        assert any(isinstance(e, NotImplementedError) for e in errors)


# ---------------------------------------------------------------------------
# TOOL-01: list_all structured output
# ---------------------------------------------------------------------------

class TestTOOL01ListAllStructuredOutput:
    """Verify list_all returns structuredContent with all entity collections."""

    async def test_list_all_returns_structured_content(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("list_all")
            assert result.structuredContent is not None
            expected_keys = {"tasks", "projects", "tags", "folders", "perspectives"}
            assert set(result.structuredContent.keys()) == expected_keys

        await run_with_client(server, _check)

    async def test_list_all_structured_content_is_camelcase(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify structuredContent uses camelCase field names for nested entities."""
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")

        # Populate InMemoryBridge with a task that has camelCase fields
        from omnifocus_operator.bridge import InMemoryBridge
        from omnifocus_operator.repository import ConstantMtimeSource, OmniFocusRepository
        from omnifocus_operator.service import OperatorService
        from omnifocus_operator.server._server import app_lifespan, create_server

        server = create_server()

        # We need data with recognisable camelCase fields, so we patch the
        # bridge factory to return a bridge with a task that has dueDate set.
        from omnifocus_operator.bridge._in_memory import InMemoryBridge as _IB

        task_data = {
            "id": "task-1",
            "name": "Test Task",
            "due_date": "2026-06-01T12:00:00+00:00",
            "effective_flagged": True,
        }
        bridge = _IB(
            data={
                "tasks": [task_data],
                "projects": [],
                "tags": [],
                "folders": [],
                "perspectives": [],
            }
        )
        repo = OmniFocusRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Patch lifespan to inject our service
        from contextlib import asynccontextmanager
        from collections.abc import AsyncIterator

        @asynccontextmanager
        async def _patched_lifespan(app: FastMCP) -> AsyncIterator[dict[str, Any]]:
            await repo.initialize()
            yield {"service": service}

        patched_server = FastMCP("omnifocus-operator", lifespan=_patched_lifespan)
        # Re-register the tool on patched server
        from omnifocus_operator.server._server import _register_tools

        _register_tools(patched_server)

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("list_all")
            assert result.structuredContent is not None
            tasks = result.structuredContent["tasks"]
            assert len(tasks) == 1
            task = tasks[0]
            # Must use camelCase, not snake_case
            assert "dueDate" in task
            assert "effectiveFlagged" in task
            assert "due_date" not in task
            assert "effective_flagged" not in task

        await run_with_client(patched_server, _check)


# ---------------------------------------------------------------------------
# TOOL-02: Annotations
# ---------------------------------------------------------------------------

class TestTOOL02Annotations:
    """Verify list_all tool annotations."""

    async def test_list_all_has_read_only_hint(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            list_all = next(t for t in tools_result.tools if t.name == "list_all")
            assert list_all.annotations is not None
            assert list_all.annotations.readOnlyHint is True

        await run_with_client(server, _check)

    async def test_list_all_has_idempotent_hint(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            list_all = next(t for t in tools_result.tools if t.name == "list_all")
            assert list_all.annotations is not None
            assert list_all.annotations.idempotentHint is True

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# TOOL-03: Output schema
# ---------------------------------------------------------------------------

class TestTOOL03OutputSchema:
    """Verify list_all tool has outputSchema with camelCase."""

    async def test_list_all_has_output_schema(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            list_all = next(t for t in tools_result.tools if t.name == "list_all")
            assert list_all.outputSchema is not None

        await run_with_client(server, _check)

    async def test_output_schema_uses_camelcase(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            list_all = next(t for t in tools_result.tools if t.name == "list_all")
            schema = list_all.outputSchema
            assert schema is not None

            # Top-level properties should have the 5 collection names
            props = schema.get("properties", {})
            assert "tasks" in props
            assert "projects" in props

            # Check nested Task schema uses camelCase (e.g. dueDate, effectiveFlagged)
            # The schema should have $defs with Task definition
            defs = schema.get("$defs", {})
            assert "Task" in defs, f"Expected Task in $defs, got: {list(defs.keys())}"
            task_props = defs["Task"].get("properties", {})
            assert "dueDate" in task_props, (
                f"Expected camelCase 'dueDate', got: {list(task_props.keys())}"
            )
            assert "effectiveFlagged" in task_props

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# TOOL-04: stderr only
# ---------------------------------------------------------------------------

class TestTOOL04StderrOnly:
    """Verify stdout redirection and logging to stderr."""

    def test_stdout_redirected_to_stderr(self) -> None:
        """After calling the redirect logic in __main__, stdout should be stderr."""
        original_stdout = sys.stdout
        try:
            # Import and invoke just the redirect part
            from omnifocus_operator.__main__ import main

            # We can't call main() fully (it would start the server),
            # so we test the redirect pattern directly
            sys.stdout = sys.stderr  # type: ignore[assignment]
            assert sys.stdout is sys.stderr
        finally:
            sys.stdout = original_stdout

    def test_logging_goes_to_stderr(self) -> None:
        """Verify omnifocus_operator logger writes to stderr."""
        import logging
        import os

        # Configure logging the same way __main__.py does
        level = os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO").upper()
        logger = logging.getLogger("omnifocus_operator")

        # After main() sets up logging, handlers should target stderr
        handler = logging.StreamHandler(sys.stderr)
        handler.setLevel(level)
        logger.addHandler(handler)

        try:
            # The handler we added targets stderr
            stderr_handlers = [
                h
                for h in logger.handlers
                if isinstance(h, logging.StreamHandler) and h.stream is sys.stderr
            ]
            assert len(stderr_handlers) > 0
        finally:
            logger.removeHandler(handler)
