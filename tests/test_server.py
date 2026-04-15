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

from omnifocus_operator.repository import BridgeOnlyRepository
from omnifocus_operator.server import _register_tools, create_server
from omnifocus_operator.service import OperatorService
from omnifocus_operator.service.preferences import OmniFocusPreferences
from tests.conftest import (
    make_folder_dict,
    make_perspective_dict,
    make_project_dict,
    make_tag_dict,
    make_task_dict,
)
from tests.doubles import ConstantMtimeSource, InMemoryBridge, SimulatorBridge

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _extract_all_property_keys(schema: dict[str, Any]) -> list[str]:
    """Recursively extract all JSON Schema property keys from a schema dict."""
    keys: list[str] = []
    if isinstance(schema, dict):
        if "properties" in schema:
            keys.extend(schema["properties"].keys())
            for v in schema["properties"].values():
                keys.extend(_extract_all_property_keys(v))
        if "$defs" in schema:
            for v in schema["$defs"].values():
                keys.extend(_extract_all_property_keys(v))
        if "items" in schema:
            keys.extend(_extract_all_property_keys(schema["items"]))
        for key in ("anyOf", "oneOf", "allOf"):
            if key in schema:
                for item in schema[key]:
                    keys.extend(_extract_all_property_keys(item))
    return keys


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
            lambda *a, **kw: BridgeOnlyRepository(
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
    """Verify repository selection through OPERATOR_REPOSITORY env var."""

    async def test_bridge_mode_via_env_var(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *a, **kw: BridgeOnlyRepository(
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
        monkeypatch.setenv("OPERATOR_REPOSITORY", "hybrid")
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(tmp_path / "missing.db"))

        server = create_server()

        async with Client(server) as client:
            with pytest.raises(ToolError, match=r"(?i)failed to start") as exc_info:
                await client.call_tool("get_all")
            assert "OPERATOR_SQLITE_PATH" in str(exc_info.value)
            assert "OPERATOR_REPOSITORY=bridge-only" in str(exc_info.value)


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
            lambda *a, **kw: BridgeOnlyRepository(
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
            "inherited_flagged": True,
            "has_children": False,
            "parent": {"project": {"id": "proj-1", "name": "My Project"}},
            "project": {"id": "proj-1", "name": "My Project"},
            "due_date": "2026-06-01T12:00:00+00:00",
        }
        # Project with flagged=True so inherited_flagged on task is truly inherited
        project_data = {
            "id": "proj-1",
            "name": "My Project",
            "url": "omnifocus:///project/proj-1",
            "note": "",
            "added": "2024-01-15T10:30:00.000Z",
            "modified": "2024-01-15T10:30:00.000Z",
            "urgency": "none",
            "availability": "available",
            "flagged": True,
            "has_children": True,
            "last_review_date": "2024-01-10T10:00:00+00:00",
            "next_review_date": "2024-01-17T10:00:00+00:00",
            "review_interval": {"steps": 7, "unit": "days"},
        }
        bridge = InMemoryBridge(
            data={
                "tasks": [task_data],
                "projects": [project_data],
                "tags": [],
                "folders": [],
                "perspectives": [],
            }
        )
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())

        preferences = OmniFocusPreferences(bridge)
        service = OperatorService(repository=repo, preferences=preferences)

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
            assert "inheritedFlagged" in task
            assert "due_date" not in task
            assert "inherited_flagged" not in task


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
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
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
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
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
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *_a, **_kw: repo,
        )

        server = create_server()

        async with Client(server) as client:
            tools = await client.list_tools()
            get_all = next(t for t in tools if t.name == "get_all")
            assert get_all.outputSchema is not None

    async def test_write_tools_retain_typed_output_schema(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Any,
    ) -> None:
        """Write tools (add/edit) return typed models with structured outputSchema.

        Read tools return dict[str, Any] after response shaping (D-09), so their
        outputSchema is generic. This is an accepted trade-off per D-09:
        "MCP clients strip outputSchema anyway; available fields documented in tool description."
        """
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
        monkeypatch.setattr(
            "omnifocus_operator.repository.create_repository",
            lambda *_a, **_kw: repo,
        )

        server = create_server()

        async with Client(server) as client:
            tools = await client.list_tools()
            add = next(t for t in tools if t.name == "add_tasks")
            edit = next(t for t in tools if t.name == "edit_tasks")
            # Write tools still have typed outputSchema with properties
            add_props = _extract_all_property_keys(add.outputSchema or {})
            assert "status" in add_props
            assert "id" in add_props
            edit_props = _extract_all_property_keys(edit.outputSchema or {})
            assert "status" in edit_props
            assert "id" in edit_props


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
        """IPC sweep runs regardless of OPERATOR_REPOSITORY setting."""
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
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
        monkeypatch.setenv("OPERATOR_REPOSITORY", "hybrid")
        monkeypatch.setenv("OPERATOR_SQLITE_PATH", str(db_file))

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
        assert items[0]["status"] == "success"
        assert items[0]["name"] == "Buy milk"
        assert "id" in items[0]

    async def test_add_tasks_with_parent(self, client: Any) -> None:
        """Create a task under an existing project."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Sub task", "parent": "proj-001"}]},
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "success"

    async def test_add_tasks_with_tags(self, client: Any) -> None:
        """Create a task with tag names resolved."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Tagged task", "tags": ["Test Tag"]}]},
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "success"

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
        assert items[0]["status"] == "success"
        assert items[0]["name"] == "Full task"

    # -- Batch constraint enforcement --

    async def test_add_tasks_two_items_best_effort(self, client: Any) -> None:
        """Passing 2 items processes both (best-effort batch)."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "A"}, {"name": "B"}]},
        )
        items = result.structured_content["result"]
        assert len(items) == 2
        assert all(item["status"] == "success" for item in items)

    async def test_add_tasks_empty_array(self, client: Any) -> None:
        """Passing 0 items returns an error (min_length=1)."""
        with pytest.raises(ToolError):
            await client.call_tool("add_tasks", {"items": []})

    # -- Validation errors --

    async def test_add_tasks_missing_name(self, client: Any) -> None:
        """Item without name returns error."""
        with pytest.raises(ToolError):
            await client.call_tool("add_tasks", {"items": [{"note": "no name"}]})

    async def test_add_tasks_invalid_parent(self, client: Any) -> None:
        """Non-existent parent returns per-item error (best-effort: no ToolError raised)."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Orphan", "parent": "nonexistent-id"}]},
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "error"
        assert "nonexistent-id" in items[0]["error"]

    async def test_add_tasks_invalid_tag(self, client: Any) -> None:
        """Non-existent tag returns per-item error (best-effort: no ToolError raised)."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Bad tag", "tags": ["Nonexistent Tag"]}]},
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "error"
        assert "Nonexistent Tag" in items[0]["error"]

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

    # -- Batch constraint enforcement --

    async def test_edit_tasks_rejects_empty_array(self, client: Any) -> None:
        """Passing 0 items returns an error (min_length=1)."""
        with pytest.raises(ToolError):
            await client.call_tool("edit_tasks", {"items": []})

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
        assert items[0]["status"] == "success"
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
        assert edit_result.structured_content["result"][0]["status"] == "success"  # type: ignore[index]

        # Verify due date is cleared (stripped from response — absent field = not set)
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert "dueDate" not in get_result.structured_content  # type: ignore[index]

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
        assert edit_result.structured_content["result"][0]["status"] == "success"  # type: ignore[index]

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
        assert edit_result.structured_content["result"][0]["status"] == "success"  # type: ignore[index]

        # Verify parent changed (tagged ParentRef: {"task": {id, name}} when parent is project ID
        # because InMemoryBridge sets both parent and project to the same project ID)
        get_result = await client.call_tool("get_task", {"id": task_id})
        parent = get_result.structured_content["parent"]  # type: ignore[index]
        assert parent is not None
        # Parent is tagged -- either task or project key
        parent_ref = parent.get("task") or parent.get("project")
        assert parent_ref is not None
        assert parent_ref["id"] == "proj-001"

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
            {"items": [{"id": task_id, "actions": {"move": {"ending": "$inbox"}}}]},
        )
        assert edit_result.structured_content["result"][0]["status"] == "success"  # type: ignore[index]

        # Verify parent points to $inbox
        get_result = await client.call_tool("get_task", {"id": task_id})
        parent = get_result.structured_content["parent"]  # type: ignore[index]
        assert parent is not None
        assert parent["project"]["id"] == "$inbox"

    # -- Task not found --

    async def test_edit_tasks_not_found(self, client: Any) -> None:
        """Edit with non-existent ID returns per-item error (fail-fast: no ToolError raised)."""
        result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": "nonexistent-id", "name": "Nope"}]},
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "error"
        assert "nonexistent-id" in items[0]["error"]

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
        assert items[0]["status"] == "success"

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
        assert items[0]["status"] == "success"

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
        assert items[0]["status"] == "success"
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
        assert items[0]["status"] == "success"
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

    async def test_add_tasks_end_unknown_keys_clean_error(self, client: Any) -> None:
        """end with unrecognized keys returns actionable error."""
        with pytest.raises(ToolError, match="end requires either") as exc_info:
            await client.call_tool(
                "add_tasks",
                {
                    "items": [
                        {
                            "name": "Bad end keys",
                            "repetitionRule": {
                                "frequency": {"type": "daily"},
                                "schedule": "regularly",
                                "basedOn": "due_date",
                                "end": {"bogus": "value"},
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
        assert items[0]["status"] == "success"

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
        assert items[0]["status"] == "success"

        # Verify it was cleared (stripped from response — absent field = not set)
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert "repetitionRule" not in get_result.structured_content

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
        assert items[0]["status"] == "success"

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

    async def test_edit_tasks_invalid_frequency_type_clean_error(self, client: Any) -> None:
        """Invalid frequency type on edit returns educational error listing valid types."""
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "For edit"}]})
        task_id = add_result.structured_content["result"][0]["id"]

        with pytest.raises(ToolError, match="Invalid frequency type") as exc_info:
            await client.call_tool(
                "edit_tasks",
                {
                    "items": [
                        {
                            "id": task_id,
                            "repetitionRule": {
                                "frequency": {"type": "fortnightly"},
                            },
                        }
                    ]
                },
            )
        text = str(exc_info.value)
        assert "fortnightly" in text
        assert "daily" in text
        assert "weekly" in text

    async def test_edit_tasks_repetition_rule_unknown_field(self, client: Any) -> None:
        """Extra field on repetitionRule in edit returns 'Unknown field' error."""
        add_result = await client.call_tool("add_tasks", {"items": [{"name": "For edit"}]})
        task_id = add_result.structured_content["result"][0]["id"]

        with pytest.raises(ToolError, match=r"Unknown field 'repetitionRule\.bogusField'"):
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
                                "bogusField": "x",
                            },
                        }
                    ]
                },
            )

    async def test_edit_tasks_end_unknown_keys_clean_error(self, client: Any) -> None:
        """end with unrecognized keys on edit returns actionable error."""
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
                                "end": {"bogus": "value"},
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
        assert items[0]["status"] == "success"
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
        assert items[0]["status"] == "success"
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
        assert items[0]["status"] == "success"
        warnings = items[0].get("warnings") or []
        assert not any("basedOn" in w for w in warnings)


# ---------------------------------------------------------------------------
# WRIT-01/02/03: Schema richness — inputSchema exposes typed fields
# ---------------------------------------------------------------------------


class TestSchemaRichness:
    """Verify that add_tasks and edit_tasks expose rich inputSchema with camelCase aliases."""

    async def test_add_tasks_schema_has_rich_input_schema(self, client: Any) -> None:
        """WRIT-01: add_tasks inputSchema contains typed fields with camelCase aliases."""
        tools = await client.list_tools()
        add_tool = next(t for t in tools if t.name == "add_tasks")
        schema_json = __import__("json").dumps(add_tool.inputSchema)

        # Schema should be substantial (rich, not just {"items": {}})
        assert len(schema_json) > 500, f"Schema too small ({len(schema_json)} chars)"

        # Key fields present (camelCase)
        for field in ("name", "dueDate", "flagged", "estimatedMinutes", "repetitionRule", "tags"):
            assert field in schema_json, f"Missing field '{field}' in add_tasks inputSchema"

        # WRIT-03: No snake_case leakage in property names.
        # Note: "due_date" etc. appear legitimately as enum values in basedOn,
        # so we check for JSON property keys ('"key":' pattern) not bare strings.

        schema = add_tool.inputSchema
        property_keys = set(_extract_all_property_keys(schema))
        for snake in ("due_date", "defer_date", "estimated_minutes", "planned_date"):
            assert snake not in property_keys, (
                f"snake_case property '{snake}' leaked into add_tasks inputSchema"
            )

    async def test_edit_tasks_schema_has_rich_input_schema(self, client: Any) -> None:
        """WRIT-02: edit_tasks inputSchema contains typed fields with camelCase aliases."""
        tools = await client.list_tools()
        edit_tool = next(t for t in tools if t.name == "edit_tasks")
        schema_json = __import__("json").dumps(edit_tool.inputSchema)

        # Schema should be substantial
        assert len(schema_json) > 500, f"Schema too small ({len(schema_json)} chars)"

        # Key fields present (camelCase)
        for field in (
            "id",
            "name",
            "dueDate",
            "flagged",
            "estimatedMinutes",
            "repetitionRule",
            "actions",
        ):
            assert field in schema_json, f"Missing field '{field}' in edit_tasks inputSchema"

        # WRIT-03: No snake_case leakage in property names
        schema = edit_tool.inputSchema
        property_keys = set(_extract_all_property_keys(schema))
        for snake in ("due_date", "defer_date", "estimated_minutes", "planned_date"):
            assert snake not in property_keys, (
                f"snake_case property '{snake}' leaked into edit_tasks inputSchema"
            )


# ---------------------------------------------------------------------------
# WRIT-11: Canary — middleware catches ValidationError from call_next()
# ---------------------------------------------------------------------------


class TestCanaryMiddleware:
    """Guard against FastMCP moving validation outside the middleware chain."""

    async def test_canary_middleware_catches_validation_error(self, client: Any) -> None:
        """Guard: FastMCP validation must happen inside call_next() so middleware can catch it.

        This test verifies that ValidationReformatterMiddleware catches ValidationError
        raised by FastMCP's internal type_adapter.validate_python() during tool dispatch.
        If this test fails after a FastMCP upgrade, it means validation moved BEFORE the
        middleware chain -- the middleware architecture needs rethinking.

        What to do if this fails:
        1. Check FastMCP changelog for validation pipeline changes
        2. The middleware approach may no longer work -- validation errors will bypass it
        3. Options: move validation back to handlers, or hook into FastMCP's new pipeline
        """
        with pytest.raises(ToolError) as exc_info:
            await client.call_tool("add_tasks", {"items": [{"bogus": "field"}]})

        error_msg = str(exc_info.value)
        # Middleware reformatted the error with "Task N:" prefix
        assert "Task 1:" in error_msg, (
            f"Expected 'Task 1:' prefix from middleware formatting, got: {error_msg}"
        )
        # No raw Pydantic internals leaking
        assert "validation error" not in error_msg.lower(), (
            f"Raw Pydantic 'validation error' leaked through middleware: {error_msg}"
        )
        assert "ValidationError" not in error_msg, (
            f"Raw Pydantic 'ValidationError' leaked through middleware: {error_msg}"
        )


# ---------------------------------------------------------------------------
# LIST: list_tasks, list_projects, list_tags, list_folders, list_perspectives
# ---------------------------------------------------------------------------

_LIST_SEED_DATA: dict[str, Any] = {
    "tasks": [
        make_task_dict(id="t-flagged", name="Flagged Task", flagged=True),
        make_task_dict(id="t-normal", name="Normal Task", flagged=False),
    ],
    "projects": [
        make_project_dict(id="proj-alpha", name="Alpha Project"),
        make_project_dict(id="proj-beta", name="Beta Project"),
    ],
    "tags": [
        make_tag_dict(id="tag-active", name="Active Tag", status="Active"),
        make_tag_dict(id="tag-hold", name="Hold Tag", status="OnHold"),
    ],
    "folders": [
        make_folder_dict(id="fold-1", name="Work Folder"),
    ],
    "perspectives": [
        make_perspective_dict(id="persp-inbox", name="Inbox"),
        make_perspective_dict(id="persp-forecast", name="Forecast"),
    ],
}


@pytest.mark.snapshot(**_LIST_SEED_DATA)
class TestListTasks:
    """Integration tests for the list_tasks MCP tool."""

    async def test_list_tasks_returns_structured_content(self, client: Any) -> None:
        result = await client.call_tool("list_tasks", {"query": {}})
        assert result.structured_content is not None
        sc = result.structured_content
        assert "items" in sc
        assert "total" in sc
        assert "hasMore" in sc
        assert isinstance(sc["items"], list)

    async def test_list_tasks_golden_path_flagged_filter(self, client: Any) -> None:
        result = await client.call_tool("list_tasks", {"query": {"flagged": True}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        assert all(item["flagged"] is True for item in items)

    async def test_list_tasks_has_read_only_annotation(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "list_tasks")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True

    async def test_list_tasks_response_uses_camelcase(self, client: Any) -> None:
        result = await client.call_tool("list_tasks", {"query": {}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        task = items[0]
        # camelCase keys expected (use fields that have non-default values)
        assert "hasChildren" in task or "availability" in task
        # snake_case keys must NOT be present
        assert "has_children" not in task
        assert "due_date" not in task

    async def test_list_tasks_invalid_availability_returns_tool_error(self, client: Any) -> None:
        with pytest.raises(ToolError):
            await client.call_tool("list_tasks", {"query": {"availability": ["invalid_value"]}})


@pytest.mark.snapshot(**_LIST_SEED_DATA)
class TestListProjects:
    """Integration tests for the list_projects MCP tool."""

    async def test_list_projects_returns_structured_content(self, client: Any) -> None:
        result = await client.call_tool("list_projects", {"query": {}})
        sc = result.structured_content
        assert sc is not None
        assert "items" in sc
        assert "total" in sc
        assert "hasMore" in sc

    async def test_list_projects_golden_path_search(self, client: Any) -> None:
        result = await client.call_tool("list_projects", {"query": {"search": "Alpha"}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        assert any("Alpha" in item["name"] for item in items)

    async def test_list_projects_has_read_only_annotation(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "list_projects")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True


@pytest.mark.snapshot(**_LIST_SEED_DATA)
class TestListTags:
    """Integration tests for the list_tags MCP tool."""

    async def test_list_tags_returns_structured_content(self, client: Any) -> None:
        result = await client.call_tool("list_tags", {"query": {}})
        sc = result.structured_content
        assert sc is not None
        assert "items" in sc
        assert "total" in sc
        assert "hasMore" in sc

    async def test_list_tags_golden_path_search(self, client: Any) -> None:
        result = await client.call_tool("list_tags", {"query": {"search": "Active"}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        assert any("Active" in item["name"] for item in items)

    async def test_list_tags_has_read_only_annotation(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "list_tags")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True


@pytest.mark.snapshot(**_LIST_SEED_DATA)
class TestListFolders:
    """Integration tests for the list_folders MCP tool."""

    async def test_list_folders_returns_structured_content(self, client: Any) -> None:
        result = await client.call_tool("list_folders", {"query": {}})
        sc = result.structured_content
        assert sc is not None
        assert "items" in sc
        assert "total" in sc
        assert "hasMore" in sc

    async def test_list_folders_golden_path_search(self, client: Any) -> None:
        result = await client.call_tool("list_folders", {"query": {"search": "Work"}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        assert any("Work" in item["name"] for item in items)

    async def test_list_folders_has_read_only_annotation(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "list_folders")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True


@pytest.mark.snapshot(**_LIST_SEED_DATA)
class TestListPerspectives:
    """Integration tests for the list_perspectives MCP tool."""

    async def test_list_perspectives_returns_structured_content(self, client: Any) -> None:
        result = await client.call_tool("list_perspectives", {"query": {}})
        sc = result.structured_content
        assert sc is not None
        assert "items" in sc
        assert "total" in sc
        assert "hasMore" in sc

    async def test_list_perspectives_golden_path_search(self, client: Any) -> None:
        result = await client.call_tool("list_perspectives", {"query": {"search": "Forecast"}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        assert any("Forecast" in item["name"] for item in items)

    async def test_list_perspectives_has_read_only_annotation(self, client: Any) -> None:
        tools = await client.list_tools()
        tool = next(t for t in tools if t.name == "list_perspectives")
        assert tool.annotations is not None
        assert tool.annotations.readOnlyHint is True
        assert tool.annotations.idempotentHint is True


# ---------------------------------------------------------------------------
# SHAPING: Response stripping and field selection integration tests
# ---------------------------------------------------------------------------


@pytest.mark.snapshot(**_LIST_SEED_DATA)
class TestResponseShaping:
    """Integration tests for response stripping and field selection (D-03, D-09)."""

    async def test_get_task_strips_null_fields(self, client: Any) -> None:
        """get_task returns stripped entity — null/false/empty values absent."""
        result = await client.call_tool("get_task", {"id": "t-normal"})
        sc = result.structured_content
        assert sc is not None
        # Normal task has flagged=False, dueDate=None — both stripped
        assert "dueDate" not in sc
        assert "flagged" not in sc
        # But id and name are always present
        assert sc["id"] == "t-normal"
        assert sc["name"] == "Normal Task"

    async def test_get_all_strips_entities(self, client: Any) -> None:
        """get_all strips null/false/empty from each entity in collections."""
        result = await client.call_tool("get_all")
        sc = result.structured_content
        assert sc is not None
        tasks = sc["tasks"]
        assert len(tasks) >= 1
        normal = next(t for t in tasks if t["id"] == "t-normal")
        # Stripped: flagged=False, dueDate=None, tags=[], note=""
        assert "dueDate" not in normal
        assert "flagged" not in normal

    async def test_list_tasks_strips_items(self, client: Any) -> None:
        """list_tasks strips null/false/empty from each item."""
        result = await client.call_tool("list_tasks", {"query": {}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        normal = next(i for i in items if i["id"] == "t-normal")
        assert "dueDate" not in normal
        assert "flagged" not in normal

    async def test_list_tasks_with_include_notes(self, client: Any) -> None:
        """list_tasks with include=['notes'] returns note field (when set)."""
        result = await client.call_tool("list_tasks", {"query": {"include": ["notes"]}})
        sc = result.structured_content
        assert sc is not None
        # items exist and have envelope structure
        assert "items" in sc
        assert "total" in sc
        assert "hasMore" in sc

    async def test_list_tasks_with_only_returns_selected_fields(self, client: Any) -> None:
        """list_tasks with only=['name'] returns only id and name."""
        result = await client.call_tool("list_tasks", {"query": {"only": ["name"]}})
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        for item in items:
            # id is always included; name was requested
            assert "id" in item
            assert "name" in item
            # No other fields should be present
            non_id_name = {k for k in item if k not in ("id", "name")}
            assert not non_id_name, f"Unexpected fields with only=['name']: {non_id_name}"

    async def test_list_tasks_with_include_star_returns_all_fields(self, client: Any) -> None:
        """list_tasks with include=['*'] returns all fields (stripped)."""
        result = await client.call_tool(
            "list_tasks", {"query": {"include": ["*"], "flagged": True}}
        )
        sc = result.structured_content
        assert sc is not None
        items = sc["items"]
        assert len(items) >= 1
        flagged = items[0]
        # With *, all field groups are included — flagged task should have flagged=True
        assert flagged["flagged"] is True

    async def test_list_tasks_invalid_include_returns_error(self, client: Any) -> None:
        """list_tasks with invalid include group produces validation error."""
        with pytest.raises(ToolError, match="Unknown field group"):
            await client.call_tool("list_tasks", {"query": {"include": ["bogus"]}})

    async def test_list_tags_strips_items(self, client: Any) -> None:
        """list_tags strips null/false/empty from each item."""
        result = await client.call_tool("list_tags", {"query": {}})
        sc = result.structured_content
        assert sc is not None
        assert "items" in sc
        assert "total" in sc
        for item in sc["items"]:
            assert "id" in item
            assert "name" in item

    async def test_add_tasks_returns_unmodified(self, client: Any) -> None:
        """add_tasks returns result as-is — no stripping applied to write results."""
        result = await client.call_tool("add_tasks", {"items": [{"name": "Test Shaping"}]})
        sc = result.structured_content
        assert sc is not None
        # Write results are wrapped in {"result": [...]}
        items = sc["result"]
        assert len(items) == 1
        item = items[0]
        assert item["status"] == "success"
        assert "id" in item
        assert "name" in item

    async def test_list_tasks_limit_zero_returns_count_only(self, client: Any) -> None:
        """limit: 0 returns empty items with total count (COUNT-01)."""
        result = await client.call_tool("list_tasks", {"query": {"limit": 0}})
        sc = result.structured_content
        assert sc is not None
        assert sc["items"] == []
        assert isinstance(sc["total"], int)
        assert sc["total"] == 2  # seed data has 2 tasks
        assert sc["hasMore"] is True  # total > 0 means hasMore is True
        # No entity fields should leak into the response envelope
        assert set(sc.keys()) <= {"items", "total", "hasMore", "warnings"}

    async def test_list_projects_limit_zero_returns_count_only(self, client: Any) -> None:
        """limit: 0 on list_projects returns empty items with total count."""
        result = await client.call_tool("list_projects", {"query": {"limit": 0}})
        sc = result.structured_content
        assert sc is not None
        assert sc["items"] == []
        assert isinstance(sc["total"], int)
        assert sc["total"] == 2  # seed data has 2 projects
        assert sc["hasMore"] is True


# ---------------------------------------------------------------------------
# BATCH-ADD: add_tasks batch processing (best-effort semantics)
# ---------------------------------------------------------------------------


class TestAddTasksBatch:
    """Verify add_tasks batch processing: best-effort semantics, per-item errors, limits."""

    # -- All succeed (best-effort) --

    async def test_batch_all_succeed(self, client: Any) -> None:
        """Submitting 2 items both succeeds — best-effort processes all items."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Task A"}, {"name": "Task B"}]},
        )
        items = result.structured_content["result"]
        assert len(items) == 2
        assert items[0]["status"] == "success"
        assert items[1]["status"] == "success"

    async def test_batch_three_items_all_succeed(self, client: Any) -> None:
        """Submitting 3 items all succeed when all are valid."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "A"}, {"name": "B"}, {"name": "C"}]},
        )
        items = result.structured_content["result"]
        assert len(items) == 3
        assert all(item["status"] == "success" for item in items)

    # -- Mixed failures (best-effort: item 2 fails but item 3 still processed) --

    async def test_batch_middle_item_fails_others_still_processed(self, client: Any) -> None:
        """3 items where item 2 fails: [success, error, success] — best-effort continues."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Good Task 1"},
                    {"name": "Bad Task", "parent": "nonexistent-parent-id"},
                    {"name": "Good Task 3"},
                ]
            },
        )
        items = result.structured_content["result"]
        assert len(items) == 3
        assert items[0]["status"] == "success"
        assert items[1]["status"] == "error"
        assert items[2]["status"] == "success"  # best-effort: item 3 still processed

    async def test_batch_first_item_fails_rest_still_processed(self, client: Any) -> None:
        """Item 1 fails: [error, success, success] — best-effort continues from item 2."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Bad Task", "parent": "nonexistent-parent-id"},
                    {"name": "Good Task 2"},
                    {"name": "Good Task 3"},
                ]
            },
        )
        items = result.structured_content["result"]
        assert len(items) == 3
        assert items[0]["status"] == "error"
        assert items[1]["status"] == "success"
        assert items[2]["status"] == "success"

    async def test_batch_all_fail(self, client: Any) -> None:
        """All items fail: [error, error] — each gets its own error."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Bad 1", "parent": "nonexistent-id-1"},
                    {"name": "Bad 2", "parent": "nonexistent-id-2"},
                ]
            },
        )
        items = result.structured_content["result"]
        assert len(items) == 2
        assert items[0]["status"] == "error"
        assert items[1]["status"] == "error"

    # -- Error message format (BATCH-06) --

    async def test_batch_error_has_task_n_prefix(self, client: Any) -> None:
        """Error items have 'Task N:' prefix in error string (1-indexed)."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Good Task"},
                    {"name": "Bad Task", "parent": "nonexistent-id"},
                    {"name": "Another Bad", "parent": "also-nonexistent"},
                ]
            },
        )
        items = result.structured_content["result"]
        # Item 2 fails -> "Task 2: ..."
        assert items[1]["error"].startswith("Task 2:")
        # Item 3 fails -> "Task 3: ..."
        assert items[2]["error"].startswith("Task 3:")

    async def test_batch_first_item_error_has_task_1_prefix(self, client: Any) -> None:
        """First item error has 'Task 1:' prefix."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Bad", "parent": "nonexistent-id"},
                ]
            },
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "error"
        assert items[0]["error"].startswith("Task 1:")

    # -- Field presence by status (BATCH-05) --

    async def test_batch_success_item_has_id_and_name(self, client: Any) -> None:
        """Success items have non-empty id and name populated."""
        result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Has Fields"}]},
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "success"
        assert items[0].get("id") is not None
        assert items[0]["id"] != ""
        assert items[0].get("name") is not None
        assert items[0]["name"] != ""

    async def test_batch_error_item_has_no_id_or_name(self, client: Any) -> None:
        """Error items have id=None and name=None (no OmniFocus ID for failed creates)."""
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Bad Task", "parent": "nonexistent-id"},
                ]
            },
        )
        items = result.structured_content["result"]
        assert items[0]["status"] == "error"
        # id and name should be absent or None for failed creates
        assert items[0].get("id") is None
        assert items[0].get("name") is None

    async def test_batch_success_with_warnings(self, client: Any) -> None:
        """Success items can have warnings (e.g. anchor date missing)."""
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
        assert items[0]["status"] == "success"
        assert items[0].get("warnings") is not None
        assert len(items[0]["warnings"]) > 0

    # -- Batch size limits (BATCH-01, BATCH-02) --

    async def test_batch_50_items_accepted(self, client: Any) -> None:
        """50 items accepted — no validation error at max batch size."""
        items_payload = [{"name": f"Task {i}"} for i in range(50)]
        result = await client.call_tool("add_tasks", {"items": items_payload})
        result_items = result.structured_content["result"]
        assert len(result_items) == 50

    async def test_batch_51_items_rejected_at_schema_level(self, client: Any) -> None:
        """51 items rejected with ToolError — schema-level maxItems enforcement."""
        items_payload = [{"name": f"Task {i}"} for i in range(51)]
        with pytest.raises(ToolError):
            await client.call_tool("add_tasks", {"items": items_payload})

    async def test_batch_0_items_rejected_at_schema_level(self, client: Any) -> None:
        """0 items rejected with ToolError — schema-level minItems enforcement."""
        with pytest.raises(ToolError):
            await client.call_tool("add_tasks", {"items": []})


# ---------------------------------------------------------------------------
# BATCH-EDIT: edit_tasks batch processing (fail-fast semantics)
# ---------------------------------------------------------------------------


class TestEditTasksBatch:
    """Verify edit_tasks batch processing: fail-fast semantics, skip messages, limits."""

    # -- All succeed --

    async def test_batch_all_succeed(self, client: Any) -> None:
        """Submitting 2 items both succeed — both processed sequentially."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Edit Me 1"}, {"name": "Edit Me 2"}]},
        )
        id1 = add_result.structured_content["result"][0]["id"]
        id2 = add_result.structured_content["result"][1]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {"items": [{"id": id1, "name": "Edited 1"}, {"id": id2, "name": "Edited 2"}]},
        )
        items = edit_result.structured_content["result"]
        assert len(items) == 2
        assert items[0]["status"] == "success"
        assert items[1]["status"] == "success"

    # -- Fail-fast: item 1 fails -> items 2 and 3 skipped --

    async def test_batch_first_item_fails_rest_skipped(self, client: Any) -> None:
        """3 items where item 1 fails: [error, skipped, skipped] — fail-fast."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Valid Task 1"}, {"name": "Valid Task 2"}]},
        )
        id1 = add_result.structured_content["result"][0]["id"]
        id2 = add_result.structured_content["result"][1]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": "nonexistent-bad-id", "name": "Fail"},
                    {"id": id1, "name": "Should be skipped"},
                    {"id": id2, "name": "Also skipped"},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert len(items) == 3
        assert items[0]["status"] == "error"
        assert items[1]["status"] == "skipped"
        assert items[2]["status"] == "skipped"

    # -- Fail-fast: item 2 fails -> item 3 skipped but item 1 succeeds --

    async def test_batch_middle_item_fails_later_items_skipped(self, client: Any) -> None:
        """3 items where item 2 fails: [success, error, skipped]."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Valid 1"}, {"name": "Valid 3"}]},
        )
        id1 = add_result.structured_content["result"][0]["id"]
        id3 = add_result.structured_content["result"][1]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": id1, "name": "Updated 1"},
                    {"id": "nonexistent-bad-id", "name": "Will fail"},
                    {"id": id3, "name": "Should be skipped"},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert len(items) == 3
        assert items[0]["status"] == "success"
        assert items[1]["status"] == "error"
        assert items[2]["status"] == "skipped"

    # -- Skip message references the failing item index (BATCH-07) --

    async def test_batch_skipped_items_reference_failing_item(self, client: Any) -> None:
        """Skipped items have warnings containing 'Skipped: task N failed' (1-indexed N)."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Will be skipped"}, {"name": "Also skipped"}]},
        )
        id1 = add_result.structured_content["result"][0]["id"]
        id2 = add_result.structured_content["result"][1]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": "nonexistent-fail", "name": "Fail"},  # item 1 fails
                    {"id": id1, "name": "Skipped"},
                    {"id": id2, "name": "Also skipped"},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        # Both skipped items reference item 1 as the failing item
        assert items[1]["status"] == "skipped"
        assert items[1]["warnings"] is not None
        assert any("Skipped: task 1 failed" in w for w in items[1]["warnings"])
        assert items[2]["status"] == "skipped"
        assert any("Skipped: task 1 failed" in w for w in items[2]["warnings"])

    async def test_batch_skipped_items_reference_second_failing_item(self, client: Any) -> None:
        """When item 2 fails, skipped item 3 references 'task 2 failed'."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "First"}, {"name": "Third"}]},
        )
        id1 = add_result.structured_content["result"][0]["id"]
        id3 = add_result.structured_content["result"][1]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": id1, "name": "Succeeds"},
                    {"id": "nonexistent-fail", "name": "Fails"},  # item 2 fails
                    {"id": id3, "name": "Skipped"},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[2]["status"] == "skipped"
        assert items[2]["warnings"] is not None
        assert any("Skipped: task 2 failed" in w for w in items[2]["warnings"])

    # -- Field presence by status (BATCH-05 for edit) --

    async def test_batch_skipped_item_has_id_from_command(self, client: Any) -> None:
        """Skipped items have id populated from the command input."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Will be skipped"}]},
        )
        task_id = add_result.structured_content["result"][0]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": "nonexistent-fail", "name": "Fail"},
                    {"id": task_id, "name": "Skipped"},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[1]["status"] == "skipped"
        assert items[1].get("id") == task_id  # id from command input

    async def test_batch_skipped_item_has_no_name(self, client: Any) -> None:
        """Skipped items have name=None — never processed by service."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Will be skipped"}]},
        )
        task_id = add_result.structured_content["result"][0]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": "nonexistent-fail", "name": "Fail"},
                    {"id": task_id, "name": "Skipped"},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[1]["status"] == "skipped"
        assert items[1].get("name") is None

    async def test_batch_error_item_has_id_from_command(self, client: Any) -> None:
        """Error items (fail-fast) have id populated from the command input."""
        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": "nonexistent-task-id", "name": "Fail"},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[0]["status"] == "error"
        assert items[0].get("id") == "nonexistent-task-id"

    async def test_batch_error_item_has_task_n_prefix(self, client: Any) -> None:
        """Error items have 'Task N:' prefix in error string (1-indexed)."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Valid"}]},
        )
        id1 = add_result.structured_content["result"][0]["id"]

        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": id1, "name": "Succeeds"},
                    {"id": "nonexistent-fail", "name": "Fails"},  # item 2 fails
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert items[1]["status"] == "error"
        assert items[1]["error"].startswith("Task 2:")

    # -- Same-task edits (BATCH-08): sequential processing --

    async def test_batch_same_task_edits_both_succeed(self, client: Any) -> None:
        """Two edits to the same task ID both succeed (sequential processing)."""
        add_result = await client.call_tool(
            "add_tasks",
            {"items": [{"name": "Original"}]},
        )
        task_id = add_result.structured_content["result"][0]["id"]

        # Two edits to the same task: first sets name, second sets flagged
        edit_result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": task_id, "name": "After First Edit"},
                    {"id": task_id, "flagged": True},
                ]
            },
        )
        items = edit_result.structured_content["result"]
        assert len(items) == 2
        assert items[0]["status"] == "success"
        assert items[1]["status"] == "success"

        # Both edits took effect — name changed and flagged set
        get_result = await client.call_tool("get_task", {"id": task_id})
        assert get_result.structured_content["name"] == "After First Edit"
        assert get_result.structured_content["flagged"] is True

    # -- Batch size limits (BATCH-01, BATCH-02) --

    async def test_batch_50_items_accepted(self, client: Any) -> None:
        """50 items accepted — no validation error at max batch size.

        Items may fail individually (bad IDs) but the batch itself is not rejected.
        """
        items_payload = [{"id": f"task-{i}", "name": f"Edit {i}"} for i in range(50)]
        # These IDs don't exist in InMemoryBridge — each will return error status
        # but the batch size limit is not triggered.
        result = await client.call_tool("edit_tasks", {"items": items_payload})
        result_items = result.structured_content["result"]
        # 50 items returned: first is error, rest are skipped (fail-fast from first failure)
        assert len(result_items) == 50

    async def test_batch_51_items_rejected_at_schema_level(self, client: Any) -> None:
        """51 items rejected with ToolError — schema-level maxItems enforcement."""
        items_payload = [{"id": f"task-{i}", "name": f"Edit {i}"} for i in range(51)]
        with pytest.raises(ToolError):
            await client.call_tool("edit_tasks", {"items": items_payload})

    async def test_batch_0_items_rejected_at_schema_level(self, client: Any) -> None:
        """0 items rejected with ToolError — schema-level minItems enforcement."""
        with pytest.raises(ToolError):
            await client.call_tool("edit_tasks", {"items": []})
