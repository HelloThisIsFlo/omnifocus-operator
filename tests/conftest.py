"""Shared test fixtures and factory functions.

Two sets of factories:
- ``make_task_dict()`` etc. return **raw bridge format** (matching bridge.js output).
  Used for seeding InMemoryBridge and most tests.
- ``make_model_task_dict()`` etc. return **model format** (after adapter transformation).
  Used for Pydantic model validation tests.
"""

from __future__ import annotations

from typing import Any

import pytest

from omnifocus_operator.models.snapshot import AllEntities

# ---------------------------------------------------------------------------
# Raw bridge format factories (match bridge.js output shape)
# ---------------------------------------------------------------------------


def make_task_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for raw bridge-format task dict (camelCase keys).

    Returns a complete task dict with all 26 bridge fields.
    Uses flat parent/project string IDs (matching bridge.js output).
    """
    defaults: dict[str, Any] = {
        # Identity (3)
        "id": "task-001",
        "name": "Test Task",
        "url": "omnifocus:///task/task-001",
        "note": "",
        # Lifecycle (2)
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        # Status -- single PascalCase string (1)
        "status": "Available",
        # Flags (2)
        "flagged": False,
        "effectiveFlagged": False,
        # Dates (10)
        "dueDate": None,
        "deferDate": None,
        "effectiveDueDate": None,
        "effectiveDeferDate": None,
        "completionDate": None,
        "effectiveCompletionDate": None,
        "plannedDate": None,
        "effectivePlannedDate": None,
        "dropDate": None,
        "effectiveDropDate": None,
        # Metadata (2)
        "estimatedMinutes": None,
        "hasChildren": False,
        # Relationships (4)
        "inInbox": True,
        "repetitionRule": None,
        "project": None,
        "parent": None,
        # Tags -- list of TagRef objects {id, name}
        "tags": [],
    }
    return {**defaults, **overrides}


def make_project_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for raw bridge-format project dict (camelCase keys).

    Returns a complete project dict with all 29 bridge fields.
    """
    defaults: dict[str, Any] = {
        # Identity (3) + lifecycle
        "id": "proj-001",
        "name": "Test Project",
        "url": "omnifocus:///project/proj-001",
        "note": "",
        # Status -- two separate PascalCase strings (2)
        "status": "Active",
        "taskStatus": "Available",
        # Lifecycle fields
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        # Completion dates (2)
        "completionDate": None,
        "effectiveCompletionDate": None,
        # Flags (2)
        "flagged": False,
        "effectiveFlagged": False,
        # Dates (8)
        "dueDate": None,
        "deferDate": None,
        "effectiveDueDate": None,
        "effectiveDeferDate": None,
        "plannedDate": None,
        "effectivePlannedDate": None,
        "dropDate": None,
        "effectiveDropDate": None,
        # Metadata (2)
        "estimatedMinutes": None,
        "hasChildren": True,
        # Repetition (1)
        "repetitionRule": None,
        # Review (3)
        "lastReviewDate": "2024-01-10T10:00:00.000Z",
        "nextReviewDate": "2024-01-17T10:00:00.000Z",
        "reviewInterval": {"steps": 7, "unit": "days"},
        # Relationships (3)
        "nextTask": None,
        "folder": None,
        # Tags -- list of TagRef objects {id, name}
        "tags": [],
    }
    return {**defaults, **overrides}


def make_tag_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for raw bridge-format tag dict (camelCase keys).

    Returns a complete tag dict with all 8 bridge fields.
    """
    defaults: dict[str, Any] = {
        "id": "tag-001",
        "name": "Test Tag",
        "url": "omnifocus:///tag/tag-001",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "status": "Active",
        "childrenAreMutuallyExclusive": False,
        "parent": None,
    }
    return {**defaults, **overrides}


def make_folder_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for raw bridge-format folder dict (camelCase keys).

    Returns a complete folder dict with all 7 bridge fields.
    """
    defaults: dict[str, Any] = {
        "id": "folder-001",
        "name": "Test Folder",
        "url": "omnifocus:///folder/folder-001",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "status": "Active",
        "parent": None,
    }
    return {**defaults, **overrides}


def make_perspective_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format perspective JSON (camelCase keys).

    Returns a complete perspective dict with all 2 bridge fields.
    (builtin is a computed field in Python, not sent from bridge.)
    """
    defaults: dict[str, Any] = {
        "id": "persp-001",
        "name": "Test Perspective",
    }
    return {**defaults, **overrides}


def make_snapshot_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for raw bridge-format snapshot dict (camelCase keys).

    Returns a complete entity dict with 1 of each entity type by default.
    Override individual collections or use empty lists.
    """
    defaults: dict[str, Any] = {
        "tasks": [make_task_dict()],
        "projects": [make_project_dict()],
        "tags": [make_tag_dict()],
        "folders": [make_folder_dict()],
        "perspectives": [make_perspective_dict()],
    }
    return {**defaults, **overrides}


# ---------------------------------------------------------------------------
# Model format factories (after adapter transformation)
# ---------------------------------------------------------------------------


def make_model_task_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for model-format task dict (camelCase keys).

    Returns a complete task dict with all 26 model fields.
    Uses unified parent field: None (inbox) or {type, id, name} (ParentRef).
    """
    defaults: dict[str, Any] = {
        # Identity (3)
        "id": "task-001",
        "name": "Test Task",
        "url": "omnifocus:///task/task-001",
        "note": "",
        # Lifecycle (2)
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        # Two-axis status (2)
        "urgency": "none",
        "availability": "available",
        # Flags (2)
        "flagged": False,
        "effectiveFlagged": False,
        # Dates (10)
        "dueDate": None,
        "deferDate": None,
        "effectiveDueDate": None,
        "effectiveDeferDate": None,
        "completionDate": None,
        "effectiveCompletionDate": None,
        "plannedDate": None,
        "effectivePlannedDate": None,
        "dropDate": None,
        "effectiveDropDate": None,
        # Metadata (2)
        "estimatedMinutes": None,
        "hasChildren": False,
        # Relationships (3)
        "inInbox": True,
        "repetitionRule": None,
        "parent": None,
        # Tags -- list of TagRef objects {id, name}
        "tags": [],
    }
    return {**defaults, **overrides}


def make_model_project_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for model-format project dict (camelCase keys).

    Returns a complete project dict with all 28 model fields.
    (Project does NOT have effectiveCompletionDate -- that's Task-only.)
    """
    defaults: dict[str, Any] = {
        # Identity (3) + lifecycle from OmniFocusEntity
        "id": "proj-001",
        "name": "Test Project",
        "url": "omnifocus:///project/proj-001",
        "note": "",
        # Lifecycle fields
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        # Two-axis status (2)
        "urgency": "none",
        "availability": "available",
        # Completion date (1 -- effectiveCompletionDate is Task-only)
        "completionDate": None,
        # Flags (2)
        "flagged": False,
        "effectiveFlagged": False,
        # Dates (8)
        "dueDate": None,
        "deferDate": None,
        "effectiveDueDate": None,
        "effectiveDeferDate": None,
        "plannedDate": None,
        "effectivePlannedDate": None,
        "dropDate": None,
        "effectiveDropDate": None,
        # Metadata (2)
        "estimatedMinutes": None,
        "hasChildren": True,
        # Repetition (1)
        "repetitionRule": None,
        # Review (3)
        "lastReviewDate": "2024-01-10T10:00:00.000Z",
        "nextReviewDate": "2024-01-17T10:00:00.000Z",
        "reviewInterval": {"steps": 7, "unit": "days"},
        # Relationships (3)
        "nextTask": None,
        "folder": None,
        # Tags -- list of TagRef objects {id, name}
        "tags": [],
    }
    return {**defaults, **overrides}


def make_model_tag_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for model-format tag dict (camelCase keys).

    Returns a complete tag dict with all 8 model fields.
    """
    defaults: dict[str, Any] = {
        "id": "tag-001",
        "name": "Test Tag",
        "url": "omnifocus:///tag/tag-001",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "availability": "available",
        "childrenAreMutuallyExclusive": False,
        "parent": None,
    }
    return {**defaults, **overrides}


def make_model_folder_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for model-format folder dict (camelCase keys).

    Returns a complete folder dict with all 7 model fields.
    """
    defaults: dict[str, Any] = {
        "id": "folder-001",
        "name": "Test Folder",
        "url": "omnifocus:///folder/folder-001",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "availability": "available",
        "parent": None,
    }
    return {**defaults, **overrides}


def make_model_snapshot_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for model-format AllEntities dict (camelCase keys).

    Returns a complete entity dict with 1 of each entity type by default.
    Override individual collections or use empty lists.
    """
    defaults: dict[str, Any] = {
        "tasks": [make_model_task_dict()],
        "projects": [make_model_project_dict()],
        "tags": [make_model_tag_dict()],
        "folders": [make_model_folder_dict()],
        "perspectives": [make_perspective_dict()],
    }
    return {**defaults, **overrides}


def make_snapshot(**overrides: Any) -> AllEntities:
    """Factory for a validated ``AllEntities`` model instance.

    Delegates to ``make_model_snapshot_dict()`` and validates through Pydantic.
    """
    return AllEntities.model_validate(make_model_snapshot_dict(**overrides))


# ---------------------------------------------------------------------------
# Shared fixtures: marker-driven bridge -> repo -> service chain
# ---------------------------------------------------------------------------


@pytest.fixture
def bridge(request: pytest.FixtureRequest) -> Any:
    """InMemoryBridge seeded from @pytest.mark.snapshot(...) or default snapshot.

    Usage:
        @pytest.mark.snapshot(tasks=[make_task_dict(id="t1")])
        async def test_something(self, service): ...

    Without marker: uses make_snapshot_dict() defaults (1 of each entity).

    Note: Return type is ``Any`` because ``InMemoryBridge`` lives in
    ``tests.doubles`` which imports from this module -- using the concrete
    type in the signature would create a circular import at module load time.
    The actual return value is always ``InMemoryBridge``.
    """
    from tests.doubles import InMemoryBridge  # noqa: PLC0415 — circular import guard

    marker = request.node.get_closest_marker("snapshot")
    if marker is not None:
        snapshot_data = make_snapshot_dict(**marker.kwargs)
    else:
        snapshot_data = make_snapshot_dict()
    return InMemoryBridge(data=snapshot_data)


@pytest.fixture
def repo(bridge: Any) -> Any:
    """Repository wired to test bridge with constant mtime.

    Note: Parameter and return types are ``Any`` to avoid circular imports
    with ``tests.doubles``.  Actual types: ``InMemoryBridge`` -> ``BridgeRepository``.
    """
    from omnifocus_operator.repository import BridgeRepository  # noqa: PLC0415
    from tests.doubles import ConstantMtimeSource  # noqa: PLC0415 — circular import guard

    return BridgeRepository(bridge=bridge, mtime_source=ConstantMtimeSource())


@pytest.fixture
def service(repo: Any) -> Any:
    """OperatorService wired to test repo.

    Note: Return type is ``Any`` to avoid importing ``OperatorService`` at
    module level (keeping conftest lightweight).  Actual return: ``OperatorService``.
    """
    from omnifocus_operator.service import OperatorService  # noqa: PLC0415

    return OperatorService(repository=repo)


@pytest.fixture
def server(service: Any) -> Any:
    """FastMCP server with patched lifespan injecting the test service.

    Chain: @pytest.mark.snapshot(...) -> bridge -> repo -> service -> server

    Note: Return type is ``Any`` to avoid importing ``FastMCP`` at module
    level.  Actual return: ``FastMCP``.
    """
    from contextlib import asynccontextmanager  # noqa: PLC0415

    from mcp.server.fastmcp import FastMCP  # noqa: PLC0415

    from omnifocus_operator.server import _register_tools  # noqa: PLC0415

    @asynccontextmanager
    async def _patched_lifespan(app: Any) -> Any:
        yield {"service": service}

    srv = FastMCP("omnifocus-operator", lifespan=_patched_lifespan)
    _register_tools(srv)
    return srv


@pytest.fixture
def client_session(server: Any) -> Any:
    """Connected MCP ClientSession against the test server.

    Chain: ... -> server -> client_session

    Returns a ``_ClientSessionProxy`` that delegates ``call_tool`` and
    ``list_tools`` to a fresh in-memory MCP connection per call.  Each call
    spins up the server, connects a ``ClientSession``, performs the
    operation, then tears down cleanly -- all within a single
    ``anyio.create_task_group`` (no cross-task cancel-scope issues).

    State persists across calls because the underlying ``InMemoryBridge``
    (held by the ``service`` fixture) lives outside the connection lifecycle.
    """
    import anyio  # noqa: PLC0415
    from mcp.client.session import ClientSession  # noqa: PLC0415
    from mcp.shared.message import SessionMessage  # noqa: PLC0415

    class _ClientSessionProxy:
        """Lightweight proxy that delegates to a per-call MCP connection."""

        def __init__(self, srv: Any) -> None:
            self._server = srv

        async def _with_session(
            self,
            method: str,
            args: tuple[Any, ...],
            kwargs: dict[str, Any],
        ) -> Any:
            s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](0)
            c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](0)

            result: Any = None

            async with anyio.create_task_group() as tg:

                async def _run_server() -> None:
                    await self._server._mcp_server.run(
                        c2s_recv,
                        s2c_send,
                        self._server._mcp_server.create_initialization_options(),
                        raise_exceptions=True,
                    )

                tg.start_soon(_run_server)

                async with ClientSession(s2c_recv, c2s_send) as session:
                    await session.initialize()
                    result = await getattr(session, method)(*args, **kwargs)
                    tg.cancel_scope.cancel()

            return result

        async def call_tool(self, *args: Any, **kwargs: Any) -> Any:
            return await self._with_session("call_tool", args, kwargs)

        async def list_tools(self, *args: Any, **kwargs: Any) -> Any:
            return await self._with_session("list_tools", args, kwargs)

    return _ClientSessionProxy(server)
