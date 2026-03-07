"""Shared test fixtures and factory functions for new-shape model dicts.

Factory functions return dicts with camelCase keys matching the new model shape
(after adapter transformation). These use the two-axis status model
(urgency + availability) and snake_case enum values.
"""

from __future__ import annotations

from typing import Any


def make_task_dict(**overrides: Any) -> dict[str, Any]:
    """Factory for new-shape task dict (camelCase keys).

    Returns a complete task dict with all 27 model fields.
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
    """Factory for new-shape project dict (camelCase keys).

    Returns a complete project dict with all 29 model fields.
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
    """Factory for new-shape tag dict (camelCase keys).

    Returns a complete tag dict with all 8 model fields.
    """
    defaults: dict[str, Any] = {
        "id": "tag-001",
        "name": "Test Tag",
        "url": "omnifocus:///tag/tag-001",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "status": "active",
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
        "status": "active",
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
    """Factory for new-shape DatabaseSnapshot dict (camelCase keys).

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
