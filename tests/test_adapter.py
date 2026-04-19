"""Tests for bridge adapter module -- maps old bridge format to new model shape.

The adapter transforms raw bridge dicts (old format with PascalCase enums,
deprecated fields) to the new model shape. Tests here construct old-format
dicts by adding legacy keys via factory overrides.
"""

from __future__ import annotations

from typing import Any

import pytest

from omnifocus_operator.models.repetition_rule import (
    EndByOccurrences,
    Frequency,
)
from omnifocus_operator.repository.bridge_only.adapter import adapt_snapshot


def _old_task(**overrides: Any) -> dict[str, Any]:
    """Build an old-format task dict (as bridge.js would produce).

    Phase 56-02: ``completedByChildren``, ``sequential``, and ``hasAttachments``
    are present here because they're *now live source fields* (not dead).
    """
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
        "hasAttachments": False,
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
    """Build an old-format project dict (as bridge.js would produce).

    Phase 56-02: ``completedByChildren``, ``sequential``,
    ``containsSingletonActions``, and ``hasAttachments`` are *now live source
    fields* (not dead).
    """
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
        "hasAttachments": False,
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
        # Phase 56-02: completedByChildren + sequential are NO LONGER dead -- they
        # become live source fields for completesWithChildren + type respectively.
        for field in (
            "active",
            "effectiveActive",
            "completed",
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
        # Phase 56-02: completedByChildren + sequential + containsSingletonActions
        # are NO LONGER dead -- they become live source fields for
        # completesWithChildren + type.
        for field in (
            "active",
            "effectiveActive",
            "completed",
            "shouldUseFloatingTimeZone",
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
# Phase 56-02: Task property surface adapter (presence flags + type enum)
# ---------------------------------------------------------------------------


class TestAdaptTaskPropertySurface:
    """Adapter maps raw bridge fields to model-shape presence flags + type."""

    @pytest.mark.parametrize(
        ("raw_cwcc", "expected"),
        [(True, True), (False, False)],
    )
    def test_task_completes_with_children_roundtrip(self, raw_cwcc: bool, expected: bool) -> None:
        raw = _old_task(completedByChildren=raw_cwcc)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["completesWithChildren"] is expected

    def test_task_type_parallel_when_sequential_false(self) -> None:
        raw = _old_task(sequential=False)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["type"] == "parallel"

    def test_task_type_sequential_when_sequential_true(self) -> None:
        raw = _old_task(sequential=True)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["type"] == "sequential"

    @pytest.mark.parametrize(
        ("note", "expected"),
        [
            ("some note", True),
            ("", False),
        ],
    )
    def test_task_has_note_derived_from_note_field(self, note: str, expected: bool) -> None:
        raw = _old_task(note=note)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["hasNote"] is expected

    def test_task_has_repetition_false_when_no_rule(self) -> None:
        raw = _old_task(repetitionRule=None)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["hasRepetition"] is False

    def test_task_has_repetition_true_when_rule_present(self) -> None:
        rule = {
            "ruleString": "FREQ=DAILY",
            "scheduleType": "Regularly",
            "anchorDateKey": "DueDate",
            "catchUpAutomatically": False,
        }
        raw = _old_task(repetitionRule=rule)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["hasRepetition"] is True

    def test_task_has_attachments_passthrough_from_bridge(self) -> None:
        raw = _old_task(hasAttachments=True)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["hasAttachments"] is True

    def test_task_completed_by_children_and_sequential_are_live(self) -> None:
        """Phase 56-02 contract: these two raw fields are transformed, not stripped."""
        raw = _old_task(completedByChildren=False, sequential=True)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        # Raw keys removed (popped during transform) but their meaning survives
        # as the model-shape fields:
        assert raw["completesWithChildren"] is False
        assert raw["type"] == "sequential"


class TestAdaptProjectPropertySurface:
    """Adapter maps raw bridge fields to model-shape presence flags + three-state type."""

    def test_project_type_single_actions_takes_precedence_over_sequential(self) -> None:
        """HIER-05 cross-path: singleActions wins over sequential."""
        raw = _old_project(sequential=True, containsSingletonActions=True)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["type"] == "singleActions"

    @pytest.mark.parametrize(
        ("sequential", "contains_single", "expected"),
        [
            (False, False, "parallel"),
            (True, False, "sequential"),
            (False, True, "singleActions"),
            (True, True, "singleActions"),  # HIER-05
        ],
    )
    def test_project_type_all_three_states(
        self, sequential: bool, contains_single: bool, expected: str
    ) -> None:
        raw = _old_project(sequential=sequential, containsSingletonActions=contains_single)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["type"] == expected

    def test_project_completes_with_children_roundtrip(self) -> None:
        raw = _old_project(completedByChildren=False)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["completesWithChildren"] is False

    def test_project_has_note_derived_from_note(self) -> None:
        raw = _old_project(note="project notes")
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["hasNote"] is True

    def test_project_has_attachments_passthrough(self) -> None:
        raw = _old_project(hasAttachments=True)
        snapshot = {"tasks": [], "projects": [raw], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["hasAttachments"] is True


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
    """Adapter transforms bridge project/parent strings into tagged ParentRef + ProjectRef."""

    def test_inbox_task_gets_inbox_refs(self) -> None:
        """Task with no project and no parent gets $inbox parent and project."""
        raw = _old_task(project=None, parent=None)
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] == {"project": {"id": "$inbox", "name": "Inbox"}}
        assert raw["project"] == {"id": "$inbox", "name": "Inbox"}

    def test_task_in_project(self) -> None:
        """Task with project ID gets parent={"project": {id, name}} and project={id, name}."""
        raw = _old_task(project="proj-001", parent=None)
        proj = _old_project(id="proj-001", name="My Project")
        snapshot = {"tasks": [raw], "projects": [proj], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] == {"project": {"id": "proj-001", "name": "My Project"}}
        assert raw["project"] == {"id": "proj-001", "name": "My Project"}

    def test_subtask_with_parent_task(self) -> None:
        """Task with parent task ID gets parent={"task": {id, name}} and project={id, name}."""
        parent_task = _old_task(
            id="task-parent-001", name="Parent Task", project="proj-001", parent=None
        )
        raw = _old_task(project="proj-001", parent="task-parent-001")
        proj = _old_project(id="proj-001", name="My Project")
        snapshot = {"tasks": [parent_task, raw], "projects": [proj], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] == {"task": {"id": "task-parent-001", "name": "Parent Task"}}
        assert raw["project"] == {"id": "proj-001", "name": "My Project"}

    def test_parent_task_takes_precedence_over_project(self) -> None:
        """When both parent and project are set, parent is task, project is containing project."""
        parent_task = _old_task(
            id="parent-task", name="Parent Task", project="proj-001", parent=None
        )
        raw = _old_task(project="proj-001", parent="parent-task")
        proj = _old_project(id="proj-001", name="My Project")
        snapshot = {"tasks": [parent_task, raw], "projects": [proj], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert "task" in raw["parent"]
        assert raw["parent"]["task"]["id"] == "parent-task"
        assert raw["parent"]["task"]["name"] == "Parent Task"
        assert raw["project"]["id"] == "proj-001"
        assert raw["project"]["name"] == "My Project"

    def test_subtask_without_project_gets_inbox_project(self) -> None:
        """Subtask with parent task but no project gets $inbox as project."""
        parent_task = _old_task(id="parent-task", name="Parent Task", project=None, parent=None)
        raw = _old_task(project=None, parent="parent-task")
        snapshot = {"tasks": [parent_task, raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] == {"task": {"id": "parent-task", "name": "Parent Task"}}
        assert raw["project"] == {"id": "$inbox", "name": "Inbox"}

    def test_root_task_parent_equals_project_id(self) -> None:
        """Root task where parent == project ID gets parent={project:...}, not {task:...}."""
        raw = _old_task(project="proj-001", parent="proj-001", projectName="My Project")
        snapshot = {"tasks": [raw], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        assert raw["parent"] == {"project": {"id": "proj-001", "name": "My Project"}}
        assert raw["project"] == {"id": "proj-001", "name": "My Project"}


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
# Project enrichment -- nextTask self-reference
# ---------------------------------------------------------------------------


class TestEnrichProjectNextTask:
    """_enrich_project filters out nextTask self-references."""

    def test_enrich_project_next_task_self_reference(self) -> None:
        """Project where nextTask == own ID gets nextTask=None after enrichment."""
        proj = _old_project(id="proj-1", nextTask="proj-1")
        task = _old_task(id="task-other", name="Other Task")
        snapshot = {"tasks": [task], "projects": [proj], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        adapted_proj = snapshot["projects"][0]
        # nextTask should be nullified, not enriched to {id, name}
        assert adapted_proj["nextTask"] is None

    def test_enrich_project_next_task_different_id(self) -> None:
        """Project where nextTask != own ID keeps the enriched {id, name} ref."""
        proj = _old_project(id="proj-1", nextTask="task-abc")
        task = _old_task(id="task-abc", name="First Task")
        snapshot = {"tasks": [task], "projects": [proj], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        adapted_proj = snapshot["projects"][0]
        next_task = adapted_proj.get("nextTask") or adapted_proj.get("next_task")
        assert next_task == {"id": "task-abc", "name": "First Task"}


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


# ---------------------------------------------------------------------------
# Project root task filtering
# ---------------------------------------------------------------------------


class TestProjectRootTaskFiltering:
    """adapt_snapshot excludes project root tasks from the tasks list.

    In OmniFocus, every project has an underlying Task object. The SQL path
    excludes these via LEFT JOIN ProjectInfo WHERE pi.task IS NULL. The
    bridge-only path must filter them out in adapt_snapshot.
    """

    def test_project_root_task_excluded(self) -> None:
        """Task whose ID matches a project ID is removed from the tasks list."""
        proj = _old_project(id="proj1", name="My Project")
        root_task = _old_task(id="proj1", name="My Project", project="proj1", parent="proj1")
        snapshot = {"tasks": [root_task], "projects": [proj], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        task_ids = [t["id"] for t in snapshot["tasks"]]
        assert "proj1" not in task_ids

    def test_normal_tasks_preserved_when_project_root_excluded(self) -> None:
        """Normal tasks survive when a project root task is filtered out."""
        proj = _old_project(id="proj1", name="My Project")
        root_task = _old_task(id="proj1", name="My Project", project="proj1", parent="proj1")
        normal_task1 = _old_task(id="task1", name="Task 1", project="proj1", parent="proj1")
        normal_task2 = _old_task(id="task2", name="Task 2", project="proj1", parent="proj1")
        snapshot = {
            "tasks": [root_task, normal_task1, normal_task2],
            "projects": [proj],
            "tags": [],
            "folders": [],
        }
        adapt_snapshot(snapshot)
        task_ids = [t["id"] for t in snapshot["tasks"]]
        assert "proj1" not in task_ids
        assert "task1" in task_ids
        assert "task2" in task_ids

    def test_no_projects_no_filtering(self) -> None:
        """When there are no projects, all tasks are preserved (no crash)."""
        task1 = _old_task(id="task1", name="Task 1")
        task2 = _old_task(id="task2", name="Task 2")
        snapshot = {"tasks": [task1, task2], "projects": [], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        task_ids = [t["id"] for t in snapshot["tasks"]]
        assert task_ids == ["task1", "task2"]
