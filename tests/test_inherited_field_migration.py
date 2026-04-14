"""Tests for inherited field migration: moved from ActionableEntity to Task only.

Projects cannot meaningfully inherit dates/flags (folders have none), so
inherited fields are structurally impossible on projects. After migration:
- ActionableEntity has zero inherited fields
- Task has all 6 inherited fields
- Project has zero inherited fields
"""

from __future__ import annotations

from datetime import UTC, datetime

from omnifocus_operator.models.common import ActionableEntity
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.task import Task
from omnifocus_operator.repository.bridge_only.adapter import adapt_snapshot

from .conftest import make_model_project_dict, make_model_task_dict

# ---------------------------------------------------------------------------
# Model structure: inherited fields only on Task
# ---------------------------------------------------------------------------


class TestInheritedFieldsOnlyOnTask:
    """After migration, inherited fields live on Task, not ActionableEntity or Project."""

    def test_project_constructed_without_inherited_fields(self) -> None:
        """Project model succeeds without any inherited_* fields."""
        d = make_model_project_dict()
        # Verify no inherited keys in the dict
        inherited_keys = [k for k in d if "inherited" in k.lower()]
        assert inherited_keys == [], (
            f"Project dict should have no inherited keys, got: {inherited_keys}"
        )
        project = Project.model_validate(d)
        assert project.id == "proj-001"

    def test_task_retains_all_six_inherited_fields(self) -> None:
        """Task model has all 6 inherited fields after migration."""
        dt = datetime(2024, 6, 15, 12, 0, tzinfo=UTC)
        d = make_model_task_dict(
            inheritedFlagged=True,
            inheritedDueDate=dt.isoformat(),
            inheritedDeferDate=dt.isoformat(),
            inheritedPlannedDate=dt.isoformat(),
            inheritedDropDate=dt.isoformat(),
            inheritedCompletionDate=dt.isoformat(),
        )
        task = Task.model_validate(d)
        assert task.inherited_flagged is True
        assert task.inherited_due_date == dt
        assert task.inherited_defer_date == dt
        assert task.inherited_planned_date == dt
        assert task.inherited_drop_date == dt
        assert task.inherited_completion_date == dt

    def test_project_serialization_has_zero_inherited_keys(self) -> None:
        """Project.model_dump(by_alias=True) contains no inherited* keys."""
        d = make_model_project_dict()
        project = Project.model_validate(d)
        serialized = project.model_dump(by_alias=True)
        inherited_keys = [k for k in serialized if "inherited" in k.lower()]
        assert inherited_keys == [], (
            f"Project serialization should have no inherited keys, got: {inherited_keys}"
        )

    def test_task_serialization_has_all_six_inherited_keys(self) -> None:
        """Task.model_dump(by_alias=True) contains all 6 inherited* keys."""
        d = make_model_task_dict()
        task = Task.model_validate(d)
        serialized = task.model_dump(by_alias=True)
        expected_inherited = {
            "inheritedFlagged",
            "inheritedDueDate",
            "inheritedDeferDate",
            "inheritedPlannedDate",
            "inheritedDropDate",
            "inheritedCompletionDate",
        }
        actual_inherited = {k for k in serialized if "inherited" in k.lower()}
        assert actual_inherited == expected_inherited

    def test_actionable_entity_has_no_inherited_fields(self) -> None:
        """ActionableEntity itself has zero inherited_* field definitions."""
        # Get fields defined directly on ActionableEntity (not inherited from parent classes)
        ae_fields = set(ActionableEntity.model_fields.keys())
        inherited_fields = {f for f in ae_fields if f.startswith("inherited_")}
        assert inherited_fields == set(), (
            f"ActionableEntity should have no inherited fields, got: {inherited_fields}"
        )


# ---------------------------------------------------------------------------
# Bridge adapter: project dead field removal
# ---------------------------------------------------------------------------


class TestBridgeAdapterProjectInheritedFields:
    """Bridge adapter removes effective* inherited fields from project dicts."""

    def test_adapter_removes_inherited_fields_from_projects(self) -> None:
        """adapt_snapshot removes effectiveFlagged, effectiveDueDate, etc. from projects."""
        project = {
            "id": "proj-001",
            "name": "Test Project",
            "url": "omnifocus:///project/proj-001",
            "note": "",
            "added": "2024-01-15T10:30:00.000Z",
            "modified": "2024-01-15T10:30:00.000Z",
            "status": "Active",
            "taskStatus": "Available",
            "flagged": False,
            "effectiveFlagged": False,
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
            "repetitionRule": None,
            "lastReviewDate": "2024-01-10T10:00:00.000Z",
            "nextReviewDate": "2024-01-17T10:00:00.000Z",
            "reviewInterval": {"steps": 7, "unit": "days"},
            "nextTask": None,
            "folder": None,
            "tags": [],
            # Dead fields that adapter should remove
            "active": True,
            "effectiveActive": True,
            "completed": False,
            "completedByChildren": False,
            "sequential": False,
            "shouldUseFloatingTimeZone": False,
            "containsSingletonActions": False,
        }
        snapshot = {"tasks": [], "projects": [project], "tags": [], "folders": []}
        adapt_snapshot(snapshot)
        adapted = snapshot["projects"][0]
        # These inherited fields should be removed as dead fields
        for field in (
            "effectiveFlagged",
            "effectiveDueDate",
            "effectiveDeferDate",
            "effectivePlannedDate",
            "effectiveDropDate",
        ):
            assert field not in adapted, f"Dead field '{field}' should be removed from project"
        # But inherited fields should NOT be renamed to inherited* on projects
        for field in (
            "inheritedFlagged",
            "inheritedDueDate",
            "inheritedDeferDate",
            "inheritedPlannedDate",
            "inheritedDropDate",
        ):
            assert field not in adapted, f"Renamed field '{field}' should not exist on project"
