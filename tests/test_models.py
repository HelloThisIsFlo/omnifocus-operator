"""Tests for OmniFocus models: base config, enums, common (MODL-07) and entities (MODL-01..06)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnifocus_operator.models import (
    ActionableEntity,
    DatabaseSnapshot,
    EntityStatus,
    Folder,
    OmniFocusBaseModel,
    OmniFocusEntity,
    Perspective,
    Project,
    RepetitionRule,
    ReviewInterval,
    Tag,
    Task,
    TaskStatus,
)

from .conftest import (
    make_folder_dict,
    make_perspective_dict,
    make_project_dict,
    make_snapshot_dict,
    make_tag_dict,
    make_task_dict,
)

# ---------------------------------------------------------------------------
# Base config tests (MODL-07)
# ---------------------------------------------------------------------------


class TestBaseConfig:
    """Verify OmniFocusBaseModel ConfigDict: aliases and validation."""

    def test_base_config_aliases(self) -> None:
        """OmniFocusBaseModel subclass serializes snake_case fields to camelCase."""

        class Sample(OmniFocusBaseModel):
            my_field: str
            another_value: int

        instance = Sample(my_field="hello", another_value=42)
        dumped = instance.model_dump(by_alias=True)
        assert "myField" in dumped
        assert "anotherValue" in dumped
        assert dumped["myField"] == "hello"
        assert dumped["anotherValue"] == 42

    def test_base_config_validate_by_name(self) -> None:
        """Construction with snake_case field names works (validate_by_name=True)."""

        class Sample(OmniFocusBaseModel):
            some_field: str

        instance = Sample(some_field="works")
        assert instance.some_field == "works"

    def test_base_config_validate_by_alias(self) -> None:
        """Construction with camelCase field names works (validate_by_alias=True)."""

        class Sample(OmniFocusBaseModel):
            some_field: str

        instance = Sample(someField="works")  # type: ignore[call-arg]
        assert instance.some_field == "works"


# ---------------------------------------------------------------------------
# Enum tests
# ---------------------------------------------------------------------------


class TestTaskStatus:
    """TaskStatus enum has exactly 7 members matching bridge script ts() function."""

    def test_task_status_values(self) -> None:
        assert TaskStatus.AVAILABLE == "Available"
        assert TaskStatus.BLOCKED == "Blocked"
        assert TaskStatus.COMPLETED == "Completed"
        assert TaskStatus.DROPPED == "Dropped"
        assert TaskStatus.DUE_SOON == "DueSoon"
        assert TaskStatus.NEXT == "Next"
        assert TaskStatus.OVERDUE == "Overdue"

    def test_task_status_member_count(self) -> None:
        assert len(TaskStatus) == 7


class TestEntityStatus:
    """EntityStatus enum has exactly 3 members matching bridge .status.name values."""

    def test_entity_status_values(self) -> None:
        assert EntityStatus.ACTIVE == "Active"
        assert EntityStatus.DONE == "Done"
        assert EntityStatus.DROPPED == "Dropped"

    def test_entity_status_member_count(self) -> None:
        assert len(EntityStatus) == 3


class TestEnumValidation:
    """Enums used in Pydantic models reject unknown values."""

    def test_enum_unknown_value_rejected(self) -> None:
        """Parsing an invalid status string raises ValidationError."""

        class StatusModel(OmniFocusBaseModel):
            status: TaskStatus

        with pytest.raises(ValidationError):
            StatusModel(status="InvalidStatus")


# ---------------------------------------------------------------------------
# Common model tests
# ---------------------------------------------------------------------------


class TestRepetitionRule:
    """RepetitionRule parses camelCase JSON and serializes back."""

    def test_repetition_rule_camel_case_round_trip(self) -> None:
        data = {"ruleString": "FREQ=DAILY", "scheduleType": "DueAgainAfterCompletion"}
        rule = RepetitionRule.model_validate(data)
        assert rule.rule_string == "FREQ=DAILY"
        assert rule.schedule_type == "DueAgainAfterCompletion"

        dumped = rule.model_dump(by_alias=True)
        assert dumped["ruleString"] == "FREQ=DAILY"
        assert dumped["scheduleType"] == "DueAgainAfterCompletion"


class TestReviewInterval:
    """ReviewInterval parses and serializes correctly."""

    def test_review_interval_round_trip(self) -> None:
        data = {"steps": 7, "unit": "days"}
        interval = ReviewInterval.model_validate(data)
        assert interval.steps == 7
        assert interval.unit == "days"

        dumped = interval.model_dump(by_alias=True)
        assert dumped["steps"] == 7
        assert dumped["unit"] == "days"


# ---------------------------------------------------------------------------
# ActionableEntity date tests
# ---------------------------------------------------------------------------


class TestActionableEntityDates:
    """AwareDatetime fields on ActionableEntity enforce timezone and default to None."""

    def test_aware_datetime_rejects_naive(self) -> None:
        """AwareDatetime raises ValidationError on naive datetime."""
        from pydantic import AwareDatetime

        class DateModel(OmniFocusBaseModel):
            ts: AwareDatetime

        with pytest.raises(ValidationError, match="timezone_aware"):
            DateModel(ts=datetime(2024, 1, 15, 10, 30))  # naive

    def test_optional_dates_default_none(self) -> None:
        """Optional date fields on ActionableEntity default to None."""
        entity = ActionableEntity(
            id="test-1",
            name="Test",
            note="",
            completed=False,
            completed_by_children=False,
            flagged=False,
            effective_flagged=False,
            sequential=False,
            has_children=False,
            should_use_floating_time_zone=False,
            tags=[],
        )
        assert entity.due_date is None
        assert entity.defer_date is None
        assert entity.effective_due_date is None
        assert entity.effective_defer_date is None
        assert entity.completion_date is None
        assert entity.effective_completion_date is None
        assert entity.planned_date is None
        assert entity.effective_planned_date is None
        assert entity.drop_date is None
        assert entity.effective_drop_date is None
        assert entity.estimated_minutes is None
        assert entity.repetition_rule is None


# ---------------------------------------------------------------------------
# Inheritance tests
# ---------------------------------------------------------------------------


class TestInheritanceHierarchy:
    """OmniFocusBaseModel -> OmniFocusEntity -> ActionableEntity."""

    def test_omnifocus_entity_has_id_and_name(self) -> None:
        entity = OmniFocusEntity(id="abc", name="Test")
        assert entity.id == "abc"
        assert entity.name == "Test"

    def test_actionable_entity_inherits_from_entity(self) -> None:
        assert issubclass(ActionableEntity, OmniFocusEntity)
        assert issubclass(ActionableEntity, OmniFocusBaseModel)

    def test_actionable_entity_with_dates(self) -> None:
        """ActionableEntity accepts timezone-aware dates."""
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=UTC)
        entity = ActionableEntity(
            id="test-1",
            name="Test",
            note="A note",
            completed=False,
            completed_by_children=False,
            flagged=True,
            effective_flagged=True,
            sequential=False,
            due_date=dt,
            has_children=False,
            should_use_floating_time_zone=False,
            tags=["errands"],
        )
        assert entity.due_date == dt
        assert entity.flagged is True
        assert entity.tags == ["errands"]


# ---------------------------------------------------------------------------
# Factory function tests
# ---------------------------------------------------------------------------


class TestFactoryFunctions:
    """Factory functions produce valid bridge-format dicts with correct field counts."""

    def test_make_task_dict_field_count(self) -> None:
        """make_task_dict returns exactly 32 fields (all bridge task fields)."""
        d = make_task_dict()
        assert len(d) == 32

    def test_make_task_dict_overrides(self) -> None:
        """make_task_dict supports keyword overrides."""
        d = make_task_dict(name="Custom Task", status="Blocked")
        assert d["name"] == "Custom Task"
        assert d["status"] == "Blocked"

    def test_make_project_dict_field_count(self) -> None:
        """make_project_dict returns exactly 31 fields (all bridge project fields)."""
        d = make_project_dict()
        assert len(d) == 31

    def test_make_tag_dict_field_count(self) -> None:
        """make_tag_dict returns exactly 9 fields (all bridge tag fields)."""
        d = make_tag_dict()
        assert len(d) == 9

    def test_make_folder_dict_field_count(self) -> None:
        """make_folder_dict returns exactly 8 fields (all bridge folder fields)."""
        d = make_folder_dict()
        assert len(d) == 8

    def test_make_perspective_dict_field_count(self) -> None:
        """make_perspective_dict returns exactly 3 fields (all bridge perspective fields)."""
        d = make_perspective_dict()
        assert len(d) == 3

    def test_make_snapshot_dict_structure(self) -> None:
        """make_snapshot_dict contains all 5 entity collections."""
        d = make_snapshot_dict()
        assert "tasks" in d
        assert "projects" in d
        assert "tags" in d
        assert "folders" in d
        assert "perspectives" in d
        assert len(d["tasks"]) == 1
        assert len(d["projects"]) == 1
        assert len(d["tags"]) == 1
        assert len(d["folders"]) == 1
        assert len(d["perspectives"]) == 1


# ---------------------------------------------------------------------------
# Task model tests (MODL-01)
# ---------------------------------------------------------------------------


class TestTaskModel:
    """Task model parses all 32 bridge fields with snake_case names and camelCase aliases."""

    def test_task_from_bridge_json(self) -> None:
        """Parse make_task_dict() via Task.model_validate(), verify all 32 fields."""
        data = make_task_dict(
            dueDate="2024-06-15T09:00:00.000Z",
            tags=["errands", "morning"],
        )
        task = Task.model_validate(data)

        # Identity
        assert task.id == "task-001"
        assert task.name == "Test Task"
        assert task.note == ""

        # Lifecycle (Task-specific)
        assert task.added is not None
        assert task.modified is not None
        assert task.active is True
        assert task.effective_active is True
        assert task.status == TaskStatus.AVAILABLE

        # Completion
        assert task.completed is False
        assert task.completed_by_children is False

        # Flags
        assert task.flagged is False
        assert task.effective_flagged is False
        assert task.sequential is False

        # Dates
        assert task.due_date is not None
        assert task.defer_date is None
        assert task.effective_due_date is None
        assert task.effective_defer_date is None
        assert task.completion_date is None
        assert task.effective_completion_date is None
        assert task.planned_date is None
        assert task.effective_planned_date is None
        assert task.drop_date is None
        assert task.effective_drop_date is None

        # Metadata
        assert task.estimated_minutes is None
        assert task.has_children is False
        assert task.should_use_floating_time_zone is False

        # Relationships
        assert task.in_inbox is True
        assert task.repetition_rule is None
        assert task.project is None
        assert task.parent is None
        assert task.assigned_container is None
        assert task.tags == ["errands", "morning"]

        # Verify total field count
        assert len(Task.model_fields) == 32

        # Serialize back to camelCase and verify round-trip
        dumped = task.model_dump(mode="json", by_alias=True)
        assert "dueDate" in dumped
        assert "effectiveFlagged" in dumped
        assert "inInbox" in dumped
        assert "assignedContainer" in dumped

        # Re-parse and compare
        task2 = Task.model_validate(dumped)
        assert task.id == task2.id
        assert task.due_date == task2.due_date
        assert task.tags == task2.tags

    def test_task_status_required(self) -> None:
        """Task without status raises ValidationError."""
        data = make_task_dict()
        del data["status"]
        with pytest.raises(ValidationError):
            Task.model_validate(data)

    def test_task_tags_are_names(self) -> None:
        """tags field contains string names (not IDs)."""
        data = make_task_dict(tags=["errands", "morning"])
        task = Task.model_validate(data)
        assert task.tags == ["errands", "morning"]
        assert all(isinstance(t, str) for t in task.tags)

    def test_task_optional_relationships_default_none(self) -> None:
        """Optional relationship fields (project, parent, assignedContainer) default to None."""
        data = make_task_dict()
        task = Task.model_validate(data)
        assert task.project is None
        assert task.parent is None
        assert task.assigned_container is None


# ---------------------------------------------------------------------------
# Project model tests (MODL-02)
# ---------------------------------------------------------------------------


class TestProjectModel:
    """Project model parses all 31 bridge fields including nested objects."""

    def test_project_from_bridge_json(self) -> None:
        """Parse make_project_dict(), verify all 31 fields, both status fields present."""
        data = make_project_dict()
        project = Project.model_validate(data)

        # Identity
        assert project.id == "proj-001"
        assert project.name == "Test Project"
        assert project.note == ""

        # Dual status
        assert project.status == EntityStatus.ACTIVE
        assert project.task_status == TaskStatus.AVAILABLE

        # Structure
        assert project.contains_singleton_actions is False

        # Completion
        assert project.completed is False
        assert project.completed_by_children is False

        # Review
        assert project.last_review_date is not None
        assert project.next_review_date is not None
        assert project.review_interval is not None
        assert project.review_interval.steps == 7
        assert project.review_interval.unit == "days"

        # Relationships
        assert project.next_task is None
        assert project.folder is None
        assert project.tags == []

        # Verify total field count
        assert len(Project.model_fields) == 31

        # Serialize back and verify camelCase keys
        dumped = project.model_dump(mode="json", by_alias=True)
        assert "taskStatus" in dumped
        assert "containsSingletonActions" in dumped
        assert "lastReviewDate" in dumped
        assert "reviewInterval" in dumped
        assert "nextTask" in dumped

    def test_project_dual_status_fields(self) -> None:
        """Project has both status (EntityStatus) and task_status (TaskStatus)."""
        data = make_project_dict(status="Dropped", taskStatus="Blocked")
        project = Project.model_validate(data)
        assert project.status == EntityStatus.DROPPED
        assert project.task_status == TaskStatus.BLOCKED

    def test_project_nested_repetition_rule(self) -> None:
        """Project with repetitionRule object parses correctly."""
        data = make_project_dict(
            repetitionRule={"ruleString": "FREQ=WEEKLY", "scheduleType": "DueAgainAfterCompletion"},
        )
        project = Project.model_validate(data)
        assert project.repetition_rule is not None
        assert project.repetition_rule.rule_string == "FREQ=WEEKLY"
        assert project.repetition_rule.schedule_type == "DueAgainAfterCompletion"

    def test_project_nested_review_interval(self) -> None:
        """Project with reviewInterval object parses correctly."""
        data = make_project_dict(reviewInterval={"steps": 14, "unit": "days"})
        project = Project.model_validate(data)
        assert project.review_interval is not None
        assert project.review_interval.steps == 14
        assert project.review_interval.unit == "days"


# ---------------------------------------------------------------------------
# Tag model tests (MODL-03)
# ---------------------------------------------------------------------------


class TestTagModel:
    """Tag model parses all 9 bridge fields."""

    def test_tag_from_bridge_json(self) -> None:
        """Parse make_tag_dict(), verify all 9 fields."""
        data = make_tag_dict()
        tag = Tag.model_validate(data)

        assert tag.id == "tag-001"
        assert tag.name == "Test Tag"
        assert tag.added is not None
        assert tag.modified is not None
        assert tag.active is True
        assert tag.effective_active is True
        assert tag.status == EntityStatus.ACTIVE
        assert tag.allows_next_action is True
        assert tag.parent is None

        # Verify total field count
        assert len(Tag.model_fields) == 9

        # Round-trip
        dumped = tag.model_dump(mode="json", by_alias=True)
        assert "allowsNextAction" in dumped
        assert "effectiveActive" in dumped
        tag2 = Tag.model_validate(dumped)
        assert tag.id == tag2.id

    def test_tag_nullable_status(self) -> None:
        """Tag with status=None parses correctly."""
        data = make_tag_dict(status=None)
        tag = Tag.model_validate(data)
        assert tag.status is None


# ---------------------------------------------------------------------------
# Folder model tests (MODL-04)
# ---------------------------------------------------------------------------


class TestFolderModel:
    """Folder model parses all 8 bridge fields."""

    def test_folder_from_bridge_json(self) -> None:
        """Parse make_folder_dict(), verify all 8 fields."""
        data = make_folder_dict()
        folder = Folder.model_validate(data)

        assert folder.id == "folder-001"
        assert folder.name == "Test Folder"
        assert folder.added is not None
        assert folder.modified is not None
        assert folder.active is True
        assert folder.effective_active is True
        assert folder.status == EntityStatus.ACTIVE
        assert folder.parent is None

        # Verify total field count
        assert len(Folder.model_fields) == 8

        # Round-trip
        dumped = folder.model_dump(mode="json", by_alias=True)
        assert "effectiveActive" in dumped
        folder2 = Folder.model_validate(dumped)
        assert folder.id == folder2.id

    def test_folder_nullable_status(self) -> None:
        """Folder with status=None parses correctly."""
        data = make_folder_dict(status=None)
        folder = Folder.model_validate(data)
        assert folder.status is None


# ---------------------------------------------------------------------------
# Perspective model tests (MODL-05)
# ---------------------------------------------------------------------------


class TestPerspectiveModel:
    """Perspective model has id: str | None, name: str, builtin: bool."""

    def test_perspective_from_bridge_json(self) -> None:
        """Parse make_perspective_dict(), verify 3 fields."""
        data = make_perspective_dict()
        perspective = Perspective.model_validate(data)

        assert perspective.id == "persp-001"
        assert perspective.name == "Test Perspective"
        assert perspective.builtin is False

        # Verify total field count
        assert len(Perspective.model_fields) == 3

        # Round-trip
        dumped = perspective.model_dump(mode="json", by_alias=True)
        perspective2 = Perspective.model_validate(dumped)
        assert perspective.id == perspective2.id

    def test_perspective_builtin_null_id(self) -> None:
        """Perspective with id=null parses correctly (builtin perspectives)."""
        data = make_perspective_dict(id=None, builtin=True, name="Inbox")
        perspective = Perspective.model_validate(data)
        assert perspective.id is None
        assert perspective.builtin is True
        assert perspective.name == "Inbox"


# ---------------------------------------------------------------------------
# DatabaseSnapshot tests (MODL-06)
# ---------------------------------------------------------------------------


class TestDatabaseSnapshot:
    """DatabaseSnapshot aggregates tasks, projects, tags, folders, perspectives lists."""

    def test_database_snapshot_round_trip(self) -> None:
        """Parse make_snapshot_dict(), verify collections, serialize and re-parse."""
        data = make_snapshot_dict()
        snapshot = DatabaseSnapshot.model_validate(data)

        assert len(snapshot.tasks) == 1
        assert len(snapshot.projects) == 1
        assert len(snapshot.tags) == 1
        assert len(snapshot.folders) == 1
        assert len(snapshot.perspectives) == 1

        # Verify types
        assert isinstance(snapshot.tasks[0], Task)
        assert isinstance(snapshot.projects[0], Project)
        assert isinstance(snapshot.tags[0], Tag)
        assert isinstance(snapshot.folders[0], Folder)
        assert isinstance(snapshot.perspectives[0], Perspective)

        # Serialize and re-parse
        dumped = snapshot.model_dump(mode="json", by_alias=True)
        snapshot2 = DatabaseSnapshot.model_validate(dumped)
        assert len(snapshot2.tasks) == 1
        assert snapshot2.tasks[0].id == snapshot.tasks[0].id

    def test_database_snapshot_empty_collections(self) -> None:
        """DatabaseSnapshot with empty lists is valid."""
        data = make_snapshot_dict(tasks=[], projects=[], tags=[], folders=[], perspectives=[])
        snapshot = DatabaseSnapshot.model_validate(data)
        assert len(snapshot.tasks) == 0
        assert len(snapshot.projects) == 0
        assert len(snapshot.tags) == 0
        assert len(snapshot.folders) == 0
        assert len(snapshot.perspectives) == 0

    def test_full_bridge_payload_round_trip(self) -> None:
        """Large payload with multiple entities round-trips without data loss."""
        data = {
            "tasks": [
                make_task_dict(id="t1", name="Task 1", status="Available"),
                make_task_dict(
                    id="t2",
                    name="Task 2",
                    status="Blocked",
                    dueDate="2024-06-15T09:00:00.000Z",
                    tags=["errands"],
                    project="proj-001",
                ),
                make_task_dict(id="t3", name="Task 3", status="Completed", completed=True),
            ],
            "projects": [
                make_project_dict(id="p1", name="Project A"),
                make_project_dict(
                    id="p2",
                    name="Project B",
                    status="Dropped",
                    taskStatus="Dropped",
                    folder="folder-001",
                ),
            ],
            "tags": [
                make_tag_dict(id="tg1", name="errands"),
                make_tag_dict(id="tg2", name="morning", allowsNextAction=False),
            ],
            "folders": [
                make_folder_dict(id="f1", name="Work"),
            ],
            "perspectives": [
                make_perspective_dict(id="ps1", name="Custom View"),
                make_perspective_dict(id=None, name="Inbox", builtin=True),
            ],
        }

        snapshot = DatabaseSnapshot.model_validate(data)
        assert len(snapshot.tasks) == 3
        assert len(snapshot.projects) == 2
        assert len(snapshot.tags) == 2
        assert len(snapshot.folders) == 1
        assert len(snapshot.perspectives) == 2

        # Full round-trip
        dumped = snapshot.model_dump(mode="json", by_alias=True)
        snapshot2 = DatabaseSnapshot.model_validate(dumped)

        # Verify data fidelity
        assert snapshot2.tasks[1].due_date is not None
        assert snapshot2.tasks[1].tags == ["errands"]
        assert snapshot2.tasks[1].project == "proj-001"
        assert snapshot2.projects[1].status == EntityStatus.DROPPED
        assert snapshot2.perspectives[1].id is None
        assert snapshot2.perspectives[1].builtin is True

        # Verify complete round-trip: compare all task IDs
        original_task_ids = [t["id"] for t in data["tasks"]]
        parsed_task_ids = [t.id for t in snapshot2.tasks]
        assert original_task_ids == parsed_task_ids
