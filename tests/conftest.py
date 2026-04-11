"""Shared test fixtures and factory functions.

Two sets of factories:
- ``make_task_dict()`` etc. return **raw bridge format** (matching bridge.js output).
  Used for seeding InMemoryBridge and most tests.
- ``make_model_task_dict()`` etc. return **model format** (after adapter transformation).
  Used for Pydantic model validation tests.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

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
    # Auto-sync effectiveFlagged from flagged when not explicitly overridden
    if "flagged" in overrides and "effectiveFlagged" not in overrides:
        overrides["effectiveFlagged"] = overrides["flagged"]
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
    # Auto-sync effectiveFlagged from flagged when not explicitly overridden
    if "flagged" in overrides and "effectiveFlagged" not in overrides:
        overrides["effectiveFlagged"] = overrides["flagged"]
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

    Returns a complete task dict with all model fields.
    Uses tagged parent field: {"project": {id, name}} or {"task": {id, name}}.
    Includes required project field: {id, name} (containing project at any depth).
    Default is an inbox task (parent and project both point to $inbox).
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
        # Relationships
        "repetitionRule": None,
        "parent": {"project": {"id": "$inbox", "name": "Inbox"}},
        "project": {"id": "$inbox", "name": "Inbox"},
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
# Settings cache reset -- ensures monkeypatched env vars take effect
# ---------------------------------------------------------------------------


@pytest.fixture(autouse=True)
def _reset_settings_cache() -> None:
    """Reset the Settings singleton before every test.

    Tests that monkeypatch OPERATOR_* env vars need the cached Settings
    instance to be cleared so pydantic-settings re-reads the environment.
    """
    from omnifocus_operator.config import reset_settings  # noqa: PLC0415

    reset_settings()


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
    with ``tests.doubles``.  Actual types: ``InMemoryBridge`` -> ``BridgeOnlyRepository``.
    """
    from omnifocus_operator.repository import BridgeOnlyRepository  # noqa: PLC0415
    from tests.doubles import ConstantMtimeSource  # noqa: PLC0415 — circular import guard

    return BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())


@pytest.fixture
def service(repo: Any, bridge: Any) -> Any:
    """OperatorService wired to test repo and preferences.

    Note: Return type is ``Any`` to avoid importing ``OperatorService`` at
    module level (keeping conftest lightweight).  Actual return: ``OperatorService``.
    """
    from omnifocus_operator.service import OperatorService  # noqa: PLC0415
    from omnifocus_operator.service.preferences import OmniFocusPreferences  # noqa: PLC0415

    preferences = OmniFocusPreferences(bridge)
    return OperatorService(repository=repo, preferences=preferences)


@pytest.fixture
def server(service: Any) -> Any:
    """FastMCP server with patched lifespan injecting the test service.

    Chain: @pytest.mark.snapshot(...) -> bridge -> repo -> service -> server

    Note: Return type is ``Any`` to avoid importing ``FastMCP`` at module
    level.  Actual return: ``FastMCP``.
    """
    import logging  # noqa: PLC0415
    from contextlib import asynccontextmanager  # noqa: PLC0415

    from fastmcp import FastMCP  # noqa: PLC0415

    from omnifocus_operator.middleware import (  # noqa: PLC0415
        ToolLoggingMiddleware,
        ValidationReformatterMiddleware,
    )
    from omnifocus_operator.server import _register_tools  # noqa: PLC0415

    @asynccontextmanager
    async def _patched_lifespan(app: Any) -> Any:
        yield {"service": service}

    srv = FastMCP("omnifocus-operator", lifespan=_patched_lifespan)
    _register_tools(srv)
    srv.add_middleware(ValidationReformatterMiddleware())
    srv.add_middleware(ToolLoggingMiddleware(logging.getLogger("omnifocus_operator.server")))
    return srv


@pytest.fixture
async def client(server: Any) -> AsyncIterator[Any]:
    """FastMCP Client connected to the test server.

    Chain: @pytest.mark.snapshot(...) -> bridge -> repo -> service -> server -> client
    """
    from fastmcp import Client  # noqa: PLC0415

    async with Client(server) as c:
        yield c
