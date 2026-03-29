"""Tests for bridge adapter module -- maps old bridge format to new model shape.

The adapter transforms raw bridge dicts (old format with PascalCase enums,
deprecated fields) to the new model shape. Tests here construct old-format
dicts by adding legacy keys via factory overrides.
"""

from __future__ import annotations

from typing import Any

import pytest

from omnifocus_operator.bridge.adapter import adapt_snapshot
from omnifocus_operator.models.repetition_rule import (
    EndByOccurrences,
    Frequency,
)


def _old_task(**overrides: Any) -> dict[str, Any]:
    """Build an old-format task dict (as bridge.js would produce)."""
    defaults: dict[str, Any] = {
        "id": "task-001",
        "name": "Test Task",
        "url": "omnifocus:///task/task-001",
        "note": "",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "active": True,
        "effectiveActive": True,
        "status": "Available",
        "completed": False,
        "completedByChildren": False,
        "flagged": False,
        "effectiveFlagged": False,
        "sequential": False,
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
        "estimatedMinutes": None,
        "hasChildren": False,
        "shouldUseFloatingTimeZone": False,
        "inInbox": True,
        "repetitionRule": None,
        "project": None,
        "parent": None,
        "tags": [],
    }
    return {**defaults, **overrides}


def _old_project(**overrides: Any) -> dict[str, Any]:
    """Build an old-format project dict (as bridge.js would produce)."""
    defaults: dict[str, Any] = {
        "id": "proj-001",
        "name": "Test Project",
        "url": "omnifocus:///project/proj-001",
        "note": "",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "active": True,
        "effectiveActive": True,
        "status": "Active",
        "taskStatus": "Available",
        "completed": False,
        "completedByChildren": False,
        "flagged": False,
        "effectiveFlagged": False,
        "sequential": False,
        "containsSingletonActions": False,
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
        "estimatedMinutes": None,
        "hasChildren": True,
        "shouldUseFloatingTimeZone": False,
        "repetitionRule": None,
        "lastReviewDate": "2024-01-10T10:00:00.000Z",
        "nextReviewDate": "2024-01-17T10:00:00.000Z",
        "reviewInterval": {"steps": 7, "unit": "days"},
        "nextTask": None,
        "folder": None,
        "tags": [],
    }
    return {**defaults, **overrides}


def _old_tag(**overrides: Any) -> dict[str, Any]:
    """Build an old-format tag dict (as bridge.js would produce)."""
    defaults: dict[str, Any] = {
        "id": "tag-001",
        "name": "Test Tag",
        "url": "omnifocus:///tag/tag-001",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "active": True,
        "effectiveActive": True,
        "status": "Active",
        "allowsNextAction": True,
        "childrenAreMutuallyExclusive": False,
        "parent": None,
    }
    return {**defaults, **overrides}


def _old_folder(**overrides: Any) -> dict[str, Any]:
    """Build an old-format folder dict (as bridge.js would produce)."""
    defaults: dict[str, Any] = {
        "id": "folder-001",
        "name": "Test Folder",
        "url": "omnifocus:///folder/folder-001",
        "added": "2024-01-15T10:30:00.000Z",
        "modified": "2024-01-15T10:30:00.000Z",
        "active": True,
        "effectiveActive": True,
        "status": "Active",
        "parent": None,
    }
    return {**defaults, **overrides}


def _old_snapshot(**overrides: Any) -> dict[str, Any]:
    """Build an old-format snapshot dict."""
    defaults: dict[str, Any] = {
        "tasks": [_old_task()],
        "projects": [_old_project()],
        "tags": [_old_tag()],
        "folders": [_old_folder()],
    }
    return {**defaults, **overrides}


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
        raw = _old_task(status=old_status)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["urgency"] == expected_urgency
        assert raw["availability"] == expected_availability

    def test_task_status_field_removed(self) -> None:
        raw = _old_task()
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert "status" not in raw

    def test_task_dead_fields_removed(self) -> None:
        raw = _old_task()
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
        raw = _old_task(status="BogusStatus")
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusStatus"):
            adapt_snapshot(snapshot)

    def test_task_preserves_other_fields(self) -> None:
        raw = _old_task(name="My Task", flagged=True)
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
        raw = _old_project(status=project_status)
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
        raw = _old_project(taskStatus=task_status)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["urgency"] == expected_urgency

    def test_project_status_and_task_status_removed(self) -> None:
        raw = _old_project()
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert "status" not in raw
        assert "taskStatus" not in raw

    def test_project_dead_fields_removed(self) -> None:
        raw = _old_project()
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
            "effectiveCompletionDate",
        ):
            assert field not in raw, f"Dead field '{field}' should be removed"

    def test_project_unknown_status_raises(self) -> None:
        raw = _old_project(status="BogusProjectStatus")
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusProjectStatus"):
            adapt_snapshot(snapshot)

    def test_project_unknown_task_status_raises(self) -> None:
        raw = _old_project(taskStatus="BogusTaskStatus")
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusTaskStatus"):
            adapt_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Tag status mapping
# ---------------------------------------------------------------------------


class TestAdaptTag:
    """Tag adapter maps bridge status -> model availability and removes dead fields."""

    @pytest.mark.parametrize(
        ("old_status", "expected_availability"),
        [
            ("Active", "available"),
            ("OnHold", "blocked"),
            ("Dropped", "dropped"),
        ],
    )
    def test_tag_status_to_availability(self, old_status: str, expected_availability: str) -> None:
        raw = _old_tag(status=old_status)
        snapshot = {"tasks": [], "projects": [], "tags": [raw], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["availability"] == expected_availability
        assert "status" not in raw

    def test_tag_dead_fields_removed(self) -> None:
        raw = _old_tag()
        snapshot = {"tasks": [], "projects": [], "tags": [raw], "folders": []}
        adapt_snapshot(snapshot)
        for field in ("allowsNextAction", "active", "effectiveActive"):
            assert field not in raw, f"Dead field '{field}' should be removed"

    def test_tag_unknown_status_raises(self) -> None:
        raw = _old_tag(status="BogusTagStatus")
        snapshot = {"tasks": [], "projects": [], "tags": [raw], "folders": []}
        with pytest.raises(ValueError, match="BogusTagStatus"):
            adapt_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Folder status mapping
# ---------------------------------------------------------------------------


class TestAdaptFolder:
    """Folder adapter maps bridge status -> model availability and removes dead fields."""

    @pytest.mark.parametrize(
        ("old_status", "expected_availability"),
        [
            ("Active", "available"),
            ("Dropped", "dropped"),
        ],
    )
    def test_folder_status_to_availability(
        self, old_status: str, expected_availability: str
    ) -> None:
        raw = _old_folder(status=old_status)
        snapshot = {"tasks": [], "projects": [], "tags": [], "folders": [raw]}
        adapt_snapshot(snapshot)
        assert raw["availability"] == expected_availability
        assert "status" not in raw

    def test_folder_dead_fields_removed(self) -> None:
        raw = _old_folder()
        snapshot = {"tasks": [], "projects": [], "tags": [], "folders": [raw]}
        adapt_snapshot(snapshot)
        for field in ("active", "effectiveActive"):
            assert field not in raw, f"Dead field '{field}' should be removed"

    def test_folder_unknown_status_raises(self) -> None:
        raw = _old_folder(status="BogusFolderStatus")
        snapshot = {"tasks": [], "projects": [], "tags": [], "folders": [raw]}
        with pytest.raises(ValueError, match="BogusFolderStatus"):
            adapt_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Task parent ref transformation
# ---------------------------------------------------------------------------


class TestAdaptTaskParentRef:
    """Adapter transforms bridge project/parent strings into ParentRef dict."""

    def test_inbox_task_parent_null(self) -> None:
        """Task with no project and no parent has parent=None."""
        raw = _old_task(project=None, parent=None)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] is None

    def test_task_in_project(self) -> None:
        """Task with project ID gets parent={type:'project', id, name}."""
        raw = _old_task(project="proj-001", parent=None)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] == {"type": "project", "id": "proj-001", "name": ""}
        assert "project" not in raw

    def test_subtask_with_parent_task(self) -> None:
        """Task with parent task ID gets parent={type:'task', id, name}."""
        raw = _old_task(project="proj-001", parent="task-parent-001")
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] == {"type": "task", "id": "task-parent-001", "name": ""}
        assert "project" not in raw

    def test_parent_task_takes_precedence_over_project(self) -> None:
        """When both parent and project are set, parent task wins."""
        raw = _old_task(project="proj-001", parent="parent-task")
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"]["type"] == "task"
        assert raw["parent"]["id"] == "parent-task"


# ---------------------------------------------------------------------------
# Repetition rule enum mapping
# ---------------------------------------------------------------------------


class TestAdaptRepetitionRule:
    """Adapter transforms bridge repetition rule to structured model shape."""

    def test_regularly_without_catch_up(self) -> None:
        """Regularly + catchUp=false -> schedule='regularly'."""
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=DAILY;INTERVAL=7",
                "scheduleType": "Regularly",
                "anchorDateKey": "DueDate",
                "catchUpAutomatically": False,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        rule = raw["repetitionRule"]
        assert rule["frequency"] == Frequency(type="daily", interval=7)
        assert rule["schedule"] == "regularly"
        assert rule["basedOn"] == "due_date"

    def test_regularly_with_catch_up(self) -> None:
        """Regularly + catchUp=true -> schedule='regularly_with_catch_up'."""
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=WEEKLY;BYDAY=MO,WE,FR",
                "scheduleType": "Regularly",
                "anchorDateKey": "DeferDate",
                "catchUpAutomatically": True,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        rule = raw["repetitionRule"]
        assert rule["frequency"] == Frequency(type="weekly", on_days=["MO", "WE", "FR"])
        assert rule["schedule"] == "regularly_with_catch_up"
        assert rule["basedOn"] == "defer_date"

    def test_from_completion(self) -> None:
        """FromCompletion + catchUp=false -> schedule='from_completion'."""
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=DAILY;INTERVAL=3",
                "scheduleType": "FromCompletion",
                "anchorDateKey": "DeferDate",
                "catchUpAutomatically": False,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        rule = raw["repetitionRule"]
        assert rule["frequency"] == Frequency(type="daily", interval=3)
        assert rule["schedule"] == "from_completion"
        assert rule["basedOn"] == "defer_date"

    def test_from_completion_with_catch_up_true(self) -> None:
        """FromCompletion + catchUp=true must NOT crash -- catch_up is irrelevant."""
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=DAILY;INTERVAL=3",
                "scheduleType": "FromCompletion",
                "anchorDateKey": "DeferDate",
                "catchUpAutomatically": True,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        rule = raw["repetitionRule"]
        assert rule["schedule"] == "from_completion"
        assert rule["frequency"] == Frequency(type="daily", interval=3)

    def test_end_condition_parsed(self) -> None:
        """RRULE with COUNT produces end condition in output."""
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=DAILY;COUNT=5",
                "scheduleType": "Regularly",
                "anchorDateKey": "DueDate",
                "catchUpAutomatically": False,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        rule = raw["repetitionRule"]
        assert rule["end"] == EndByOccurrences(occurrences=5)

    def test_none_schedule_type_nullifies_rule(self) -> None:
        """scheduleType "None" from bridge means no real repetition -- nullify the rule."""
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=DAILY",
                "scheduleType": "None",
                "anchorDateKey": "PlannedDate",
                "catchUpAutomatically": False,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["repetitionRule"] is None

    def test_null_repetition_rule_ignored(self) -> None:
        raw = _old_task(repetitionRule=None)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["repetitionRule"] is None

    def test_unknown_schedule_type_raises(self) -> None:
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=DAILY",
                "scheduleType": "BogusScheduleType",
                "anchorDateKey": "DueDate",
                "catchUpAutomatically": False,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusScheduleType"):
            adapt_snapshot(snapshot)

    def test_unknown_anchor_date_key_raises(self) -> None:
        raw = _old_task(
            repetitionRule={
                "ruleString": "FREQ=DAILY",
                "scheduleType": "Regularly",
                "anchorDateKey": "BogusAnchorKey",
                "catchUpAutomatically": False,
            }
        )
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        with pytest.raises(ValueError, match="BogusAnchorKey"):
            adapt_snapshot(snapshot)


# ---------------------------------------------------------------------------
# Idempotency -- adapter is no-op on already-adapted data
# ---------------------------------------------------------------------------


class TestAdapterIdempotency:
    """Adapter is safe to call on already-adapted (new-shape) data."""

    def test_task_without_status_key_is_noop(self) -> None:
        """Task dict with urgency/availability and no status key is untouched."""
        raw = {
            "id": "task-001",
            "name": "Already Adapted Task",
            "urgency": "due_soon",
            "availability": "available",
            "flagged": True,
        }
        original = dict(raw)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw == original

    def test_project_without_status_key_is_noop(self) -> None:
        """Project dict with urgency/availability and no status key is untouched."""
        raw = {
            "id": "proj-001",
            "name": "Already Adapted Project",
            "urgency": "none",
            "availability": "blocked",
            "folder": None,
        }
        original = dict(raw)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw == original

    def test_tag_with_availability_is_noop(self) -> None:
        """Tag dict with availability values is untouched."""
        for avail in ("available", "blocked", "dropped"):
            raw = {
                "id": "tag-001",
                "name": "Already Adapted Tag",
                "availability": avail,
                "childrenAreMutuallyExclusive": False,
                "parent": None,
            }
            original = dict(raw)
            snapshot = {"tasks": [], "projects": [], "tags": [raw], "folders": []}
            adapt_snapshot(snapshot)
            assert raw == original, f"Tag with availability={avail!r} should be a no-op"

    def test_folder_with_availability_is_noop(self) -> None:
        """Folder dict with availability values is untouched."""
        for avail in ("available", "dropped"):
            raw = {
                "id": "folder-001",
                "name": "Already Adapted Folder",
                "availability": avail,
                "parent": None,
            }
            original = dict(raw)
            snapshot = {"tasks": [], "projects": [], "tags": [], "folders": [raw]}
            adapt_snapshot(snapshot)
            assert raw == original, f"Folder with availability={avail!r} should be a no-op"


# ---------------------------------------------------------------------------
# Full snapshot
# ---------------------------------------------------------------------------


class TestAdaptSnapshot:
    """adapt_snapshot processes all entity types in a complete snapshot."""

    def test_full_snapshot(self) -> None:
        snapshot = _old_snapshot()
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
        assert tag["availability"] == "available"
        assert "status" not in tag
        assert "allowsNextAction" not in tag
        # Folder adapted
        folder = result["folders"][0]
        assert folder["availability"] == "available"
        assert "status" not in folder

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


# ---------------------------------------------------------------------------
# FALL-02: Bridge mode availability limitation
# ---------------------------------------------------------------------------


class TestFall02BridgeAvailabilityLimitation:
    """FALL-02: Bridge mode never produces 'blocked' availability for tasks or projects.

    The OmniJS bridge cannot determine sequential/dependency information, so it
    never sends "Blocked" task status or "OnHold" project status. In bridge mode,
    task and project availability is limited to: available, completed, dropped.

    Urgency remains fully populated: overdue, due_soon, none.
    """

    # The statuses that the OmniJS bridge actually sends for tasks.
    # "Blocked" is NOT in this set -- OmniJS can't detect blocking.
    BRIDGE_TASK_STATUSES = ("Available", "Next", "DueSoon", "Overdue", "Completed", "Dropped")

    # The statuses that the OmniJS bridge actually sends for projects.
    # "OnHold" is NOT in this set -- OmniJS can't detect on-hold.
    BRIDGE_PROJECT_STATUSES = ("Active", "Done", "Dropped")

    ALLOWED_TASK_AVAILABILITY = frozenset({"available", "completed", "dropped"})
    ALLOWED_TASK_URGENCY = frozenset({"overdue", "due_soon", "none"})

    ALLOWED_PROJECT_AVAILABILITY = frozenset({"available", "completed", "dropped"})

    @pytest.mark.parametrize("bridge_status", BRIDGE_TASK_STATUSES)
    def test_task_never_produces_blocked(self, bridge_status: str) -> None:
        raw = _old_task(status=bridge_status)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["availability"] != "blocked", (
            f"Bridge task status {bridge_status!r} must not produce 'blocked' availability"
        )
        assert raw["availability"] in self.ALLOWED_TASK_AVAILABILITY

    @pytest.mark.parametrize("bridge_status", BRIDGE_TASK_STATUSES)
    def test_task_urgency_fully_populated(self, bridge_status: str) -> None:
        raw = _old_task(status=bridge_status)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["urgency"] in self.ALLOWED_TASK_URGENCY

    @pytest.mark.parametrize("bridge_status", BRIDGE_PROJECT_STATUSES)
    def test_project_never_produces_blocked(self, bridge_status: str) -> None:
        raw = _old_project(status=bridge_status)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["availability"] != "blocked", (
            f"Bridge project status {bridge_status!r} must not produce 'blocked' availability"
        )
        assert raw["availability"] in self.ALLOWED_PROJECT_AVAILABILITY

    def test_full_bridge_snapshot_no_blocked(self) -> None:
        """A snapshot with all bridge-reachable statuses produces no 'blocked' values."""
        tasks = [_old_task(id=f"t-{i}", status=s) for i, s in enumerate(self.BRIDGE_TASK_STATUSES)]
        projects = [
            _old_project(id=f"p-{i}", status=s) for i, s in enumerate(self.BRIDGE_PROJECT_STATUSES)
        ]
        snapshot = {"tasks": tasks, "projects": projects, "tags": [], "folders": []}
        adapt_snapshot(snapshot)

        for task in snapshot["tasks"]:
            assert task["availability"] in self.ALLOWED_TASK_AVAILABILITY
            assert task["urgency"] in self.ALLOWED_TASK_URGENCY
        for project in snapshot["projects"]:
            assert project["availability"] in self.ALLOWED_PROJECT_AVAILABILITY
