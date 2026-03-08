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


# ---------------------------------------------------------------------------
# LOOK: get-by-ID tools (get_task, get_project, get_tag)
# ---------------------------------------------------------------------------


class TestGetByIdTools:
    """Verify get_task, get_project, get_tag MCP tools."""

    async def _make_server_with_data(self) -> FastMCP:
        """Build a test server with known snapshot data."""
        from omnifocus_operator.repository import InMemoryRepository
        from omnifocus_operator.server import _register_tools
        from omnifocus_operator.service import OperatorService

        from .conftest import make_snapshot

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        server = _build_patched_server(repo, service)
        _register_tools(server)
        return server

    async def test_get_task_returns_task(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_task", {"id": "task-001"})
            assert result.isError is not True
            assert result.structuredContent is not None
            assert result.structuredContent["id"] == "task-001"
            assert result.structuredContent["name"] == "Test Task"

        await run_with_client(server, _check)

    async def test_get_task_not_found_returns_error(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_task", {"id": "nonexistent"})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "Task not found: nonexistent" in text

        await run_with_client(server, _check)

    async def test_get_project_returns_project(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_project", {"id": "proj-001"})
            assert result.isError is not True
            assert result.structuredContent is not None
            assert result.structuredContent["id"] == "proj-001"
            assert result.structuredContent["name"] == "Test Project"

        await run_with_client(server, _check)

    async def test_get_project_not_found_returns_error(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_project", {"id": "nonexistent"})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "Project not found: nonexistent" in text

        await run_with_client(server, _check)

    async def test_get_tag_returns_tag(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_tag", {"id": "tag-001"})
            assert result.isError is not True
            assert result.structuredContent is not None
            assert result.structuredContent["id"] == "tag-001"
            assert result.structuredContent["name"] == "Test Tag"

        await run_with_client(server, _check)

    async def test_get_tag_not_found_returns_error(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("get_tag", {"id": "nonexistent"})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "Tag not found: nonexistent" in text

        await run_with_client(server, _check)

    async def test_get_task_has_annotations(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            tool = next(t for t in tools_result.tools if t.name == "get_task")
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.idempotentHint is True

        await run_with_client(server, _check)

    async def test_get_project_has_annotations(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            tool = next(t for t in tools_result.tools if t.name == "get_project")
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.idempotentHint is True

        await run_with_client(server, _check)

    async def test_get_tag_has_annotations(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            tool = next(t for t in tools_result.tools if t.name == "get_tag")
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is True
            assert tool.annotations.idempotentHint is True

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# CREA: add_tasks tool
# ---------------------------------------------------------------------------


class TestAddTasks:
    """Verify add_tasks MCP tool registration and behaviour."""

    async def _make_server_with_data(
        self,
        *,
        extra_projects: list[dict[str, Any]] | None = None,
        extra_tags: list[dict[str, Any]] | None = None,
    ) -> FastMCP:
        """Build a test server with InMemoryRepository and known data."""
        from omnifocus_operator.repository import InMemoryRepository
        from omnifocus_operator.server import _register_tools
        from omnifocus_operator.service import OperatorService

        from .conftest import make_project_dict, make_snapshot, make_tag_dict

        projects = [make_project_dict()]
        if extra_projects:
            projects.extend(extra_projects)

        tags = [make_tag_dict()]
        if extra_tags:
            tags.extend(extra_tags)

        snapshot = make_snapshot(projects=projects, tags=tags)
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        server = _build_patched_server(repo, service)
        _register_tools(server)
        return server

    # -- Registration & annotations --

    async def test_add_tasks_registered(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            names = [t.name for t in tools_result.tools]
            assert "add_tasks" in names

        await run_with_client(server, _check)

    async def test_add_tasks_has_write_annotations(self) -> None:
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            tool = next(t for t in tools_result.tools if t.name == "add_tasks")
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is False
            assert tool.annotations.destructiveHint is False
            assert tool.annotations.idempotentHint is False

        await run_with_client(server, _check)

    # -- Happy path --

    async def test_add_tasks_minimal(self) -> None:
        """Create a task with only a name."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("add_tasks", {"items": [{"name": "Buy milk"}]})
            assert result.isError is not True
            assert result.structuredContent is not None
            # FastMCP wraps list return in {"result": [...]}
            items = result.structuredContent["result"]
            assert isinstance(items, list)
            assert len(items) == 1
            assert items[0]["success"] is True
            assert items[0]["name"] == "Buy milk"
            assert "id" in items[0]

        await run_with_client(server, _check)

    async def test_add_tasks_with_parent(self) -> None:
        """Create a task under an existing project."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Sub task", "parent": "proj-001"}]},
            )
            assert result.isError is not True
            items = result.structuredContent["result"]
            assert items[0]["success"] is True

        await run_with_client(server, _check)

    async def test_add_tasks_with_tags(self) -> None:
        """Create a task with tag names resolved."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Tagged task", "tags": ["Test Tag"]}]},
            )
            assert result.isError is not True
            items = result.structuredContent["result"]
            assert items[0]["success"] is True

        await run_with_client(server, _check)

    async def test_add_tasks_all_fields(self) -> None:
        """Create a task with all optional fields set."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "add_tasks",
                {
                    "items": [
                        {
                            "name": "Full task",
                            "parent": "proj-001",
                            "tags": ["Test Tag"],
                            "dueDate": "2026-06-01T12:00:00+00:00",
                            "deferDate": "2026-05-01T08:00:00+00:00",
                            "plannedDate": "2026-05-15T09:00:00+00:00",
                            "flagged": True,
                            "estimatedMinutes": 30,
                            "note": "Important note",
                        }
                    ]
                },
            )
            assert result.isError is not True
            items = result.structuredContent["result"]
            assert items[0]["success"] is True
            assert items[0]["name"] == "Full task"

        await run_with_client(server, _check)

    # -- Constraint enforcement --

    async def test_add_tasks_single_item_constraint(self) -> None:
        """Passing 2 items returns an error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "A"}, {"name": "B"}]},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "exactly 1 item" in text

        await run_with_client(server, _check)

    async def test_add_tasks_empty_array(self) -> None:
        """Passing 0 items returns an error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("add_tasks", {"items": []})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "exactly 1 item" in text

        await run_with_client(server, _check)

    # -- Validation errors --

    async def test_add_tasks_missing_name(self) -> None:
        """Item without name returns error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("add_tasks", {"items": [{"note": "no name"}]})
            assert result.isError is True

        await run_with_client(server, _check)

    async def test_add_tasks_invalid_parent(self) -> None:
        """Non-existent parent returns error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Orphan", "parent": "nonexistent-id"}]},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "nonexistent-id" in text

        await run_with_client(server, _check)

    async def test_add_tasks_invalid_tag(self) -> None:
        """Non-existent tag returns error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Bad tag", "tags": ["Nonexistent Tag"]}]},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "Nonexistent Tag" in text

        await run_with_client(server, _check)

    # -- Post-write freshness --

    async def test_add_tasks_then_get_all(self) -> None:
        """After add_tasks, get_all includes the newly created task."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            # Create a task
            add_result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Fresh task"}]},
            )
            assert add_result.isError is not True
            new_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

            # Fetch all and verify the new task appears
            get_result = await session.call_tool("get_all")
            assert get_result.structuredContent is not None
            task_ids = [t["id"] for t in get_result.structuredContent["tasks"]]
            assert new_id in task_ids

        await run_with_client(server, _check)


# ---------------------------------------------------------------------------
# EDIT: edit_tasks tool
# ---------------------------------------------------------------------------


class TestEditTasks:
    """Verify edit_tasks MCP tool registration and behaviour."""

    async def _make_server_with_data(
        self,
        *,
        extra_tasks: list[dict[str, Any]] | None = None,
        extra_projects: list[dict[str, Any]] | None = None,
        extra_tags: list[dict[str, Any]] | None = None,
    ) -> FastMCP:
        """Build a test server with InMemoryRepository and known data."""
        from omnifocus_operator.repository import InMemoryRepository
        from omnifocus_operator.server import _register_tools
        from omnifocus_operator.service import OperatorService

        from .conftest import make_project_dict, make_snapshot, make_tag_dict, make_task_dict

        tasks = [make_task_dict()]
        if extra_tasks:
            tasks.extend(extra_tasks)

        projects = [make_project_dict()]
        if extra_projects:
            projects.extend(extra_projects)

        tags = [make_tag_dict()]
        if extra_tags:
            tags.extend(extra_tags)

        snapshot = make_snapshot(tasks=tasks, projects=projects, tags=tags)
        repo = InMemoryRepository(snapshot=snapshot)
        service = OperatorService(repository=repo)

        server = _build_patched_server(repo, service)
        _register_tools(server)
        return server

    # -- Single-item constraint (EDIT-09) --

    async def test_edit_tasks_rejects_empty_array(self) -> None:
        """Passing 0 items returns an error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool("edit_tasks", {"items": []})
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "exactly 1 item" in text

        await run_with_client(server, _check)

    async def test_edit_tasks_rejects_multi_item_array(self) -> None:
        """Passing 2+ items returns an error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": "a"}, {"id": "b"}]},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "exactly 1 item" in text

        await run_with_client(server, _check)

    # -- Basic field edit --

    async def test_edit_tasks_basic_name_change(self) -> None:
        """Create a task, edit its name, verify result and persistence."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            # Create a task
            add_result = await session.call_tool("add_tasks", {"items": [{"name": "Original"}]})
            assert add_result.isError is not True
            task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

            # Edit the name
            edit_result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": task_id, "name": "Updated"}]},
            )
            assert edit_result.isError is not True
            items = edit_result.structuredContent["result"]  # type: ignore[index]
            assert items[0]["success"] is True
            assert items[0]["name"] == "Updated"

            # Verify via get_task
            get_result = await session.call_tool("get_task", {"id": task_id})
            assert get_result.isError is not True
            assert get_result.structuredContent["name"] == "Updated"  # type: ignore[index]

        await run_with_client(server, _check)

    # -- Clear a field --

    async def test_edit_tasks_clear_field(self) -> None:
        """Create task with due date, edit with dueDate=null, verify cleared."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            # Create task with due date
            add_result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Has due", "dueDate": "2026-06-01T12:00:00+00:00"}]},
            )
            assert add_result.isError is not True
            task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

            # Clear due date
            edit_result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": task_id, "dueDate": None}]},
            )
            assert edit_result.isError is not True
            assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

            # Verify due date is cleared
            get_result = await session.call_tool("get_task", {"id": task_id})
            assert get_result.isError is not True
            assert get_result.structuredContent["dueDate"] is None  # type: ignore[index]

        await run_with_client(server, _check)

    # -- Tag replace --

    async def test_edit_tasks_tag_replace(self) -> None:
        """Create task with tags, replace tags via edit."""
        server = await self._make_server_with_data(
            extra_tags=[
                {
                    "id": "tag-new",
                    "name": "New Tag",
                    "url": "omnifocus:///tag/tag-new",
                    "added": "2024-01-15T10:30:00.000Z",
                    "modified": "2024-01-15T10:30:00.000Z",
                    "availability": "available",
                    "childrenAreMutuallyExclusive": False,
                    "parent": None,
                },
            ],
        )

        async def _check(session: ClientSession) -> None:
            # Create task with original tag
            add_result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Tagged", "tags": ["Test Tag"]}]},
            )
            assert add_result.isError is not True
            task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

            # Replace tags
            edit_result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": task_id, "tags": ["New Tag"]}]},
            )
            assert edit_result.isError is not True
            assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

            # Verify tags replaced
            get_result = await session.call_tool("get_task", {"id": task_id})
            assert get_result.isError is not True
            tag_names = [t["name"] for t in get_result.structuredContent["tags"]]  # type: ignore[index]
            assert "tag-new" in tag_names or "New Tag" in tag_names
            # Original tag should be gone
            assert "tag-001" not in [t["id"] for t in get_result.structuredContent["tags"]]  # type: ignore[index]

        await run_with_client(server, _check)

    # -- Move to project --

    async def test_edit_tasks_move_to_project(self) -> None:
        """Create task in inbox, move to project via edit."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            # Create task in inbox (no parent)
            add_result = await session.call_tool("add_tasks", {"items": [{"name": "Inbox task"}]})
            assert add_result.isError is not True
            task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

            # Move to project
            edit_result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": task_id, "moveTo": {"ending": "proj-001"}}]},
            )
            assert edit_result.isError is not True
            assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

            # Verify parent changed
            get_result = await session.call_tool("get_task", {"id": task_id})
            assert get_result.isError is not True
            parent = get_result.structuredContent["parent"]  # type: ignore[index]
            assert parent is not None
            assert parent["id"] == "proj-001"

        await run_with_client(server, _check)

    # -- Move to inbox --

    async def test_edit_tasks_move_to_inbox(self) -> None:
        """Create task under project, move to inbox via edit."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            # Create task under project
            add_result = await session.call_tool(
                "add_tasks",
                {"items": [{"name": "Project task", "parent": "proj-001"}]},
            )
            assert add_result.isError is not True
            task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

            # Move to inbox
            edit_result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": task_id, "moveTo": {"ending": None}}]},
            )
            assert edit_result.isError is not True
            assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

            # Verify parent is null (inbox)
            get_result = await session.call_tool("get_task", {"id": task_id})
            assert get_result.isError is not True
            assert get_result.structuredContent["parent"] is None  # type: ignore[index]

        await run_with_client(server, _check)

    # -- Task not found --

    async def test_edit_tasks_not_found(self) -> None:
        """Edit with non-existent ID returns error."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": "nonexistent-id", "name": "Nope"}]},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "nonexistent-id" in text

        await run_with_client(server, _check)

    # -- Full roundtrip freshness --

    async def test_edit_tasks_then_get_all_reflects_change(self) -> None:
        """After edit, get_all returns updated data."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            # Create a task
            add_result = await session.call_tool("add_tasks", {"items": [{"name": "Before edit"}]})
            assert add_result.isError is not True
            task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

            # Edit its name
            edit_result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": task_id, "name": "After edit"}]},
            )
            assert edit_result.isError is not True

            # Verify via get_all
            get_result = await session.call_tool("get_all")
            assert get_result.structuredContent is not None
            task = next(t for t in get_result.structuredContent["tasks"] if t["id"] == task_id)
            assert task["name"] == "After edit"

        await run_with_client(server, _check)

    # -- Registration & annotations --

    async def test_edit_tasks_registered(self) -> None:
        """edit_tasks tool is registered."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            names = [t.name for t in tools_result.tools]
            assert "edit_tasks" in names

        await run_with_client(server, _check)

    async def test_edit_tasks_has_write_annotations(self) -> None:
        """edit_tasks has correct write annotations."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            tool = next(t for t in tools_result.tools if t.name == "edit_tasks")
            assert tool.annotations is not None
            assert tool.annotations.readOnlyHint is False
            assert tool.annotations.destructiveHint is False
            assert tool.annotations.idempotentHint is False

        await run_with_client(server, _check)

    # -- Clean validation error messages --

    async def test_edit_tasks_tags_plus_addtags_clean_error(self) -> None:
        """Pydantic error for tag mutual exclusion is clean (no type=/input/URL noise)."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "edit_tasks",
                {"items": [{"id": "task-001", "tags": ["a"], "addTags": ["b"]}]},
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "Cannot use 'tags'" in text
            assert "type=" not in text
            assert "pydantic" not in text.lower()
            assert "input_value" not in text

        await run_with_client(server, _check)

    async def test_edit_tasks_moveto_multiple_keys_clean_error(self) -> None:
        """Pydantic error for moveTo multi-key is clean (no type=/input/URL noise)."""
        server = await self._make_server_with_data()

        async def _check(session: ClientSession) -> None:
            result = await session.call_tool(
                "edit_tasks",
                {
                    "items": [
                        {
                            "id": "task-001",
                            "moveTo": {"beginning": "proj-1", "ending": "proj-1"},
                        }
                    ]
                },
            )
            assert result.isError is True
            text = result.content[0].text  # type: ignore[union-attr]
            assert "exactly one key" in text
            assert "type=" not in text
            assert "pydantic" not in text.lower()
            assert "input_value" not in text

        await run_with_client(server, _check)
