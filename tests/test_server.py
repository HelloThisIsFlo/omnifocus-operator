"""In-process MCP integration tests for the server package.

Tests verify end-to-end behaviour through the full MCP protocol using
FastMCP's Client(server) pattern -- no network sockets or subprocesses needed.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client
from fastmcp.exceptions import ToolError

from omnifocus_operator.repository import BridgeRepository
from omnifocus_operator.server import _register_tools, create_server
from omnifocus_operator.service import OperatorService
from tests.conftest import make_tag_dict, make_task_dict
from tests.doubles import ConstantMtimeSource, InMemoryBridge, SimulatorBridge

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _build_patched_server(
    service: OperatorService,
) -> Any:
    """Create a FastMCP server with a patched lifespan injecting *service*."""
    from fastmcp import FastMCP  # noqa: PLC0415

    @asynccontextmanager
    async def _patched_lifespan(app: FastMCP) -> AsyncIterator[dict[str, Any]]:  # type: ignore[override]
        yield {"service": service}

    return FastMCP("omnifocus-operator", lifespan=_patched_lifespan)


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

        async with Client(server) as client:
            result = await client.call_tool("get_all")
            assert result.structured_content is not None
            keys = set(result.structured_content.keys())
            assert keys == {"tasks", "projects", "tags", "folders", "perspectives"}


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

        async with Client(server) as client:
            result = await client.call_tool("get_all")
            assert result.structured_content is not None

    async def test_sqlite_mode_missing_db_enters_error_mode(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """FALL-03: SQLite not found -> error-serving mode with actionable message."""
        monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "hybrid")
        monkeypatch.setenv("OMNIFOCUS_SQLITE_PATH", str(tmp_path / "missing.db"))

        server = create_server()

        async with Client(server) as client:
            with pytest.raises(ToolError, match=r"(?i)failed to start") as exc_info:
                await client.call_tool("get_all")
            assert "OMNIFOCUS_SQLITE_PATH" in str(exc_info.value)
            assert "OMNIFOCUS_REPOSITORY=bridge-only" in str(exc_info.value)


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

        async with Client(server) as client:
            result = await client.call_tool("get_all")
            assert result.structured_content is not None
            expected_keys = {"tasks", "projects", "tags", "folders", "perspectives"}
            assert set(result.structured_content.keys()) == expected_keys

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
        patched_server = _build_patched_server(service)
        _register_tools(patched_server)

        async with Client(patched_server) as client:
            result = await client.call_tool("get_all")
            assert result.structured_content is not None
            tasks = result.structured_content["tasks"]
            assert len(tasks) == 1
            task = tasks[0]
            # Must use camelCase, not snake_case
            assert "dueDate" in task
            assert "effectiveFlagged" in task
            assert "due_date" not in task
            assert "effective_flagged" not in task


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

        async with Client(server) as client:
            tools = await client.list_tools()
            get_all = next(t for t in tools if t.name == "get_all")
            assert get_all.annotations is not None
            assert get_all.annotations.readOnlyHint is True

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

        async with Client(server) as client:
            tools = await client.list_tools()
            get_all = next(t for t in tools if t.name == "get_all")
            assert get_all.annotations is not None
            assert get_all.annotations.idempotentHint is True


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

        async with Client(server) as client:
            tools = await client.list_tools()
            get_all = next(t for t in tools if t.name == "get_all")
            assert get_all.outputSchema is not None

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

        async with Client(server) as client:
            tools = await client.list_tools()
            get_all = next(t for t in tools if t.name == "get_all")
            schema = get_all.outputSchema
            assert schema is not None

            # Top-level properties should have the 5 collection names
            props = schema.get("properties", {})
            assert "tasks" in props
            assert "projects" in props

            # Check nested Task schema uses camelCase (e.g. dueDate, effectiveFlagged).
            # FastMCP v3 inlines definitions rather than using $defs references,
            # so look for Task properties in the tasks array items schema.
            tasks_schema = props["tasks"]
            task_props = tasks_schema.get("items", {}).get("properties", {})
            assert "dueDate" in task_props, (
                f"Expected camelCase 'dueDate', got: {list(task_props.keys())}"
            )
            assert "effectiveFlagged" in task_props


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
            server = create_server()

            async with Client(server) as _client:
                pass  # Connection triggers lifespan; sweep runs on enter

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
            server = create_server()

            async with Client(server) as _client:
                pass  # Connection triggers lifespan; sweep runs on enter

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
        """Tool calls raise ToolError with actionable message when startup fails."""
        with patch(
            "omnifocus_operator.repository.create_repository",
            side_effect=RuntimeError("repository exploded"),
        ):
            server = create_server()

            async with Client(server) as client:
                with pytest.raises(ToolError, match=r"(?i)failed to start"):
                    await client.call_tool("get_all")

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
            server = create_server()

            with caplog.at_level(logging.ERROR):
                async with Client(server) as client:
                    with pytest.raises(ToolError):
                        await client.call_tool("get_all")

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
            server = create_server()

            with caplog.at_level(logging.WARNING):
                async with Client(server) as client:
                    with pytest.raises(ToolError):
                        await client.call_tool("get_all")

        assert any("error mode" in r.message.lower() for r in caplog.records)


# ---------------------------------------------------------------------------
# LOOK: get-by-ID tools (get_task, get_project, get_tag)
# ---------------------------------------------------------------------------


class TestGetByIdTools:
    """Verify get_task, get_project, get_tag MCP tools."""

    async def test_get_task_returns_task(self, client: Any) -> None:
        result = await client.call_tool("get_task", {"id": "task-001"})
        assert result.structured_content is not None
        assert result.structured_content["id"] == "task-001"
        assert result.structured_content["name"] == "Test Task"

    async def test_get_task_not_found_returns_error(self, client: Any) -> None:
        with pytest.raises(ToolError, match="Task not found: nonexistent"):
            await client.call_tool("get_task", {"id": "nonexistent"})

    async def test_get_project_returns_project(self, client: Any) -> None:
        result = await client.call_tool("get_project", {"id": "proj-001"})
        assert result.structured_content is not None
        assert result.structured_content["id"] == "proj-001"
        assert result.structured_content["name"] == "Test Project"

    async def test_get_project_not_found_returns_error(self, client: Any) -> None:
        with pytest.raises(ToolError, match="Project not found: nonexistent"):
            await client.call_tool("get_project", {"id": "nonexistent"})

    async def test_get_tag_returns_tag(self, client: Any) -> None:
        result = await client.call_tool("get_tag", {"id": "tag-001"})
        assert result.structured_content is not None
        assert result.structured_content["id"] == "tag-001"
        assert result.structured_content["name"] == "Test Tag"

    async def test_get_tag_not_found_returns_error(self, client: Any) -> None:
        with pytest.raises(ToolError, match="Tag not found: nonexistent"):
            await client.call_tool("get_tag", {"id": "nonexistent"})

    async def test_get_task_has_annotations(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "get_task")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True

    async def test_get_project_has_annotations(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "get_project")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True

    async def test_get_tag_has_annotations(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "get_tag")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True


# ---------------------------------------------------------------------------
# CREA: add_tasks tool
# ---------------------------------------------------------------------------


class TestAddTasks:
    """Verify add_tasks MCP tool registration and behaviour."""

    # -- Registration & annotations --

    async def test_add_tasks_registered(self, client: Any) -> None:
        tools = await client.list_tools()
        names = [t.name for t in tools]
        assert "add_tasks" in names

    async def test_add_tasks_has_write_annotations(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "add_tasks")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is False
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is False

    # -- Happy path --

    async def test_add_tasks_minimal(self, client: Any) -> None:
        """Create a task with only a name."""
        result = await client.call_tool("add_tasks", {"items": [{"name": "Buy milk"}]})
        assert result.structured_content is not None
        # FastMCP wraps list return in {"result": [...]}
        items = result.structured_content["result"]
        assert isinstance(items, list)
        assert len(items) == 1
        assert items[0]["success"] is True
        assert items[0]["name"] == "Buy milk"
        assert "id" in items[0]

    async def test_add_tasks_with_parent(self, client: Any) -> None:
        """Create a task under an existing project."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Sub task", "parent": "proj-001"}]},
        )
        items = result.structured_content["result"]
        assert items[0]["success"] is True

    async def test_add_tasks_with_tags(self, client: Any) -> None:
        """Create a task with tag names resolved."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Tagged task", "tags": ["Test Tag"]}]},
        )
        items = result.structured_content["result"]
        assert items[0]["success"] is True

    async def test_add_tasks_all_fields(self, client: Any) -> None:
        """Create a task with all optional fields set."""
        result = await client.call_tool(
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
        items = result.structured_content["result"]
        assert items[0]["success"] is True
        assert items[0]["name"] == "Full task"

    # -- Constraint enforcement --

    async def test_add_tasks_single_item_constraint(self, client: Any) -> None:
        """Passing 2 items returns an error."""
        with pytest.raises(ToolError, match="exactly 1 item"):
            await client.call_tool(
                "add_tasks",
                {"items": [{"name": "A"}, {"name": "B"}]},
            )

    async def test_add_tasks_empty_array(self, client: Any) -> None:
        """Passing 0 items returns an error."""
        with pytest.raises(ToolError, match="exactly 1 item"):
            await client.call_tool("add_tasks", {"items": []})

    # -- Validation errors --

    async def test_add_tasks_missing_name(self, client: Any) -> None:
        """Item without name returns error."""
        with pytest.raises(ToolError):
            await client.call_tool("add_tasks", {"items": [{"note": "no name"}]})

    async def test_add_tasks_invalid_parent(self, client: Any) -> None:
        """Non-existent parent returns error."""
        with pytest.raises(ToolError, match="nonexistent-id"):
            await client.call_tool(
                "add_tasks",
                {"items": [{"name": "Orphan", "parent": "nonexistent-id"}]},
            )

    async def test_add_tasks_invalid_tag(self, client: Any) -> None:
        """Non-existent tag returns error."""
        with pytest.raises(ToolError, match="Nonexistent Tag"):
            await client.call_tool(
                "add_tasks",
                {"items": [{"name": "Bad tag", "tags": ["Nonexistent Tag"]}]},
            )

    # -- Unknown field rejection (STRCT-01) --

    async def test_add_tasks_unknown_field_names_field(self, client: Any) -> None:
        """Server error message includes the unknown field name, not generic message."""
        with pytest.raises(ToolError, match="Unknown field 'bogusField'"):
            await client.call_tool(
                "add_tasks",
                {"items": [{"name": "Task", "bogusField": "x"}]},
            )

    # -- Post-write freshness --

    async def test_add_tasks_then_get_all(self, client: Any) -> None:
        """After add_tasks, get_all includes the newly created task."""
        # Create a task
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Fresh task"}]},
        )
        new_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        # Fetch all and verify the new task appears
        get_result = await client.call_tool("get_all")
        assert get_result.structured_content is not None
        task_ids = [t["id"] for t in get_result.structured_content["tasks"]]
        assert new_id in task_ids


# ---------------------------------------------------------------------------
# EDIT: edit_tasks tool
# ---------------------------------------------------------------------------


class TestEditTasks:
    """Verify edit_tasks MCP tool registration and behaviour."""

    # -- Single-item constraint (EDIT-09) --

    async def test_edit_tasks_rejects_empty_array(self, client: Any) -> None:
        """Passing 0 items returns an error."""
        with pytest.raises(ToolError, match="exactly 1 item"):
            await client.call_tool("edit_tasks", {"items": []})

    async def test_edit_tasks_rejects_multi_item_array(self, client: Any) -> None:
        """Passing 2+ items returns an error."""
        with pytest.raises(ToolError, match="exactly 1 item"):
            await client.call_tool(
                "edit_tasks",
                {"items": [{"id": "a"}, {"id": "b"}]},
            )

    # -- Unknown field rejection (STRCT-01) --

    async def test_edit_tasks_unknown_field_names_field(self, client: Any) -> None:
        """Server error message includes the unknown field name, not generic message."""
        with pytest.raises(ToolError, match="Unknown field 'bogusField'"):
            await client.call_tool(
                "edit_tasks",
                {"items": [{"id": "task-001", "bogusField": "x"}]},
            )

    # -- Basic field edit --

    async def test_edit_tasks_basic_name_change(self, client: Any) -> None:
        """Create a task, edit its name, verify result and persistence."""
        # Create a task
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "Original"}]})
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        # Edit the name
        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "name": "Updated"}]},
        )
        items = edit_result.structured_content["result"]  # type: ignore[index]
        assert items[0]["success"] is True
        assert items[0]["name"] == "Updated"

        # Verify via get_task
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert get_result.structured_content["name"] == "Updated"  # type: ignore[index]

    # -- Clear a field --

    async def test_edit_tasks_clear_field(self, client: Any) -> None:
        """Create task with due date, edit with dueDate=null, verify cleared."""
        # Create task with due date
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Has due", "dueDate": "2026-06-01T12:00:00+00:00"}]},
        )
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        # Clear due date
        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "dueDate": None}]},
        )
        assert edit_result.structured_content["result"][0]["success"] is True  # type: ignore[index]

        # Verify due date is cleared
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert get_result.structured_content["dueDate"] is None  # type: ignore[index]

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
                "status": "Active",
                "childrenAreMutuallyExclusive": False,
                "parent": None,
            },
        ],
    )
    async def test_edit_tasks_tag_replace(self, client: Any) -> None:
        """Create task with tags, replace tags via edit."""
        # Create task with original tag
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Tagged", "tags": ["Test Tag"]}]},
        )
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        # Replace tags
        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"tags": {"replace": ["New Tag"]}}}]},
        )
        assert edit_result.structured_content["result"][0]["success"] is True  # type: ignore[index]

        # Verify tags replaced
        get_result = await client.call_tool("get_task", {"id": task_id})
        tag_names = [t["name"] for t in get_result.structured_content["tags"]]  # type: ignore[index]
        assert "tag-new" in tag_names or "New Tag" in tag_names
        # Original tag should be gone
        assert "tag-001" not in [t["id"] for t in get_result.structured_content["tags"]]  # type: ignore[index]

    # -- Move to project --

    async def test_edit_tasks_move_to_project(self, client: Any) -> None:
        """Create task in inbox, move to project via edit."""
        # Create task in inbox (no parent)
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "Inbox task"}]})
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        # Move to project
        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"move": {"ending": "proj-001"}}}]},
        )
        assert edit_result.structured_content["result"][0]["success"] is True  # type: ignore[index]

        # Verify parent changed
        get_result = await client.call_tool("get_task", {"id": task_id})
        parent = get_result.structured_content["parent"]  # type: ignore[index]
        assert parent is not None
        assert parent["id"] == "proj-001"

    # -- Move to inbox --

    async def test_edit_tasks_move_to_inbox(self, client: Any) -> None:
        """Create task under project, move to inbox via edit."""
        # Create task under project
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Project task", "parent": "proj-001"}]},
        )
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        # Move to inbox
        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"move": {"ending": None}}}]},
        )
        assert edit_result.structured_content["result"][0]["success"] is True  # type: ignore[index]

        # Verify parent is null (inbox)
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert get_result.structured_content["parent"] is None  # type: ignore[index]

    # -- Task not found --

    async def test_edit_tasks_not_found(self, client: Any) -> None:
        """Edit with non-existent ID returns error."""
        with pytest.raises(ToolError, match="nonexistent-id"):
            await client.call_tool(
                "edit_tasks",
                {"items": [{"id": "nonexistent-id", "name": "Nope"}]},
            )

    # -- Full roundtrip freshness --

    async def test_edit_tasks_then_get_all_reflects_change(self, client: Any) -> None:
        """After edit, get_all returns updated data."""
        # Create a task
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "Before edit"}]})
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        # Edit its name
        await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "name": "After edit"}]},
        )

        # Verify via get_all
        get_result = await client.call_tool("get_all")
        assert get_result.structured_content is not None
        task = next(t for t in get_result.structured_content["tasks"] if t["id"] == task_id)
        assert task["name"] == "After edit"

    # -- Registration & annotations --

    async def test_edit_tasks_registered(self, client: Any) -> None:
        """edit_tasks tool is registered."""
        tools = await client.list_tools()
        names = [t.name for t in tools]
        assert "edit_tasks" in names

    async def test_edit_tasks_has_write_annotations(self, client: Any) -> None:
        """edit_tasks has correct write annotations."""
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "edit_tasks")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is False
        assert tool.annotations.destructiveHint is False
        assert tool.annotations.idempotentHint is False

    # -- Clean validation error messages --

    async def test_edit_tasks_replace_plus_add_clean_error(self, client: Any) -> None:
        """Pydantic error for tag mutual exclusion is clean (no type=/input/URL noise)."""
        with pytest.raises(ToolError, match="Cannot use 'replace'") as exc_info:
            await client.call_tool(
                "edit_tasks",
                {
                    "items": [
                        {"id": "task-001", "actions": {"tags": {"replace": ["a"], "add": ["b"]}}}
                    ]
                },
            )
        text = str(exc_info.value)
        assert "type=" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text

    async def test_edit_tasks_move_multiple_keys_clean_error(self, client: Any) -> None:
        """Pydantic error for move multi-key is clean (no type=/input/URL noise)."""
        with pytest.raises(ToolError, match="exactly one key") as exc_info:
            await client.call_tool(
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
        text = str(exc_info.value)
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

    async def test_edit_tasks_lifecycle_complete(self, client: Any) -> None:
        """lifecycle='complete' on a normal task returns success."""
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "To Complete"}]})
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"lifecycle": "complete"}}]},
        )
        items = edit_result.structured_content["result"]  # type: ignore[index]
        assert items[0]["success"] is True

        # Verify task is completed via get_task
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert get_result.structured_content["availability"] == "completed"  # type: ignore[index]

    # -- Lifecycle: drop --

    async def test_edit_tasks_lifecycle_drop(self, client: Any) -> None:
        """lifecycle='drop' on a normal task returns success."""
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "To Drop"}]})
        task_id = add_result.structured_content["result"][0]["id"]  # type: ignore[index]

        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "actions": {"lifecycle": "drop"}}]},
        )
        items = edit_result.structured_content["result"]  # type: ignore[index]
        assert items[0]["success"] is True

        # Verify task is dropped
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert get_result.structured_content["availability"] == "dropped"  # type: ignore[index]

    # -- Lifecycle: invalid value --

    async def test_edit_tasks_lifecycle_invalid_clean_error(self, client: Any) -> None:
        """lifecycle='invalid' returns clean error echoing the value, without Pydantic internals."""
        with pytest.raises(ToolError, match="must be 'complete' or 'drop'") as exc_info:
            await client.call_tool(
                "edit_tasks",
                {"items": [{"id": "task-001", "actions": {"lifecycle": "invalid"}}]},
            )
        text = str(exc_info.value)
        # Must be clean -- no Pydantic internals
        assert "type=" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text
        # Must echo the invalid value
        assert "invalid" in text

    # -- Lifecycle: already completed (no-op) --

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(),
            make_task_dict(
                id="completed-task",
                name="Already Done",
                status="Completed",
                completionDate="2024-01-15T12:00:00.000Z",
            ),
        ],
    )
    async def test_edit_tasks_lifecycle_complete_already_completed(self, client: Any) -> None:
        """Completing an already-completed task returns success with warning."""
        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": "completed-task", "actions": {"lifecycle": "complete"}}]},
        )
        items = edit_result.structured_content["result"]  # type: ignore[index]
        assert items[0]["success"] is True
        warnings = items[0].get("warnings", [])
        assert any("already" in w.lower() for w in warnings)


# ---------------------------------------------------------------------------
# REPET: Repetition rule server-level handling
# ---------------------------------------------------------------------------


class TestAddTasksRepetitionRule:
    """Verify repetition rule support through the add_tasks MCP tool."""

    async def test_add_tasks_with_repetition_rule_success(self, client: Any) -> None:
        """Create a task with a valid repetition rule."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {
                        "name": "Repeating task",
                        "repetitionRule": {
                            "frequency": {"type": "daily", "interval": 3},
                            "schedule": "from_completion",
                            "basedOn": "defer_date",
                        },
                    }
                ]
            },
        )
        items = result.structured_content["result"]
        assert items[0]["success"] is True
        assert items[0]["name"] == "Repeating task"
        assert "id" in items[0]

    async def test_add_tasks_repetition_rule_validation_error(self, client: Any) -> None:
        """Invalid frequency type returns educational error listing valid types."""
        with pytest.raises(ToolError, match="Invalid frequency type") as exc_info:
            await client.call_tool(
                "add_tasks",
                {
                    "items": [
                        {
                            "name": "Bad repeat",
                            "repetitionRule": {
                                "frequency": {"type": "biweekly", "interval": 1},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "biweekly" in text
        assert "daily" in text
        assert "weekly" in text

    async def test_add_tasks_repetition_rule_unknown_field(self, client: Any) -> None:
        """Extra field on repetitionRule returns 'Unknown field' error."""
        with pytest.raises(ToolError, match=r"Unknown field 'repetitionRule\.bogusField'"):
            await client.call_tool(
                "add_tasks",
                {
                    "items": [
                        {
                            "name": "Bad field",
                            "repetitionRule": {
                                "frequency": {"type": "daily", "interval": 1},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                                "bogusField": "x",
                            },
                        }
                    ]
                },
            )

    async def test_add_tasks_interval_zero_clean_error(self, client: Any) -> None:
        """interval=0 returns clean error without pydantic internals."""
        with pytest.raises(ToolError, match="Interval must be") as exc_info:
            await client.call_tool(
                "add_tasks",
                {
                    "items": [
                        {
                            "name": "Bad interval",
                            "repetitionRule": {
                                "frequency": {"type": "daily", "interval": 0},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "type=" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text

    async def test_add_tasks_end_occurrences_zero_clean_error(self, client: Any) -> None:
        """end:{occurrences: 0} returns clean error without 'Field required' noise."""
        with pytest.raises(ToolError, match="occurrences must be") as exc_info:
            await client.call_tool(
                "add_tasks",
                {
                    "items": [
                        {
                            "name": "Bad occurrences",
                            "repetitionRule": {
                                "frequency": {"type": "daily"},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                                "end": {"occurrences": 0},
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "Field required" not in text

    async def test_add_tasks_end_empty_object_clean_error(self, client: Any) -> None:
        """end:{} returns actionable error explaining what's needed."""
        with pytest.raises(ToolError, match="end requires either") as exc_info:
            await client.call_tool(
                "add_tasks",
                {
                    "items": [
                        {
                            "name": "Empty end",
                            "repetitionRule": {
                                "frequency": {"type": "daily"},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                                "end": {},
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "date" in text
        assert "occurrences" in text


class TestEditTasksRepetitionRule:
    """Verify repetition rule support through the edit_tasks MCP tool."""

    async def test_edit_tasks_with_repetition_rule_success(self, client: Any) -> None:
        """Set a repetition rule on an existing task."""
        # Create task first
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "Will repeat"}]})
        task_id = add_result.structured_content["result"][0]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {
                        "id": task_id,
                        "repetitionRule": {
                            "frequency": {
                                "type": "weekly",
                                "interval": 1,
                                "onDays": ["MO", "FR"],
                            },
                            "schedule": "regularly",
                            "basedOn": "due_date",
                        },
                    }
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[0]["success"] is True

    async def test_edit_tasks_clear_repetition_rule(self, client: Any) -> None:
        """Setting repetitionRule to null clears it."""
        # Create task with repetition
        add_result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {
                        "name": "Has repeat",
                        "repetitionRule": {
                            "frequency": {"type": "daily", "interval": 1},
                            "schedule": "regularly",
                            "basedOn": "due_date",
                        },
                    }
                ]
            },
        )
        task_id = add_result.structured_content["result"][0]["id"]

        # Clear the repetition rule
        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": task_id, "repetitionRule": None}]},
        )
        items = edit_result.structured_content["result"]
        assert items[0]["success"] is True

        # Verify it was cleared
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert get_result.structured_content["repetitionRule"] is None

    async def test_edit_tasks_repetition_partial_update(self, client: Any) -> None:
        """Partial update changes only the specified root field."""
        # Create task with repetition rule
        add_result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {
                        "name": "Partial update",
                        "repetitionRule": {
                            "frequency": {"type": "daily", "interval": 1},
                            "schedule": "regularly",
                            "basedOn": "due_date",
                        },
                    }
                ]
            },
        )
        task_id = add_result.structured_content["result"][0]["id"]

        # Partial update: change only schedule
        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {
                        "id": task_id,
                        "repetitionRule": {"schedule": "from_completion"},
                    }
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[0]["success"] is True

    async def test_edit_tasks_interval_zero_clean_error(self, client: Any) -> None:
        """interval=0 on edit returns clean error without pydantic internals."""
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "For edit"}]})
        task_id = add_result.structured_content["result"][0]["id"]

        with pytest.raises(ToolError, match="Interval must be") as exc_info:
            await client.call_tool(
                "edit_tasks",
                {
                    "items": [
                        {
                            "id": task_id,
                            "repetitionRule": {
                                "frequency": {"type": "daily", "interval": 0},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "type=" not in text
        assert "pydantic" not in text.lower()
        assert "input_value" not in text

    async def test_edit_tasks_end_occurrences_zero_clean_error(self, client: Any) -> None:
        """end:{occurrences: 0} on edit returns clean error without '_Unset' noise."""
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "For edit"}]})
        task_id = add_result.structured_content["result"][0]["id"]

        with pytest.raises(ToolError, match="occurrences must be") as exc_info:
            await client.call_tool(
                "edit_tasks",
                {
                    "items": [
                        {
                            "id": task_id,
                            "repetitionRule": {
                                "frequency": {"type": "daily"},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                                "end": {"occurrences": 0},
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "_Unset" not in text
        assert "Field required" not in text

    async def test_edit_tasks_end_empty_object_clean_error(self, client: Any) -> None:
        """end:{} on edit returns actionable error explaining what's needed."""
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "For edit"}]})
        task_id = add_result.structured_content["result"][0]["id"]

        with pytest.raises(ToolError, match="end requires either") as exc_info:
            await client.call_tool(
                "edit_tasks",
                {
                    "items": [
                        {
                            "id": task_id,
                            "repetitionRule": {
                                "frequency": {"type": "daily"},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                                "end": {},
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "date" in text
        assert "occurrences" in text


class TestAnchorDateWarning:
    """Verify anchor date missing warning through add_tasks and edit_tasks MCP tools."""

    async def test_add_tasks_repetition_anchor_date_missing_warning(self, client: Any) -> None:
        """Add task with basedOn='due_date' but no dueDate produces warning."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {
                        "name": "Missing anchor",
                        "repetitionRule": {
                            "frequency": {"type": "daily"},
                            "schedule": "regularly",
                            "basedOn": "due_date",
                        },
                    }
                ]
            },
        )
        items = result.structured_content["result"]
        assert items[0]["success"] is True
        assert items[0]["warnings"] is not None
        warnings = items[0]["warnings"]
        assert any("basedOn is 'due_date'" in w for w in warnings)
        assert any("dueDate" in w for w in warnings)

    async def test_add_tasks_repetition_anchor_date_present_no_warning(self, client: Any) -> None:
        """Add task with basedOn='due_date' AND dueDate set produces no anchor warning."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {
                        "name": "Has anchor date",
                        "dueDate": "2026-06-01T12:00:00Z",
                        "repetitionRule": {
                            "frequency": {"type": "daily"},
                            "schedule": "regularly",
                            "basedOn": "due_date",
                        },
                    }
                ]
            },
        )
        items = result.structured_content["result"]
        assert items[0]["success"] is True
        # No warnings at all, or no anchor-related warning
        warnings = items[0].get("warnings") or []
        assert not any("basedOn" in w for w in warnings)

    async def test_edit_tasks_repetition_anchor_date_existing_task_has_date(
        self, client: Any
    ) -> None:
        """Edit task that already has dueDate, set basedOn='due_date' -> no anchor warning."""
        # Create task with dueDate
        add_result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {
                        "name": "Has due date",
                        "dueDate": "2026-06-01T12:00:00Z",
                    }
                ]
            },
        )
        task_id = add_result.structured_content["result"][0]["id"]

        # Edit: add repetition rule with basedOn=due_date
        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {
                        "id": task_id,
                        "repetitionRule": {
                            "frequency": {"type": "daily"},
                            "schedule": "regularly",
                            "basedOn": "due_date",
                        },
                    }
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[0]["success"] is True
        warnings = items[0].get("warnings") or []
        assert not any("basedOn" in w for w in warnings)
