"""Tests for OmniFocus models: base config, enums, common (MODL-07) and entities (MODL-01..06)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import ValidationError

from omnifocus_operator.models import (
    ActionableEntity,
    AnchorDateKey,
    Availability,
    DatabaseSnapshot,
    Folder,
    FolderStatus,
    OmniFocusBaseModel,
    OmniFocusEntity,
    Perspective,
    Project,
    ProjectStatus,
    RepetitionRule,
    ReviewInterval,
    ScheduleType,
    Tag,
    TagRef,
    TagStatus,
    Task,
    TaskStatus,
    Urgency,
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


class TestUrgency:
    """Urgency enum has exactly 3 members with snake_case values."""

    def test_urgency_values(self) -> None:
        assert Urgency.OVERDUE == "overdue"
        assert Urgency.DUE_SOON == "due_soon"
        assert Urgency.NONE == "none"

    def test_urgency_member_count(self) -> None:
        assert len(Urgency) == 3

    def test_urgency_is_str_enum(self) -> None:
        assert isinstance(Urgency.OVERDUE, str)


class TestAvailability:
    """Availability enum has exactly 4 members with snake_case values."""

    def test_availability_values(self) -> None:
        assert Availability.AVAILABLE == "available"
        assert Availability.BLOCKED == "blocked"
        assert Availability.COMPLETED == "completed"
        assert Availability.DROPPED == "dropped"

    def test_availability_member_count(self) -> None:
        assert len(Availability) == 4

    def test_availability_is_str_enum(self) -> None:
        assert isinstance(Availability.AVAILABLE, str)


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


class TestProjectStatus:
    """ProjectStatus enum has exactly 4 members matching bridge ps() resolver."""

    def test_project_status_values(self) -> None:
        assert ProjectStatus.ACTIVE == "Active"
        assert ProjectStatus.ON_HOLD == "OnHold"
        assert ProjectStatus.DONE == "Done"
        assert ProjectStatus.DROPPED == "Dropped"

    def test_project_status_member_count(self) -> None:
        assert len(ProjectStatus) == 4


class TestTagStatus:
    """TagStatus enum has exactly 3 members matching bridge gs() resolver."""

    def test_tag_status_values(self) -> None:
        assert TagStatus.ACTIVE == "Active"
        assert TagStatus.ON_HOLD == "OnHold"
        assert TagStatus.DROPPED == "Dropped"

    def test_tag_status_member_count(self) -> None:
        assert len(TagStatus) == 3


class TestFolderStatus:
    """FolderStatus enum has exactly 2 members matching bridge fs() resolver."""

    def test_folder_status_values(self) -> None:
        assert FolderStatus.ACTIVE == "Active"
        assert FolderStatus.DROPPED == "Dropped"

    def test_folder_status_member_count(self) -> None:
        assert len(FolderStatus) == 2


class TestScheduleType:
    """ScheduleType enum has exactly 3 members matching bridge rst() resolver."""

    def test_schedule_type_values(self) -> None:
        assert ScheduleType.REGULARLY == "Regularly"
        assert ScheduleType.FROM_COMPLETION == "FromCompletion"
        assert ScheduleType.NONE == "None"

    def test_schedule_type_member_count(self) -> None:
        assert len(ScheduleType) == 3


class TestAnchorDateKey:
    """AnchorDateKey enum has exactly 3 members matching bridge adk() resolver."""

    def test_anchor_date_key_values(self) -> None:
        assert AnchorDateKey.DUE_DATE == "DueDate"
        assert AnchorDateKey.DEFER_DATE == "DeferDate"
        assert AnchorDateKey.PLANNED_DATE == "PlannedDate"

    def test_anchor_date_key_member_count(self) -> None:
        assert len(AnchorDateKey) == 3


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


class TestTagRef:
    """TagRef model with id and name for tag serialization."""

    def test_tag_ref_round_trip(self) -> None:
        data = {"id": "tag-001", "name": "errands"}
        ref = TagRef.model_validate(data)
        assert ref.id == "tag-001"
        assert ref.name == "errands"
        dumped = ref.model_dump(by_alias=True)
        assert dumped == {"id": "tag-001", "name": "errands"}


class TestRepetitionRule:
    """RepetitionRule has 4 required typed fields."""

    def test_repetition_rule_full_round_trip(self) -> None:
        data = {
            "ruleString": "FREQ=DAILY",
            "scheduleType": "Regularly",
            "anchorDateKey": "DueDate",
            "catchUpAutomatically": True,
        }
        rule = RepetitionRule.model_validate(data)
        assert rule.rule_string == "FREQ=DAILY"
        assert rule.schedule_type == ScheduleType.REGULARLY
        assert rule.anchor_date_key == AnchorDateKey.DUE_DATE
        assert rule.catch_up_automatically is True

    def test_repetition_rule_missing_field_rejected(self) -> None:
        """All 4 fields are required."""
        data = {"ruleString": "FREQ=DAILY"}
        with pytest.raises(ValidationError):
            RepetitionRule.model_validate(data)

    def test_repetition_rule_invalid_schedule_type_rejected(self) -> None:
        data = {
            "ruleString": "FREQ=DAILY",
            "scheduleType": "InvalidType",
            "anchorDateKey": "DueDate",
            "catchUpAutomatically": False,
        }
        with pytest.raises(ValidationError):
            RepetitionRule.model_validate(data)


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
            url="omnifocus:///test/test-1",
            added=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            modified=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            active=True,
            effective_active=True,
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
        entity = OmniFocusEntity(
            id="abc",
            name="Test",
            url="omnifocus:///test/abc",
            added=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            modified=datetime(2024, 1, 15, 10, 30, tzinfo=UTC),
            active=True,
            effective_active=True,
        )
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
            url="omnifocus:///test/test-1",
            added=dt,
            modified=dt,
            active=True,
            effective_active=True,
            note="A note",
            completed=False,
            completed_by_children=False,
            flagged=True,
            effective_flagged=True,
            sequential=False,
            due_date=dt,
            has_children=False,
            should_use_floating_time_zone=False,
            tags=[TagRef(id="tag-001", name="errands")],
        )
        assert entity.due_date == dt
        assert entity.flagged is True
        assert len(entity.tags) == 1
        assert isinstance(entity.tags[0], TagRef)
        assert entity.tags[0].name == "errands"


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
        """make_project_dict returns exactly 36 fields (all bridge project fields)."""
        d = make_project_dict()
        assert len(d) == 36

    def test_make_tag_dict_field_count(self) -> None:
        """make_tag_dict returns exactly 11 fields (all bridge tag fields)."""
        d = make_tag_dict()
        assert len(d) == 11

    def test_make_folder_dict_field_count(self) -> None:
        """make_folder_dict returns exactly 9 fields (all bridge folder fields)."""
        d = make_folder_dict()
        assert len(d) == 9

    def test_make_perspective_dict_field_count(self) -> None:
        """make_perspective_dict returns exactly 2 fields (id and name only)."""
        d = make_perspective_dict()
        assert len(d) == 2

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
            tags=[{"id": "t1", "name": "errands"}, {"id": "t2", "name": "morning"}],
        )
        task = Task.model_validate(data)

        # Identity
        assert task.id == "task-001"
        assert task.name == "Test Task"
        assert task.url == "omnifocus:///task/task-001"
        assert task.note == ""

        # Lifecycle (inherited from OmniFocusEntity)
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

        # Tags are TagRef objects
        assert len(task.tags) == 2
        assert isinstance(task.tags[0], TagRef)
        assert task.tags[0].name == "errands"
        assert task.tags[0].id == "t1"
        assert task.tags[1].name == "morning"

        # Verify total field count
        assert len(Task.model_fields) == 32

        # Serialize back to camelCase and verify round-trip
        dumped = task.model_dump(mode="json", by_alias=True)
        assert "dueDate" in dumped
        assert "effectiveFlagged" in dumped
        assert "inInbox" in dumped
        assert "url" in dumped

        # Re-parse and compare
        task2 = Task.model_validate(dumped)
        assert task.id == task2.id
        assert task.due_date == task2.due_date
        assert len(task2.tags) == 2
        assert task2.tags[0].name == "errands"

    def test_task_status_required(self) -> None:
        """Task without status raises ValidationError."""
        data = make_task_dict()
        del data["status"]
        with pytest.raises(ValidationError):
            Task.model_validate(data)

    def test_task_tags_are_tag_refs(self) -> None:
        """tags field contains TagRef objects with id and name."""
        data = make_task_dict(
            tags=[{"id": "t1", "name": "errands"}, {"id": "t2", "name": "morning"}],
        )
        task = Task.model_validate(data)
        assert len(task.tags) == 2
        assert isinstance(task.tags[0], TagRef)
        assert task.tags[0].name == "errands"
        assert task.tags[0].id == "t1"

    def test_task_optional_relationships_default_none(self) -> None:
        """Optional relationship fields (project, parent) default to None."""
        data = make_task_dict()
        task = Task.model_validate(data)
        assert task.project is None
        assert task.parent is None


# ---------------------------------------------------------------------------
# Project model tests (MODL-02)
# ---------------------------------------------------------------------------


class TestProjectModel:
    """Project model parses all 36 bridge fields including nested objects."""

    def test_project_from_bridge_json(self) -> None:
        """Parse make_project_dict(), verify all 36 fields, both status fields present."""
        data = make_project_dict()
        project = Project.model_validate(data)

        # Identity + lifecycle from OmniFocusEntity
        assert project.id == "proj-001"
        assert project.name == "Test Project"
        assert project.url == "omnifocus:///project/proj-001"
        assert project.note == ""
        assert project.active is True
        assert project.effective_active is True
        assert project.added is not None
        assert project.modified is not None

        # Dual status
        assert project.status == ProjectStatus.ACTIVE
        assert project.task_status == TaskStatus.AVAILABLE

        # Structure
        assert project.contains_singleton_actions is False

        # Completion
        assert project.completed is False
        assert project.completed_by_children is False

        # Review (required per BRIDGE-SPEC)
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
        assert len(Project.model_fields) == 36

        # Serialize back and verify camelCase keys
        dumped = project.model_dump(mode="json", by_alias=True)
        assert "taskStatus" in dumped
        assert "containsSingletonActions" in dumped
        assert "lastReviewDate" in dumped
        assert "reviewInterval" in dumped
        assert "nextTask" in dumped
        assert "url" in dumped

    def test_project_dual_status_fields(self) -> None:
        """Project has both status (ProjectStatus) and task_status (TaskStatus)."""
        data = make_project_dict(status="Dropped", taskStatus="Blocked")
        project = Project.model_validate(data)
        assert project.status == ProjectStatus.DROPPED
        assert project.task_status == TaskStatus.BLOCKED

    def test_project_nested_repetition_rule(self) -> None:
        """Project with repetitionRule object parses correctly."""
        data = make_project_dict(
            repetitionRule={
                "ruleString": "FREQ=WEEKLY",
                "scheduleType": "Regularly",
                "anchorDateKey": "DueDate",
                "catchUpAutomatically": False,
            },
        )
        project = Project.model_validate(data)
        assert project.repetition_rule is not None
        assert project.repetition_rule.rule_string == "FREQ=WEEKLY"
        assert project.repetition_rule.schedule_type == ScheduleType.REGULARLY
        assert project.repetition_rule.anchor_date_key == AnchorDateKey.DUE_DATE
        assert project.repetition_rule.catch_up_automatically is False

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
    """Tag model parses all 11 bridge fields."""

    def test_tag_from_bridge_json(self) -> None:
        """Parse make_tag_dict(), verify all 11 fields."""
        data = make_tag_dict()
        tag = Tag.model_validate(data)

        assert tag.id == "tag-001"
        assert tag.name == "Test Tag"
        assert tag.url == "omnifocus:///tag/tag-001"
        assert tag.added is not None
        assert tag.modified is not None
        assert tag.active is True
        assert tag.effective_active is True
        assert tag.status == TagStatus.ACTIVE
        assert tag.allows_next_action is True
        assert tag.children_are_mutually_exclusive is False
        assert tag.parent is None

        # Verify total field count
        assert len(Tag.model_fields) == 11

        # Round-trip
        dumped = tag.model_dump(mode="json", by_alias=True)
        assert "allowsNextAction" in dumped
        assert "effectiveActive" in dumped
        assert "childrenAreMutuallyExclusive" in dumped
        tag2 = Tag.model_validate(dumped)
        assert tag.id == tag2.id

    def test_tag_status_required(self) -> None:
        """Tag without status raises ValidationError."""
        data = make_tag_dict()
        del data["status"]
        with pytest.raises(ValidationError):
            Tag.model_validate(data)


# ---------------------------------------------------------------------------
# Folder model tests (MODL-04)
# ---------------------------------------------------------------------------


class TestFolderModel:
    """Folder model parses all 9 bridge fields."""

    def test_folder_from_bridge_json(self) -> None:
        """Parse make_folder_dict(), verify all 9 fields."""
        data = make_folder_dict()
        folder = Folder.model_validate(data)

        assert folder.id == "folder-001"
        assert folder.name == "Test Folder"
        assert folder.url == "omnifocus:///folder/folder-001"
        assert folder.added is not None
        assert folder.modified is not None
        assert folder.active is True
        assert folder.effective_active is True
        assert folder.status == FolderStatus.ACTIVE
        assert folder.parent is None

        # Verify total field count
        assert len(Folder.model_fields) == 9

        # Round-trip
        dumped = folder.model_dump(mode="json", by_alias=True)
        assert "effectiveActive" in dumped
        folder2 = Folder.model_validate(dumped)
        assert folder.id == folder2.id

    def test_folder_status_required(self) -> None:
        """Folder without status raises ValidationError."""
        data = make_folder_dict()
        del data["status"]
        with pytest.raises(ValidationError):
            Folder.model_validate(data)


# ---------------------------------------------------------------------------
# Perspective model tests (MODL-05)
# ---------------------------------------------------------------------------


class TestPerspectiveModel:
    """Perspective model has id: str | None, name: str, builtin: computed."""

    def test_perspective_from_bridge_json(self) -> None:
        """Parse make_perspective_dict(), verify 2 stored + 1 computed fields."""
        data = make_perspective_dict()
        perspective = Perspective.model_validate(data)

        assert perspective.id == "persp-001"
        assert perspective.name == "Test Perspective"
        assert perspective.builtin is False

        # Verify stored field count (builtin is computed, not in model_fields)
        assert len(Perspective.model_fields) == 2
        assert len(Perspective.model_computed_fields) == 1
        assert "builtin" in Perspective.model_computed_fields

        # Round-trip
        dumped = perspective.model_dump(mode="json", by_alias=True)
        perspective2 = Perspective.model_validate(dumped)
        assert perspective.id == perspective2.id

    def test_perspective_builtin_null_id(self) -> None:
        """Perspective with id=null is computed as builtin."""
        data = make_perspective_dict(id=None, name="Inbox")
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
                    tags=[{"id": "tref1", "name": "errands"}],
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
                make_perspective_dict(id=None, name="Inbox"),
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
        assert len(snapshot2.tasks[1].tags) == 1
        assert snapshot2.tasks[1].tags[0].name == "errands"
        assert snapshot2.tasks[1].project == "proj-001"
        assert snapshot2.projects[1].status == ProjectStatus.DROPPED
        assert snapshot2.perspectives[1].id is None
        assert snapshot2.perspectives[1].builtin is True

        # Verify complete round-trip: compare all task IDs
        original_task_ids = [t["id"] for t in data["tasks"]]
        parsed_task_ids = [t.id for t in snapshot2.tasks]
        assert original_task_ids == parsed_task_ids
