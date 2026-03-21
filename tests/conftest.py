"""Shared test fixtures and factory functions for new-shape model dicts.

Factory functions return dicts with camelCase keys matching the new model shape
(after adapter transformation). These use the two-axis status model
(urgency + availability) and snake_case enum values.
"""

from __future__ import annotations

from typing import Any

import pytest

from omnifocus_operator.models.snapshot import AllEntities


def make_task_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for new-shape task dict (camelCase keys).

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


def make_project_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for new-shape project dict (camelCase keys).

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


def make_tag_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for new-shape tag dict (camelCase keys).

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


def make_folder_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for new-shape folder dict (camelCase keys).

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
    """Factory for new-shape AllEntities dict (camelCase keys).

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


def make_snapshot(**overrides: Any) -> AllEntities:
    """Factory for a validated ``AllEntities`` model instance.

    Delegates to ``make_snapshot_dict()`` and validates through Pydantic.
    """
    return AllEntities.model_validate(make_snapshot_dict(**overrides))


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
