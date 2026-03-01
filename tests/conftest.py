"""Shared test fixtures and factory functions for bridge-format JSON dicts.

Factory functions return dicts with camelCase keys matching the exact shape
produced by the bridge script (operatorBridgeScript.js). These are reused
across all test modules for model validation, parsing, and round-trip tests.
"""

from __future__ import annotations

from typing import Any


def make_task_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format task JSON (camelCase keys).

    Returns a complete task dict with all 32 bridge fields.
    """
    defaults: dict[str, Any] = {
        # Identity (3)
        "id": "task-001",
        "name": "Test Task",
        "note": "",
        # Lifecycle (5)
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "active": True,
        "effectiveActive": True,
        "status": "Available",
        # Completion (2)
        "completed": False,
        "completedByChildren": False,
        # Flags (3)
        "flagged": False,
        "effectiveFlagged": False,
        "sequential": False,
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
        # Metadata (3)
        "estimatedMinutes": None,
        "hasChildren": False,
        "shouldUseFloatingTimeZone": False,
        # Relationships (5)
        "inInbox": True,
        "repetitionRule": None,
        "project": None,
        "parent": None,
        "assignedContainer": None,
        "tags": [],
    }
    return {**defaults, **overrides}


def make_project_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format project JSON (camelCase keys).

    Returns a complete project dict with all 31 bridge fields.
    """
    defaults: dict[str, Any] = {
        # Identity (3)
        "id": "proj-001",
        "name": "Test Project",
        "note": "",
        # Status (2)
        "status": "Active",
        "taskStatus": "Available",
        # Completion (2)
        "completed": False,
        "completedByChildren": False,
        # Completion dates (2)
        "completionDate": None,
        "effectiveCompletionDate": None,
        # Flags (3)
        "flagged": False,
        "effectiveFlagged": False,
        "sequential": False,
        # Structure (1)
        "containsSingletonActions": False,
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
        # Time zone (1)
        "shouldUseFloatingTimeZone": False,
        # Repetition (1)
        "repetitionRule": None,
        # Review (3)
        "lastReviewDate": "2024-01-10T10:00:00.000Z",
        "nextReviewDate": "2024-01-17T10:00:00.000Z",
        "reviewInterval": {"steps": 7, "unit": "days"},
        # Relationships (3)
        "nextTask": None,
        "folder": None,
        "tags": [],
    }
    return {**defaults, **overrides}


def make_tag_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format tag JSON (camelCase keys).

    Returns a complete tag dict with all 9 bridge fields.
    """
    defaults: dict[str, Any] = {
        "id": "tag-001",
        "name": "Test Tag",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "active": True,
        "effectiveActive": True,
        "status": "Active",
        "allowsNextAction": True,
        "parent": None,
    }
    return {**defaults, **overrides}


def make_folder_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format folder JSON (camelCase keys).

    Returns a complete folder dict with all 8 bridge fields.
    """
    defaults: dict[str, Any] = {
        "id": "folder-001",
        "name": "Test Folder",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "active": True,
        "effectiveActive": True,
        "status": "Active",
        "parent": None,
    }
    return {**defaults, **overrides}


def make_perspective_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format perspective JSON (camelCase keys).

    Returns a complete perspective dict with all 3 bridge fields.
    """
    defaults: dict[str, Any] = {
        "id": "persp-001",
        "name": "Test Perspective",
        "builtin": False,
    }
    return {**defaults, **overrides}


def make_snapshot_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for bridge-format DatabaseSnapshot JSON (camelCase keys).

    Returns a complete snapshot dict with 1 of each entity type by default.
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
