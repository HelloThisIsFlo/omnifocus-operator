"""Tests for bridge adapter module -- maps old bridge format to new model shape."""

from __future__ import annotations

from typing import Any

import pytest

from omnifocus_operator.bridge.adapter import adapt_snapshot

from .conftest import (
    make_folder_dict,
    make_project_dict,
    make_snapshot_dict,
    make_tag_dict,
    make_task_dict,
)

# ---------------------------------------------------------------------------
# Task status mapping
# ---------------------------------------------------------------------------


class TestAdaptTask:
    """Task adapter maps old TaskStatus -> (urgency, availability) and removes dead fields."""

    @pytest.mark.parametrize(
        ("old_status", "expected_urgency", "expected_availability"),
        [
            ("Available", "none", "available"),
            ("Next", "none", "available"),
            ("Blocked", "none", "blocked"),
            ("DueSoon", "due_soon", "available"),
            ("Overdue", "overdue", "available"),
            ("Completed", "none", "completed"),
            ("Dropped", "none", "dropped"),
        ],
    )
    def test_task_status_mapping(
        self, old_status: str, expected_urgency: str, expected_availability: str
    ) -> None:
        raw = make_task_dict(status=old_status)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["urgency"] == expected_urgency
        assert raw["availability"] == expected_availability

    def test_task_status_field_removed(self) -> None:
        raw = make_task_dict()
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert "status" not in raw

    def test_task_dead_fields_removed(self) -> None:
        raw = make_task_dict()
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        for field in (
            "active",
            "effectiveActive",
            "completed",
            "completedByChildren",
            "sequential",
            "shouldUseFloatingTimeZone",
        ):
            assert field not in raw, f"Dead field '{field}' should be removed"

    def test_task_unknown_status_raises(self) -> None:
        raw = make_task_dict(status="BogusStatus")
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusStatus"):
            adapt_snapshot(snapshot)

    def test_task_preserves_other_fields(self) -> None:
        raw = make_task_dict(name="My Task", flagged=True)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["name"] == "My Task"
        assert raw["flagged"] is True


# ---------------------------------------------------------------------------
# Project status mapping
# ---------------------------------------------------------------------------


class TestAdaptProject:
    """Project adapter maps ProjectStatus -> availability, TaskStatus -> urgency."""

    @pytest.mark.parametrize(
        ("project_status", "expected_availability"),
        [
            ("Active", "available"),
            ("OnHold", "blocked"),
            ("Done", "completed"),
            ("Dropped", "dropped"),
        ],
    )
    def test_project_status_to_availability(
        self, project_status: str, expected_availability: str
    ) -> None:
        raw = make_project_dict(status=project_status)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["availability"] == expected_availability

    @pytest.mark.parametrize(
        ("task_status", "expected_urgency"),
        [
            ("Available", "none"),
            ("Next", "none"),
            ("Blocked", "none"),
            ("DueSoon", "due_soon"),
            ("Overdue", "overdue"),
            ("Completed", "none"),
            ("Dropped", "none"),
        ],
    )
    def test_project_task_status_to_urgency(self, task_status: str, expected_urgency: str) -> None:
        raw = make_project_dict(taskStatus=task_status)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["urgency"] == expected_urgency

    def test_project_status_and_task_status_removed(self) -> None:
        raw = make_project_dict()
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert "status" not in raw
        assert "taskStatus" not in raw

    def test_project_dead_fields_removed(self) -> None:
        raw = make_project_dict()
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        for field in (
            "active",
            "effectiveActive",
            "completed",
            "completedByChildren",
            "sequential",
            "shouldUseFloatingTimeZone",
            "containsSingletonActions",
        ):
            assert field not in raw, f"Dead field '{field}' should be removed"

    def test_project_unknown_status_raises(self) -> None:
        raw = make_project_dict(status="BogusProjectStatus")
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusProjectStatus"):
            adapt_snapshot(snapshot)

    def test_project_unknown_task_status_raises(self) -> None:
        raw = make_project_dict(taskStatus="BogusTaskStatus")
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusTaskStatus"):
            adapt_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Tag status mapping
# ---------------------------------------------------------------------------


class TestAdaptTag:
    """Tag adapter maps TagStatus -> snake_case and removes dead fields."""

    @pytest.mark.parametrize(
        ("old_status", "expected_status"),
        [
            ("Active", "active"),
            ("OnHold", "on_hold"),
            ("Dropped", "dropped"),
        ],
    )
    def test_tag_status_mapping(self, old_status: str, expected_status: str) -> None:
        raw = make_tag_dict(status=old_status)
        snapshot = {"tasks": [], "projects": [], "tags": [raw], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["status"] == expected_status

    def test_tag_dead_fields_removed(self) -> None:
        raw = make_tag_dict()
        snapshot = {"tasks": [], "projects": [], "tags": [raw], "folders": []}
        adapt_snapshot(snapshot)
        for field in ("allowsNextAction", "active", "effectiveActive"):
            assert field not in raw, f"Dead field '{field}' should be removed"

    def test_tag_unknown_status_raises(self) -> None:
        raw = make_tag_dict(status="BogusTagStatus")
        snapshot = {"tasks": [], "projects": [], "tags": [raw], "folders": []}
        with pytest.raises(ValueError, match="BogusTagStatus"):
            adapt_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Folder status mapping
# ---------------------------------------------------------------------------


class TestAdaptFolder:
    """Folder adapter maps FolderStatus -> snake_case and removes dead fields."""

    @pytest.mark.parametrize(
        ("old_status", "expected_status"),
        [
            ("Active", "active"),
            ("Dropped", "dropped"),
        ],
    )
    def test_folder_status_mapping(self, old_status: str, expected_status: str) -> None:
        raw = make_folder_dict(status=old_status)
        snapshot = {"tasks": [], "projects": [], "tags": [], "folders": [raw]}
        adapt_snapshot(snapshot)
        assert raw["status"] == expected_status

    def test_folder_dead_fields_removed(self) -> None:
        raw = make_folder_dict()
        snapshot = {"tasks": [], "projects": [], "tags": [], "folders": [raw]}
        adapt_snapshot(snapshot)
        for field in ("active", "effectiveActive"):
            assert field not in raw, f"Dead field '{field}' should be removed"

    def test_folder_unknown_status_raises(self) -> None:
        raw = make_folder_dict(status="BogusFolderStatus")
        snapshot = {"tasks": [], "projects": [], "tags": [], "folders": [raw]}
        with pytest.raises(ValueError, match="BogusFolderStatus"):
            adapt_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Repetition rule enum mapping
# ---------------------------------------------------------------------------


class TestAdaptRepetitionRule:
    """Adapter maps ScheduleType and AnchorDateKey to snake_case."""

    def test_schedule_type_mapping(self) -> None:
        raw = make_task_dict(
            repetitionRule={
                "scheduleType": "Regularly",
                "anchorDateKey": "DueDate",
                "interval": 7,
                "steps": 1,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["repetitionRule"]["scheduleType"] == "regularly"
        assert raw["repetitionRule"]["anchorDateKey"] == "due_date"

    def test_from_completion_schedule_type(self) -> None:
        raw = make_task_dict(
            repetitionRule={
                "scheduleType": "FromCompletion",
                "anchorDateKey": "DeferDate",
                "interval": 3,
                "steps": 1,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["repetitionRule"]["scheduleType"] == "from_completion"
        assert raw["repetitionRule"]["anchorDateKey"] == "defer_date"

    def test_none_schedule_type(self) -> None:
        raw = make_task_dict(
            repetitionRule={
                "scheduleType": "None",
                "anchorDateKey": "PlannedDate",
                "interval": 1,
                "steps": 1,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["repetitionRule"]["scheduleType"] == "none"
        assert raw["repetitionRule"]["anchorDateKey"] == "planned_date"

    def test_null_repetition_rule_ignored(self) -> None:
        raw = make_task_dict(repetitionRule=None)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["repetitionRule"] is None


# ---------------------------------------------------------------------------
# Full snapshot
# ---------------------------------------------------------------------------


class TestAdaptSnapshot:
    """adapt_snapshot processes all entity types in a complete snapshot."""

    def test_full_snapshot(self) -> None:
        snapshot = make_snapshot_dict()
        result = adapt_snapshot(snapshot)
        # Returns the same dict
        assert result is snapshot
        # Task adapted
        task = result["tasks"][0]
        assert "urgency" in task
        assert "availability" in task
        assert "status" not in task
        # Project adapted
        project = result["projects"][0]
        assert "urgency" in project
        assert "availability" in project
        assert "status" not in project
        assert "taskStatus" not in project
        # Tag adapted
        tag = result["tags"][0]
        assert tag["status"] == "active"
        assert "allowsNextAction" not in tag
        # Folder adapted
        folder = result["folders"][0]
        assert folder["status"] == "active"

    def test_empty_collections(self) -> None:
        snapshot: dict[str, Any] = {
            "tasks": [],
            "projects": [],
            "tags": [],
            "folders": [],
        }
        result = adapt_snapshot(snapshot)
        assert result == snapshot

    def test_missing_collections(self) -> None:
        snapshot: dict[str, Any] = {}
        result = adapt_snapshot(snapshot)
        assert result == {}
