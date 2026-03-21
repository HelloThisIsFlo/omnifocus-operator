"""In-process MCP integration tests for the server package.

Tests verify end-to-end behaviour through the full MCP protocol using
paired memory streams -- no network sockets or subprocesses needed.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage

from omnifocus_operator.repository import BridgeRepository
from omnifocus_operator.server import _register_tools, app_lifespan, create_server
from omnifocus_operator.service import OperatorService
from tests.conftest import make_tag_dict, make_task_dict
from tests.doubles import ConstantMtimeSource, InMemoryBridge, SimulatorBridge

if TYPE_CHECKING:
    from collections.abc import AsyncIterator, Awaitable, Callable

    from omnifocus_operator.repository import Repository


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_patched_server(
    repo: Repository,
    service: OperatorService,
) -> FastMCP:
    """Create a FastMCP server with a patched lifespan injecting *service*."""

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
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *a, **kw: BridgeRepository(
                bridge=InMemoryBridge(
                    data={
                        "tasks": [],
                        "projects": [],
                        "tags": [],
                        "folders": [],
                        "perspectives": [],
                    }
                ),
                mtime_source=ConstantMtimeSource(),
            ),
        )

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
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *a, **kw: BridgeRepository(
                bridge=InMemoryBridge(
                    data={
                        "tasks": [],
                        "projects": [],
                        "tags": [],
                        "folders": [],
                        "perspectives": [],
                    }
                ),
                mtime_source=ConstantMtimeSource(),
            ),
        )

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
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *a, **kw: BridgeRepository(
                bridge=InMemoryBridge(
                    data={
                        "tasks": [],
                        "projects": [],
                        "tags": [],
                        "folders": [],
                        "perspectives": [],
                    }
                ),
                mtime_source=ConstantMtimeSource(),
            ),
        )

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
        tmp_path: Any,
    ) -> None:
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *_a, **_kw: repo,
        )

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
        tmp_path: Any,
    ) -> None:
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *_a, **_kw: repo,
        )

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
        tmp_path: Any,
    ) -> None:
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *_a, **_kw: repo,
        )

        server = create_server()

        async def _check(session: ClientSession) -> None:
            tools_result = await session.list_tools()
            get_all = next(t for t in tools_result.tools if t.name == "get_all")
            assert get_all.outputSchema is not None

        await run_with_client(server, _check)

    async def test_output_schema_uses_camelcase(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *_a, **_kw: repo,
        )

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
        tmp_path: Any,
    ) -> None:
        """IPC sweep runs regardless of OMNIFOCUS_REPOSITORY setting."""
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        repo = BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *_a, **_kw: repo,
        )

        mock_sweep = AsyncMock()

        with patch(
            "omnifocus_operator.bridge.real.sweep_orphaned_files",
            mock_sweep,
        ):
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
        with patch(
            "omnifocus_operator.repository.create_repository",
            side_effect=RuntimeError("repository exploded"),
        ):
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
        with patch(
            "omnifocus_operator.repository.create_repository",
            side_effect=RuntimeError("repository exploded"),
        ):
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

    async def test_get_task_returns_task(self, client_session: ClientSession) -> None:
        result = await client_session.call_tool("get_task", {"id": "task-001"})
        assert result.isError is not True
        assert result.structuredContent is not None
        assert result.structuredContent["id"] == "task-001"
        assert result.structuredContent["name"] == "Test Task"

    async def test_get_task_not_found_returns_error(self, client_session: ClientSession) -> None:
        result = await client_session.call_tool("get_task", {"id": "nonexistent"})
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "Task not found: nonexistent" in text

    async def test_get_project_returns_project(self, client_session: ClientSession) -> None:
        result = await client_session.call_tool("get_project", {"id": "proj-001"})
        assert result.isError is not True
        assert result.structuredContent is not None
        assert result.structuredContent["id"] == "proj-001"
        assert result.structuredContent["name"] == "Test Project"

    async def test_get_project_not_found_returns_error(self, client_session: ClientSession) -> None:
        result = await client_session.call_tool("get_project", {"id": "nonexistent"})
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "Project not found: nonexistent" in text

    async def test_get_tag_returns_tag(self, client_session: ClientSession) -> None:
        result = await client_session.call_tool("get_tag", {"id": "tag-001"})
        assert result.isError is not True
        assert result.structuredContent is not None
        assert result.structuredContent["id"] == "tag-001"
        assert result.structuredContent["name"] == "Test Tag"

    async def test_get_tag_not_found_returns_error(self, client_session: ClientSession) -> None:
        result = await client_session.call_tool("get_tag", {"id": "nonexistent"})
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "Tag not found: nonexistent" in text

    async def test_get_task_has_annotations(self, client_session: ClientSession) -> None:
        tools_result = await client_session.list_tools()
        tool = next(t for t in tools_result.tools if t.name == "get_task")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True

    async def test_get_project_has_annotations(self, client_session: ClientSession) -> None:
        tools_result = await client_session.list_tools()
        tool = next(t for t in tools_result.tools if t.name == "get_project")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True

    async def test_get_tag_has_annotations(self, client_session: ClientSession) -> None:
        tools_result = await client_session.list_tools()
        tool = next(t for t in tools_result.tools if t.name == "get_tag")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True


# ---------------------------------------------------------------------------
# CREA: add_tasks tool
# ---------------------------------------------------------------------------


class TestAddTasks:
    """Verify add_tasks MCP tool registration and behaviour."""

    # -- Registration & annotations --

    async def test_add_tasks_registered(self, client_session: ClientSession) -> None:
        tools_result = await client_session.list_tools()
        names = [t.name for t in tools_result.tools]
        assert "add_tasks" in names

    async def test_add_tasks_has_write_annotations(self, client_session: ClientSession) -> None:
        tools_result = await client_session.list_tools()
        tool = next(t for t in tools_result.tools if t.name == "add_tasks")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is False
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is False

    # -- Happy path --

    async def test_add_tasks_minimal(self, client_session: ClientSession) -> None:
        """Create a task with only a name."""
        result = await client_session.call_tool("add_tasks", {"items": [{"name": "Buy milk"}]})
        assert result.isError is not True
        assert result.structuredContent is not None
        # FastMCP wraps list return in {"result": [...]}
        items = result.structuredContent["result"]
        assert isinstance(items, list)
        assert len(items) == 1
        assert items[0]["success"] is True
        assert items[0]["name"] == "Buy milk"
        assert "id" in items[0]

    async def test_add_tasks_with_parent(self, client_session: ClientSession) -> None:
        """Create a task under an existing project."""
        result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Sub task", "parent": "proj-001"}]},
        )
        assert result.isError is not True
        items = result.structuredContent["result"]
        assert items[0]["success"] is True

    async def test_add_tasks_with_tags(self, client_session: ClientSession) -> None:
        """Create a task with tag names resolved."""
        result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Tagged task", "tags": ["Test Tag"]}]},
        )
        assert result.isError is not True
        items = result.structuredContent["result"]
        assert items[0]["success"] is True

    async def test_add_tasks_all_fields(self, client_session: ClientSession) -> None:
        """Create a task with all optional fields set."""
        result = await client_session.call_tool(
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

    # -- Constraint enforcement --

    async def test_add_tasks_single_item_constraint(self, client_session: ClientSession) -> None:
        """Passing 2 items returns an error."""
        result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "A"}, {"name": "B"}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "exactly 1 item" in text

    async def test_add_tasks_empty_array(self, client_session: ClientSession) -> None:
        """Passing 0 items returns an error."""
        result = await client_session.call_tool("add_tasks", {"items": []})
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "exactly 1 item" in text

    # -- Validation errors --

    async def test_add_tasks_missing_name(self, client_session: ClientSession) -> None:
        """Item without name returns error."""
        result = await client_session.call_tool("add_tasks", {"items": [{"note": "no name"}]})
        assert result.isError is True

    async def test_add_tasks_invalid_parent(self, client_session: ClientSession) -> None:
        """Non-existent parent returns error."""
        result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Orphan", "parent": "nonexistent-id"}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "nonexistent-id" in text

    async def test_add_tasks_invalid_tag(self, client_session: ClientSession) -> None:
        """Non-existent tag returns error."""
        result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Bad tag", "tags": ["Nonexistent Tag"]}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "Nonexistent Tag" in text

    # -- Unknown field rejection (STRCT-01) --

    async def test_add_tasks_unknown_field_names_field(self, client_session: ClientSession) -> None:
        """Server error message includes the unknown field name, not generic message."""
        result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Task", "bogusField": "x"}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "Unknown field 'bogusField'" in text

    # -- Post-write freshness --

    async def test_add_tasks_then_get_all(self, client_session: ClientSession) -> None:
        """After add_tasks, get_all includes the newly created task."""
        # Create a task
        add_result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Fresh task"}]},
        )
        assert add_result.isError is not True
        new_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        # Fetch all and verify the new task appears
        get_result = await client_session.call_tool("get_all")
        assert get_result.structuredContent is not None
        task_ids = [t["id"] for t in get_result.structuredContent["tasks"]]
        assert new_id in task_ids


# ---------------------------------------------------------------------------
# EDIT: edit_tasks tool
# ---------------------------------------------------------------------------


class TestEditTasks:
    """Verify edit_tasks MCP tool registration and behaviour."""

    # -- Single-item constraint (EDIT-09) --

    async def test_edit_tasks_rejects_empty_array(self, client_session: ClientSession) -> None:
        """Passing 0 items returns an error."""
        result = await client_session.call_tool("edit_tasks", {"items": []})
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "exactly 1 item" in text

    async def test_edit_tasks_rejects_multi_item_array(self, client_session: ClientSession) -> None:
        """Passing 2+ items returns an error."""
        result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": "a"}, {"id": "b"}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "exactly 1 item" in text

    # -- Unknown field rejection (STRCT-01) --

    async def test_edit_tasks_unknown_field_names_field(
        self, client_session: ClientSession
    ) -> None:
        """Server error message includes the unknown field name, not generic message."""
        result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": "task-001", "bogusField": "x"}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "Unknown field 'bogusField'" in text

    # -- Basic field edit --

    async def test_edit_tasks_basic_name_change(self, client_session: ClientSession) -> None:
        """Create a task, edit its name, verify result and persistence."""
        # Create a task
        add_result = await client_session.call_tool("add_tasks", {"items": [{"name": "Original"}]})
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        # Edit the name
        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "name": "Updated"}]},
        )
        assert edit_result.isError is not True
        items = edit_result.structuredContent["result"]  # type: ignore[index]
        assert items[0]["success"] is True
        assert items[0]["name"] == "Updated"

        # Verify via get_task
        get_result = await client_session.call_tool("get_task", {"id": task_id})
        assert get_result.isError is not True
        assert get_result.structuredContent["name"] == "Updated"  # type: ignore[index]

    # -- Clear a field --

    async def test_edit_tasks_clear_field(self, client_session: ClientSession) -> None:
        """Create task with due date, edit with dueDate=null, verify cleared."""
        # Create task with due date
        add_result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Has due", "dueDate": "2026-06-01T12:00:00+00:00"}]},
        )
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        # Clear due date
        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "dueDate": None}]},
        )
        assert edit_result.isError is not True
        assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

        # Verify due date is cleared
        get_result = await client_session.call_tool("get_task", {"id": task_id})
        assert get_result.isError is not True
        assert get_result.structuredContent["dueDate"] is None  # type: ignore[index]

    # -- Tag replace --

    @pytest.mark.snapshot(
        tags=[
            make_tag_dict(),
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
    async def test_edit_tasks_tag_replace(self, client_session: ClientSession) -> None:
        """Create task with tags, replace tags via edit."""
        # Create task with original tag
        add_result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Tagged", "tags": ["Test Tag"]}]},
        )
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        # Replace tags
        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"tags": {"replace": ["New Tag"]}}}]},
        )
        assert edit_result.isError is not True
        assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

        # Verify tags replaced
        get_result = await client_session.call_tool("get_task", {"id": task_id})
        assert get_result.isError is not True
        tag_names = [t["name"] for t in get_result.structuredContent["tags"]]  # type: ignore[index]
        assert "tag-new" in tag_names or "New Tag" in tag_names
        # Original tag should be gone
        assert "tag-001" not in [t["id"] for t in get_result.structuredContent["tags"]]  # type: ignore[index]

    # -- Move to project --

    async def test_edit_tasks_move_to_project(self, client_session: ClientSession) -> None:
        """Create task in inbox, move to project via edit."""
        # Create task in inbox (no parent)
        add_result = await client_session.call_tool(
            "add_tasks", {"items": [{"name": "Inbox task"}]}
        )
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        # Move to project
        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"move": {"ending": "proj-001"}}}]},
        )
        assert edit_result.isError is not True
        assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

        # Verify parent changed
        get_result = await client_session.call_tool("get_task", {"id": task_id})
        assert get_result.isError is not True
        parent = get_result.structuredContent["parent"]  # type: ignore[index]
        assert parent is not None
        assert parent["id"] == "proj-001"

    # -- Move to inbox --

    async def test_edit_tasks_move_to_inbox(self, client_session: ClientSession) -> None:
        """Create task under project, move to inbox via edit."""
        # Create task under project
        add_result = await client_session.call_tool(
            "add_tasks",
            {"items": [{"name": "Project task", "parent": "proj-001"}]},
        )
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        # Move to inbox
        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"move": {"ending": None}}}]},
        )
        assert edit_result.isError is not True
        assert edit_result.structuredContent["result"][0]["success"] is True  # type: ignore[index]

        # Verify parent is null (inbox)
        get_result = await client_session.call_tool("get_task", {"id": task_id})
        assert get_result.isError is not True
        assert get_result.structuredContent["parent"] is None  # type: ignore[index]

    # -- Task not found --

    async def test_edit_tasks_not_found(self, client_session: ClientSession) -> None:
        """Edit with non-existent ID returns error."""
        result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": "nonexistent-id", "name": "Nope"}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "nonexistent-id" in text

    # -- Full roundtrip freshness --

    async def test_edit_tasks_then_get_all_reflects_change(
        self, client_session: ClientSession
    ) -> None:
        """After edit, get_all returns updated data."""
        # Create a task
        add_result = await client_session.call_tool(
            "add_tasks", {"items": [{"name": "Before edit"}]}
        )
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        # Edit its name
        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "name": "After edit"}]},
        )
        assert edit_result.isError is not True

        # Verify via get_all
        get_result = await client_session.call_tool("get_all")
        assert get_result.structuredContent is not None
        task = next(t for t in get_result.structuredContent["tasks"] if t["id"] == task_id)
        assert task["name"] == "After edit"

    # -- Registration & annotations --

    async def test_edit_tasks_registered(self, client_session: ClientSession) -> None:
        """edit_tasks tool is registered."""
        tools_result = await client_session.list_tools()
        names = [t.name for t in tools_result.tools]
        assert "edit_tasks" in names

    async def test_edit_tasks_has_write_annotations(self, client_session: ClientSession) -> None:
        """edit_tasks has correct write annotations."""
        tools_result = await client_session.list_tools()
        tool = next(t for t in tools_result.tools if t.name == "edit_tasks")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is False
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is False

    # -- Clean validation error messages --

    async def test_edit_tasks_replace_plus_add_clean_error(
        self, client_session: ClientSession
    ) -> None:
        """Pydantic error for tag mutual exclusion is clean (no type=/input/URL noise)."""
        result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": "task-001", "actions": {"tags": {"replace": ["a"], "add": ["b"]}}}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "Cannot use 'replace'" in text
        assert "type=" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text

    async def test_edit_tasks_move_multiple_keys_clean_error(
        self, client_session: ClientSession
    ) -> None:
        """Pydantic error for move multi-key is clean (no type=/input/URL noise)."""
        result = await client_session.call_tool(
            "edit_tasks",
            {
                "items": [
                    {
                        "id": "task-001",
                        "actions": {"move": {"beginning": "proj-1", "ending": "proj-1"}},
                    }
                ]
            },
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        assert "exactly one key" in text
        assert "_Unset" not in text
        assert "type=" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text


# ---------------------------------------------------------------------------
# LIFECYCLE: edit_tasks lifecycle actions (complete/drop)
# ---------------------------------------------------------------------------


class TestEditTasksLifecycle:
    """Verify lifecycle actions (complete/drop) through the server layer."""

    # -- Lifecycle: complete --

    async def test_edit_tasks_lifecycle_complete(self, client_session: ClientSession) -> None:
        """lifecycle='complete' on a normal task returns success."""
        add_result = await client_session.call_tool(
            "add_tasks", {"items": [{"name": "To Complete"}]}
        )
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"lifecycle": "complete"}}]},
        )
        assert edit_result.isError is not True
        items = edit_result.structuredContent["result"]  # type: ignore[index]
        assert items[0]["success"] is True

        # Verify task is completed via get_task
        get_result = await client_session.call_tool("get_task", {"id": task_id})
        assert get_result.isError is not True
        assert get_result.structuredContent["availability"] == "completed"  # type: ignore[index]

    # -- Lifecycle: drop --

    async def test_edit_tasks_lifecycle_drop(self, client_session: ClientSession) -> None:
        """lifecycle='drop' on a normal task returns success."""
        add_result = await client_session.call_tool("add_tasks", {"items": [{"name": "To Drop"}]})
        assert add_result.isError is not True
        task_id = add_result.structuredContent["result"][0]["id"]  # type: ignore[index]

        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"lifecycle": "drop"}}]},
        )
        assert edit_result.isError is not True
        items = edit_result.structuredContent["result"]  # type: ignore[index]
        assert items[0]["success"] is True

        # Verify task is dropped
        get_result = await client_session.call_tool("get_task", {"id": task_id})
        assert get_result.isError is not True
        assert get_result.structuredContent["availability"] == "dropped"  # type: ignore[index]

    # -- Lifecycle: invalid value --

    async def test_edit_tasks_lifecycle_invalid_clean_error(
        self, client_session: ClientSession
    ) -> None:
        """lifecycle='invalid' returns clean error echoing the value, without Pydantic internals."""
        result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": "task-001", "actions": {"lifecycle": "invalid"}}]},
        )
        assert result.isError is True
        text = result.content[0].text  # type: ignore[union-attr]
        # Must be clean -- no Pydantic internals
        assert "type=" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text
        # Must echo the invalid value and list allowed values
        assert "invalid" in text
        assert "must be 'complete' or 'drop'" in text

    # -- Lifecycle: already completed (no-op) --

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(),
            {
                "id": "completed-task",
                "name": "Already Done",
                "url": "omnifocus:///task/completed-task",
                "note": "",
                "added": "2024-01-15T10:30:00.000Z",
                "modified": "2024-01-15T10:30:00.000Z",
                "urgency": "none",
                "availability": "completed",
                "flagged": False,
                "effectiveFlagged": False,
                "dueDate": None,
                "deferDate": None,
                "effectiveDueDate": None,
                "effectiveDeferDate": None,
                "completionDate": "2024-01-15T12:00:00.000Z",
                "effectiveCompletionDate": "2024-01-15T12:00:00.000Z",
                "plannedDate": None,
                "effectivePlannedDate": None,
                "dropDate": None,
                "effectiveDropDate": None,
                "estimatedMinutes": None,
                "hasChildren": False,
                "inInbox": True,
                "repetitionRule": None,
                "parent": None,
                "tags": [],
            },
        ],
    )
    async def test_edit_tasks_lifecycle_complete_already_completed(
        self, client_session: ClientSession
    ) -> None:
        """Completing an already-completed task returns success with warning."""
        edit_result = await client_session.call_tool(
            "edit_tasks",
            {"items": [{"id": "completed-task", "actions": {"lifecycle": "complete"}}]},
        )
        assert edit_result.isError is not True
        items = edit_result.structuredContent["result"]  # type: ignore[index]
        assert items[0]["success"] is True
        warnings = items[0].get("warnings", [])
        assert any("already" in w.lower() for w in warnings)
