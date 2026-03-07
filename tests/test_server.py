"""In-process MCP integration tests for the server package.

Tests verify end-to-end behaviour through the full MCP protocol using
paired memory streams -- no network sockets or subprocesses needed.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import anyio
from mcp.client.session import ClientSession
from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    import pytest

    from omnifocus_operator.repository import Repository
    from omnifocus_operator.service import OperatorService


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_patched_server(
    repo: Repository,
    service: OperatorService,
) -> FastMCP:
    """Create a FastMCP server with a patched lifespan injecting *service*."""
    from contextlib import asynccontextmanager

    @asynccontextmanager
    async def _patched_lifespan(app: FastMCP) -> AsyncIterator[dict[str, Any]]:
        yield {"service": service}

    return FastMCP("omnifocus-operator", lifespan=_patched_lifespan)


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
    """Verify the MCP tool -> OperatorService -> Repository path."""

    async def test_get_all_returns_data_through_all_layers(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_all")
            assert result.structuredContent is not None
            keys = set(result.structuredContent.keys())
            assert keys == {"tasks", "projects", "tags", "folders", "perspectives"}

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# ARCH-02: Repository injection via env var
# ---------------------------------------------------------------------------


class TestARCH02RepositoryInjection:
    """Verify repository selection through OMNIFOCUS_REPOSITORY env var."""

    async def test_bridge_mode_via_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_all")
            assert result.structuredContent is not None

        await run_with_client(server, _check)

    async def test_sqlite_mode_missing_db_enters_error_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """FALL-03: SQLite not found -> error-serving mode with actionable message."""
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "hybrid")
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(tmp_path / "missing.db"))
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_all")
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "failed to start" in text.lower()
            assert "OMNIFOCUS_SQLITE_PATH" in text
            assert "OMNIFOCUS_REPOSITORY=bridge-only" in text

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# TOOL-01: get_all structured output
# ---------------------------------------------------------------------------


class TestTOOL01ListAllStructuredOutput:
    """Verify get_all returns structuredContent with all entity collections."""

    async def test_get_all_returns_structured_content(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_all")
            assert result.structuredContent is not None
            expected_keys = {"tasks", "projects", "tags", "folders", "perspectives"}
            assert set(result.structuredContent.keys()) == expected_keys

        await run_with_client(server, _check)

    async def test_get_all_structured_content_is_camelcase(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Verify structuredContent uses camelCase field names for nested entities."""
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")

        from omnifocus_operator.bridge.in_memory import InMemoryBridge
        from omnifocus_operator.bridge.mtime import ConstantMtimeSource
        from omnifocus_operator.repository import BridgeRepository
        from omnifocus_operator.server import _register_tools
        from omnifocus_operator.service import OperatorService

        task_data = {
            "id": "task-1",
            "name": "Test Task",
            "url": "omnifocus:///task/task-1",
            "note": "",
            "added": "2024-01-15T10:30:00.000Z",
            "modified": "2024-01-15T10:30:00.000Z",
            "urgency": "none",
            "availability": "available",
            "flagged": False,
            "effective_flagged": True,
            "has_children": False,
            "in_inbox": False,
            "due_date": "2026-06-01T12:00:00+00:00",
        }
        bridge = InMemoryBridge(
            data={
                "tasks": [task_data],
                "projects": [],
                "tags": [],
                "folders": [],
                "perspectives": [],
            }
        )
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        service = OperatorService(repository=repo)

        # Build a server with a patched lifespan that injects our custom service
        patched_server = _build_patched_server(repo, service)
        _register_tools(patched_server)

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_all")
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
    """Verify get_all tool annotations."""

    async def test_get_all_has_read_only_hint(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            get_all = next(t for t in tools_result.tools if t.name == "get_all")
            assert get_all.annotations is not None
            assert get_all.annotations.readOnlyHint is True

        await run_with_client(server, _check)

    async def test_get_all_has_idempotent_hint(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            get_all = next(t for t in tools_result.tools if t.name == "get_all")
            assert get_all.annotations is not None
            assert get_all.annotations.idempotentHint is True

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# TOOL-03: Output schema
# ---------------------------------------------------------------------------


class TestTOOL03OutputSchema:
    """Verify get_all tool has outputSchema with camelCase."""

    async def test_get_all_has_output_schema(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            get_all = next(t for t in tools_result.tools if t.name == "get_all")
            assert get_all.outputSchema is not None

        await run_with_client(server, _check)

    async def test_output_schema_uses_camelcase(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")
        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            get_all = next(t for t in tools_result.tools if t.name == "get_all")
            schema = get_all.outputSchema
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


class TestTOOL04StdoutClean:
    """Stdout is reserved for MCP protocol traffic.

    A stray ``print()`` anywhere in the source will corrupt the JSON-RPC
    stream and break the connection.  Rather than runtime hacks, we catch
    this statically: grep the source for ``print(`` calls.
    """

    def test_no_print_calls_in_source(self) -> None:
        """Source files must not contain print() calls."""
        from pathlib import Path

        src = Path(__file__).resolve().parent.parent / "src" / "omnifocus_operator"
        violations = []
        for py_file in sorted(src.rglob("*.py")):
            for i, line in enumerate(py_file.read_text().splitlines(), 1):
                stripped = line.lstrip()
                if stripped.startswith("print(") or stripped.startswith("print ("):
                    violations.append(f"{py_file.relative_to(src)}:{i}: {stripped}")

        assert not violations, (
            "print() calls found in source (stdout is reserved for MCP protocol):\n"
            + "\n".join(violations)
        )


# ---------------------------------------------------------------------------
# IPC-06: Orphan sweep always runs in app_lifespan
# ---------------------------------------------------------------------------


class TestIPC06OrphanSweepWiring:
    """Verify sweep_orphaned_files always runs in the server lifespan."""

    async def test_sweep_always_runs_even_in_bridge_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """IPC sweep runs regardless of OMNIFOCUS_REPOSITORY setting."""
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "inmemory")

        mock_sweep = AsyncMock()

        with patch(
            "omnifocus_operator.bridge.real.sweep_orphaned_files",
            mock_sweep,
        ):
            from omnifocus_operator.server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            async def _check(session: ClientSession) -> None:
                pass

            await run_with_client(server, _check)

        mock_sweep.assert_called_once()

    async def test_sweep_runs_in_sqlite_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """IPC sweep runs even when using sqlite repository mode."""
        db_file = tmp_path / "OmniFocusDatabase.db"
        db_file.touch()
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "hybrid")
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(db_file))

        mock_sweep = AsyncMock()

        with patch(
            "omnifocus_operator.bridge.real.sweep_orphaned_files",
            mock_sweep,
        ):
            from omnifocus_operator.server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            async def _check(session: ClientSession) -> None:
                pass

            await run_with_client(server, _check)

        mock_sweep.assert_called_once()


# ---------------------------------------------------------------------------
# ERR: Degraded mode (error-serving)
# ---------------------------------------------------------------------------


class TestDegradedMode:
    """Verify the server enters degraded mode on fatal startup errors."""

    async def test_tool_call_returns_error_when_lifespan_fails(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """Tool calls return isError=True with actionable message when startup fails."""
        with patch(
            "omnifocus_operator.repository.create_repository",
            side_effect=RuntimeError("repository exploded"),
        ):
            from omnifocus_operator.server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            async def _check(session: ClientSession) -> None:
                result = await session.call_tool("get_all")
                assert result.isError is True
                text = result.content[0].text  # type: ignore[union-attr]
                assert "failed to start" in text.lower()

            await run_with_client(server, _check)

    async def test_degraded_mode_logs_traceback_at_error_level(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """Full traceback is logged at ERROR level when startup fails."""
        import logging

        with patch(
            "omnifocus_operator.repository.create_repository",
            side_effect=RuntimeError("repository exploded"),
        ):
            from omnifocus_operator.server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            with caplog.at_level(logging.ERROR):

                async def _check(session: ClientSession) -> None:
                    await session.call_tool("get_all")

                await run_with_client(server, _check)

        assert any("Fatal error during startup" in r.message for r in caplog.records)

    async def test_degraded_mode_logs_warning_on_tool_call(
        self,
        monkeypatch: pytest.MonkeyPatch,
        caplog: pytest.LogCaptureFixture,
    ) -> None:
        """WARNING is logged for each tool call in degraded mode."""
        import logging

        with patch(
            "omnifocus_operator.repository.create_repository",
            side_effect=RuntimeError("repository exploded"),
        ):
            from omnifocus_operator.server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            with caplog.at_level(logging.WARNING):

                async def _check(session: ClientSession) -> None:
                    await session.call_tool("get_all")

                await run_with_client(server, _check)

        assert any("error mode" in r.message.lower() for r in caplog.records)
