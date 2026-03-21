"""Tests for OmniFocus models: base config, enums, common (MODL-07) and entities (MODL-01..06)."""

from __future__ import annotations

from datetime import UTC, datetime

import pytest
from pydantic import AwareDatetime, ValidationError

from omnifocus_operator.contracts.base import _Unset
from omnifocus_operator.contracts.common import MoveAction, TagAction
from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand, AddTaskResult
from omnifocus_operator.contracts.use_cases.edit_task import (
    EditTaskActions,
    EditTaskCommand,
    EditTaskResult,
)
from omnifocus_operator.models import (
    ActionableEntity,
    AllEntities,
    AnchorDateKey,
    Availability,
    Folder,
    FolderAvailability,
    OmniFocusBaseModel,
    OmniFocusEntity,
    ParentRef,
    Perspective,
    Project,
    RepetitionRule,
    ReviewInterval,
    ScheduleType,
    Tag,
    TagAvailability,
    TagRef,
    Task,
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


class TestTagAvailability:
    """TagAvailability enum has exactly 3 members."""

    def test_tag_availability_values(self) -> None:
        assert TagAvailability.AVAILABLE == "available"
        assert TagAvailability.BLOCKED == "blocked"
        assert TagAvailability.DROPPED == "dropped"

    def test_tag_availability_member_count(self) -> None:
        assert len(TagAvailability) == 3


class TestFolderAvailability:
    """FolderAvailability enum has exactly 2 members."""

    def test_folder_availability_values(self) -> None:
        assert FolderAvailability.AVAILABLE == "available"
        assert FolderAvailability.DROPPED == "dropped"

    def test_folder_availability_member_count(self) -> None:
        assert len(FolderAvailability) == 2


class TestScheduleType:
    """ScheduleType enum has exactly 2 members with snake_case values."""

    def test_schedule_type_values(self) -> None:
        assert ScheduleType.REGULARLY == "regularly"
        assert ScheduleType.FROM_COMPLETION == "from_completion"

    def test_schedule_type_member_count(self) -> None:
        assert len(ScheduleType) == 2


class TestAnchorDateKey:
    """AnchorDateKey enum has exactly 3 members with snake_case values."""

    def test_anchor_date_key_values(self) -> None:
        assert AnchorDateKey.DUE_DATE == "due_date"
        assert AnchorDateKey.DEFER_DATE == "defer_date"
        assert AnchorDateKey.PLANNED_DATE == "planned_date"

    def test_anchor_date_key_member_count(self) -> None:
        assert len(AnchorDateKey) == 3


class TestEnumValidation:
    """Enums used in Pydantic models reject unknown values."""

    def test_enum_unknown_value_rejected(self) -> None:
        """Parsing an invalid urgency string raises ValidationError."""

        class StatusModel(OmniFocusBaseModel):
            urgency: Urgency

        with pytest.raises(ValidationError):
            StatusModel(urgency="InvalidStatus")


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


class TestParentRef:
    """ParentRef model with type, id, and name."""

    def test_parent_ref_round_trip(self) -> None:
        data = {"type": "project", "id": "proj-001", "name": "My Project"}
        ref = ParentRef.model_validate(data)
        assert ref.type == "project"
        assert ref.id == "proj-001"
        assert ref.name == "My Project"
        dumped = ref.model_dump(by_alias=True)
        assert dumped == {"type": "project", "id": "proj-001", "name": "My Project"}

    def test_parent_ref_task_type(self) -> None:
        data = {"type": "task", "id": "task-parent-001", "name": "Parent Task"}
        ref = ParentRef.model_validate(data)
        assert ref.type == "task"
        assert ref.id == "task-parent-001"
        assert ref.name == "Parent Task"


class TestRepetitionRule:
    """RepetitionRule has 4 required typed fields."""

    def test_repetition_rule_full_round_trip(self) -> None:
        data = {
            "ruleString": "FREQ=DAILY",
            "scheduleType": "regularly",
            "anchorDateKey": "due_date",
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
            "anchorDateKey": "due_date",
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
            urgency=Urgency.NONE,
            availability=Availability.AVAILABLE,
            note="",
            flagged=False,
            effective_flagged=False,
            has_children=False,
            tags=[],
        )
        assert entity.due_date is None
        assert entity.defer_date is None
        assert entity.effective_due_date is None
        assert entity.effective_defer_date is None
        assert entity.completion_date is None
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
            urgency=Urgency.NONE,
            availability=Availability.AVAILABLE,
            note="A note",
            flagged=True,
            effective_flagged=True,
            due_date=dt,
            has_children=False,
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
    """Factory functions produce valid new-shape dicts with correct field counts."""

    def test_make_task_dict_field_count(self) -> None:
        """make_task_dict returns exactly 26 fields (new model shape with unified parent)."""
        d = make_task_dict()
        assert len(d) == 26

    def test_make_task_dict_overrides(self) -> None:
        """make_task_dict supports keyword overrides."""
        d = make_task_dict(name="Custom Task", urgency="overdue")
        assert d["name"] == "Custom Task"
        assert d["urgency"] == "overdue"

    def test_make_project_dict_field_count(self) -> None:
        """make_project_dict returns exactly 28 fields (no effectiveCompletionDate)."""
        d = make_project_dict()
        assert len(d) == 28

    def test_make_tag_dict_field_count(self) -> None:
        """make_tag_dict returns exactly 8 fields (new model shape)."""
        d = make_tag_dict()
        assert len(d) == 8

    def test_make_folder_dict_field_count(self) -> None:
        """make_folder_dict returns exactly 7 fields (new model shape)."""
        d = make_folder_dict()
        assert len(d) == 7

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
    """Task model parses all 26 fields with snake_case names and camelCase aliases."""

    def test_task_from_bridge_json(self) -> None:
        """Parse make_task_dict() via Task.model_validate(), verify all 26 fields."""
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

        # Two-axis status
        assert task.urgency == Urgency.NONE
        assert task.availability == Availability.AVAILABLE

        # Flags
        assert task.flagged is False
        assert task.effective_flagged is False

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

        # Relationships
        assert task.in_inbox is True
        assert task.repetition_rule is None
        assert task.parent is None

        # Tags are TagRef objects
        assert len(task.tags) == 2
        assert isinstance(task.tags[0], TagRef)
        assert task.tags[0].name == "errands"
        assert task.tags[0].id == "t1"
        assert task.tags[1].name == "morning"

        # Verify total field count (26 after merging project+parent into single parent)
        assert len(Task.model_fields) == 26

        # Serialize back to camelCase and verify round-trip
        dumped = task.model_dump(mode="json", by_alias=True)
        assert "dueDate" in dumped
        assert "effectiveFlagged" in dumped
        assert "inInbox" in dumped
        assert "url" in dumped
        assert "urgency" in dumped
        assert "availability" in dumped

        # Re-parse and compare
        task2 = Task.model_validate(dumped)
        assert task.id == task2.id
        assert task.due_date == task2.due_date
        assert len(task2.tags) == 2
        assert task2.tags[0].name == "errands"

    def test_task_urgency_required(self) -> None:
        """Task without urgency raises ValidationError."""
        data = make_task_dict()
        del data["urgency"]
        with pytest.raises(ValidationError):
            Task.model_validate(data)

    def test_task_availability_required(self) -> None:
        """Task without availability raises ValidationError."""
        data = make_task_dict()
        del data["availability"]
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

    def test_task_parent_none_for_inbox(self) -> None:
        """Inbox task has parent=None."""
        data = make_task_dict()
        task = Task.model_validate(data)
        assert task.parent is None

    def test_task_parent_ref_project(self) -> None:
        """Task in project has parent as ParentRef with type='project'."""
        data = make_task_dict(parent={"type": "project", "id": "proj-001", "name": "My Project"})
        task = Task.model_validate(data)
        assert task.parent is not None
        assert isinstance(task.parent, ParentRef)
        assert task.parent.type == "project"
        assert task.parent.id == "proj-001"
        assert task.parent.name == "My Project"

    def test_task_parent_ref_task(self) -> None:
        """Subtask has parent as ParentRef with type='task'."""
        data = make_task_dict(parent={"type": "task", "id": "task-parent", "name": "Parent Task"})
        task = Task.model_validate(data)
        assert task.parent is not None
        assert isinstance(task.parent, ParentRef)
        assert task.parent.type == "task"
        assert task.parent.id == "task-parent"


# ---------------------------------------------------------------------------
# Project model tests (MODL-02)
# ---------------------------------------------------------------------------


class TestProjectModel:
    """Project model parses all 28 fields including nested objects."""

    def test_project_from_bridge_json(self) -> None:
        """Parse make_project_dict(), verify all 28 fields."""
        data = make_project_dict()
        project = Project.model_validate(data)

        # Identity + lifecycle from OmniFocusEntity
        assert project.id == "proj-001"
        assert project.name == "Test Project"
        assert project.url == "omnifocus:///project/proj-001"
        assert project.note == ""
        assert project.added is not None
        assert project.modified is not None

        # Two-axis status
        assert project.urgency == Urgency.NONE
        assert project.availability == Availability.AVAILABLE

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

        # Verify total field count (no effectiveCompletionDate -- Task-only)
        assert len(Project.model_fields) == 28

        # Serialize back and verify camelCase keys
        dumped = project.model_dump(mode="json", by_alias=True)
        assert "urgency" in dumped
        assert "availability" in dumped
        assert "lastReviewDate" in dumped
        assert "reviewInterval" in dumped
        assert "nextTask" in dumped
        assert "url" in dumped

    def test_project_status_axes(self) -> None:
        """Project uses urgency + availability two-axis model."""
        data = make_project_dict(urgency="overdue", availability="blocked")
        project = Project.model_validate(data)
        assert project.urgency == Urgency.OVERDUE
        assert project.availability == Availability.BLOCKED

    def test_project_nested_repetition_rule(self) -> None:
        """Project with repetitionRule object parses correctly."""
        data = make_project_dict(
            repetitionRule={
                "ruleString": "FREQ=WEEKLY",
                "scheduleType": "regularly",
                "anchorDateKey": "due_date",
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
    """Tag model parses all 8 fields."""

    def test_tag_from_bridge_json(self) -> None:
        """Parse make_tag_dict(), verify all 8 fields."""
        data = make_tag_dict()
        tag = Tag.model_validate(data)

        assert tag.id == "tag-001"
        assert tag.name == "Test Tag"
        assert tag.url == "omnifocus:///tag/tag-001"
        assert tag.added is not None
        assert tag.modified is not None
        assert tag.availability == TagAvailability.AVAILABLE
        assert tag.children_are_mutually_exclusive is False
        assert tag.parent is None

        # Verify total field count
        assert len(Tag.model_fields) == 8

        # Round-trip
        dumped = tag.model_dump(mode="json", by_alias=True)
        assert "childrenAreMutuallyExclusive" in dumped
        tag2 = Tag.model_validate(dumped)
        assert tag.id == tag2.id

    def test_tag_availability_required(self) -> None:
        """Tag without availability raises ValidationError."""
        data = make_tag_dict()
        del data["availability"]
        with pytest.raises(ValidationError):
            Tag.model_validate(data)


# ---------------------------------------------------------------------------
# Folder model tests (MODL-04)
# ---------------------------------------------------------------------------


class TestFolderModel:
    """Folder model parses all 7 fields."""

    def test_folder_from_bridge_json(self) -> None:
        """Parse make_folder_dict(), verify all 7 fields."""
        data = make_folder_dict()
        folder = Folder.model_validate(data)

        assert folder.id == "folder-001"
        assert folder.name == "Test Folder"
        assert folder.url == "omnifocus:///folder/folder-001"
        assert folder.added is not None
        assert folder.modified is not None
        assert folder.availability == FolderAvailability.AVAILABLE
        assert folder.parent is None

        # Verify total field count
        assert len(Folder.model_fields) == 7

        # Round-trip
        dumped = folder.model_dump(mode="json", by_alias=True)
        folder2 = Folder.model_validate(dumped)
        assert folder.id == folder2.id

    def test_folder_availability_required(self) -> None:
        """Folder without availability raises ValidationError."""
        data = make_folder_dict()
        del data["availability"]
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
# AllEntities tests (MODL-06)
# ---------------------------------------------------------------------------


class TestAllEntities:
    """AllEntities aggregates tasks, projects, tags, folders, perspectives lists."""

    def test_all_entities_round_trip(self) -> None:
        """Parse make_snapshot_dict(), verify collections, serialize and re-parse."""
        data = make_snapshot_dict()
        snapshot = AllEntities.model_validate(data)

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
        snapshot2 = AllEntities.model_validate(dumped)
        assert len(snapshot2.tasks) == 1
        assert snapshot2.tasks[0].id == snapshot.tasks[0].id

    def test_all_entities_empty_collections(self) -> None:
        """AllEntities with empty lists is valid."""
        data = make_snapshot_dict(tasks=[], projects=[], tags=[], folders=[], perspectives=[])
        snapshot = AllEntities.model_validate(data)
        assert len(snapshot.tasks) == 0
        assert len(snapshot.projects) == 0
        assert len(snapshot.tags) == 0
        assert len(snapshot.folders) == 0
        assert len(snapshot.perspectives) == 0

    def test_full_bridge_payload_round_trip(self) -> None:
        """Large payload with multiple entities round-trips without data loss."""
        data = {
            "tasks": [
                make_task_dict(id="t1", name="Task 1", urgency="none", availability="available"),
                make_task_dict(
                    id="t2",
                    name="Task 2",
                    urgency="due_soon",
                    availability="available",
                    dueDate="2024-06-15T09:00:00.000Z",
                    tags=[{"id": "tref1", "name": "errands"}],
                    parent={"type": "project", "id": "proj-001", "name": "Project A"},
                ),
                make_task_dict(
                    id="t3",
                    name="Task 3",
                    urgency="none",
                    availability="completed",
                ),
            ],
            "projects": [
                make_project_dict(id="p1", name="Project A"),
                make_project_dict(
                    id="p2",
                    name="Project B",
                    urgency="none",
                    availability="dropped",
                    folder="folder-001",
                ),
            ],
            "tags": [
                make_tag_dict(id="tg1", name="errands"),
                make_tag_dict(id="tg2", name="morning"),
            ],
            "folders": [
                make_folder_dict(id="f1", name="Work"),
            ],
            "perspectives": [
                make_perspective_dict(id="ps1", name="Custom View"),
                make_perspective_dict(id=None, name="Inbox"),
            ],
        }

        snapshot = AllEntities.model_validate(data)
        assert len(snapshot.tasks) == 3
        assert len(snapshot.projects) == 2
        assert len(snapshot.tags) == 2
        assert len(snapshot.folders) == 1
        assert len(snapshot.perspectives) == 2

        # Full round-trip
        dumped = snapshot.model_dump(mode="json", by_alias=True)
        snapshot2 = AllEntities.model_validate(dumped)

        # Verify data fidelity
        assert snapshot2.tasks[1].due_date is not None
        assert len(snapshot2.tasks[1].tags) == 1
        assert snapshot2.tasks[1].tags[0].name == "errands"
        assert snapshot2.tasks[1].parent is not None
        assert snapshot2.tasks[1].parent.type == "project"
        assert snapshot2.tasks[1].parent.id == "proj-001"
        assert snapshot2.projects[1].availability == Availability.DROPPED
        assert snapshot2.perspectives[1].id is None
        assert snapshot2.perspectives[1].builtin is True

        # Verify complete round-trip: compare all task IDs
        original_task_ids = [t["id"] for t in data["tasks"]]
        parsed_task_ids = [t.id for t in snapshot2.tasks]
        assert original_task_ids == parsed_task_ids


# ---------------------------------------------------------------------------
# Write model tests
# ---------------------------------------------------------------------------


class TestWriteModels:
    """AddTaskCommand and AddTaskResult write models."""

    def test_task_create_spec_minimal(self) -> None:
        """AddTaskCommand with only name (required) creates valid instance."""
        spec = AddTaskCommand(name="Buy groceries")
        assert spec.name == "Buy groceries"
        assert spec.parent is None
        assert spec.tags is None
        assert spec.due_date is None
        assert spec.defer_date is None
        assert spec.planned_date is None
        assert spec.flagged is None
        assert spec.estimated_minutes is None
        assert spec.note is None

    def test_task_create_spec_all_fields(self) -> None:
        """AddTaskCommand with all fields populated."""
        dt = datetime(2024, 6, 15, 9, 0, tzinfo=UTC)
        spec = AddTaskCommand(
            name="Full task",
            parent="proj-001",
            tags=["errands", "morning"],
            due_date=dt,
            defer_date=dt,
            planned_date=dt,
            flagged=True,
            estimated_minutes=30.0,
            note="A note",
        )
        assert spec.name == "Full task"
        assert spec.parent == "proj-001"
        assert spec.tags == ["errands", "morning"]
        assert spec.due_date == dt
        assert spec.defer_date == dt
        assert spec.planned_date == dt
        assert spec.flagged is True
        assert spec.estimated_minutes == 30.0
        assert spec.note == "A note"

    def test_task_create_spec_rejects_missing_name(self) -> None:
        """AddTaskCommand without name raises ValidationError."""
        with pytest.raises(ValidationError):
            AddTaskCommand()  # type: ignore[call-arg]

    def test_task_create_spec_camel_case_serialization(self) -> None:
        """AddTaskCommand serializes to camelCase via OmniFocusBaseModel."""
        dt = datetime(2024, 6, 15, 9, 0, tzinfo=UTC)
        spec = AddTaskCommand(
            name="Test",
            due_date=dt,
            defer_date=dt,
            planned_date=dt,
            estimated_minutes=15.0,
        )
        dumped = spec.model_dump(by_alias=True)
        assert "dueDate" in dumped
        assert "deferDate" in dumped
        assert "plannedDate" in dumped
        assert "estimatedMinutes" in dumped
        # snake_case keys should NOT be present
        assert "due_date" not in dumped
        assert "defer_date" not in dumped

    def test_task_create_result_round_trip(self) -> None:
        """AddTaskResult parses and serializes correctly."""
        result = AddTaskResult(success=True, id="task-new-001", name="New Task")
        assert result.success is True
        assert result.id == "task-new-001"
        assert result.name == "New Task"

        # camelCase round-trip (fields are already camelCase-friendly)
        dumped = result.model_dump(by_alias=True)
        result2 = AddTaskResult.model_validate(dumped)
        assert result2.success is True
        assert result2.id == "task-new-001"
        assert result2.name == "New Task"


class TestActionsSpecLifecycle:
    """ActionsSpec.lifecycle validates to Literal['complete', 'drop']."""

    def test_lifecycle_complete_valid(self) -> None:
        """EditTaskActions(lifecycle='complete') validates successfully."""
        spec = EditTaskActions(lifecycle="complete")
        assert spec.lifecycle == "complete"

    def test_lifecycle_drop_valid(self) -> None:
        """EditTaskActions(lifecycle='drop') validates successfully."""
        spec = EditTaskActions(lifecycle="drop")
        assert spec.lifecycle == "drop"

    def test_lifecycle_reopen_rejected(self) -> None:
        """EditTaskActions(lifecycle='reopen') raises ValidationError."""
        with pytest.raises(ValidationError):
            EditTaskActions(lifecycle="reopen")

    def test_lifecycle_invalid_rejected(self) -> None:
        """EditTaskActions(lifecycle='invalid') raises ValidationError."""
        with pytest.raises(ValidationError):
            EditTaskActions(lifecycle="invalid")


class TestWriteModelStrictness:
    """Write models reject unknown fields (STRCT-01); read models stay permissive (STRCT-02)."""

    # --- STRCT-01: Write models reject unknown fields ---

    def test_task_create_spec_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="bogus_field"):
            AddTaskCommand.model_validate({"name": "Task", "bogus_field": "x"})

    def test_task_edit_spec_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="bogus_field"):
            EditTaskCommand.model_validate({"id": "t1", "bogus_field": "x"})

    def test_move_to_spec_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="bogus_field"):
            MoveAction.model_validate({"ending": "p1", "bogus_field": "x"})

    def test_tag_action_spec_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="bogus_field"):
            TagAction.model_validate({"add": ["tag1"], "bogus_field": "x"})

    def test_actions_spec_rejects_unknown_field(self) -> None:
        with pytest.raises(ValidationError, match="bogus_field"):
            EditTaskActions.model_validate({"lifecycle": "complete", "bogus_field": "x"})

    # --- STRCT-02: Read/result models stay permissive ---

    def test_task_create_result_accepts_unknown_field(self) -> None:
        result = AddTaskResult.model_validate(
            {"success": True, "id": "t1", "name": "T", "bogus": "x"}
        )
        assert result.success is True
        assert not hasattr(result, "bogus")

    def test_task_edit_result_accepts_unknown_field(self) -> None:
        result = EditTaskResult.model_validate(
            {"success": True, "id": "t1", "name": "T", "bogus": "x"}
        )
        assert result.success is True
        assert not hasattr(result, "bogus")

    def test_read_model_task_accepts_unknown_field(self) -> None:
        """Read models from OmniFocus must stay permissive for forward compatibility."""
        data = make_task_dict()
        data["some_future_field"] = "unknown"
        task = Task.model_validate(data)
        assert task.name is not None
        assert not hasattr(task, "some_future_field")

    # --- STRCT-03: UNSET sentinel works with extra=forbid ---

    def test_task_edit_spec_unset_defaults_with_forbid(self) -> None:
        """All UNSET defaults validate successfully -- they are declared fields, not extra."""
        spec = EditTaskCommand(id="t1")
        assert spec.id == "t1"
        assert isinstance(spec.name, _Unset)
        assert isinstance(spec.flagged, _Unset)
        assert isinstance(spec.note, _Unset)
        assert isinstance(spec.due_date, _Unset)
        assert isinstance(spec.actions, _Unset)

    def test_task_edit_spec_set_values_with_forbid(self) -> None:
        """Setting real values on write models still works under forbid."""
        spec = EditTaskCommand(id="t1", name="Updated", flagged=True)
        assert spec.name == "Updated"
        assert spec.flagged is True

    def test_write_model_accepts_camel_case_alias(self) -> None:
        """Agents send camelCase -- must be accepted under forbid."""
        spec = AddTaskCommand.model_validate(
            {
                "name": "Test",
                "dueDate": "2024-06-15T09:00:00Z",
                "deferDate": "2024-06-15T09:00:00Z",
                "estimatedMinutes": 30,
            }
        )
        assert spec.name == "Test"
        assert spec.estimated_minutes == 30

    # --- Schema generation: agent-visible JSON schema is clean ---

    def test_edit_command_schema_only_id_required(self) -> None:
        """Only 'id' is required — all UNSET-defaulted fields are optional."""
        schema = EditTaskCommand.model_json_schema()
        assert schema["required"] == ["id"]

    def test_edit_command_schema_non_nullable_fields(self) -> None:
        """Non-nullable UNSET fields appear as their plain type."""
        props = EditTaskCommand.model_json_schema()["properties"]
        assert props["name"]["type"] == "string"
        assert props["flagged"]["type"] == "boolean"
        assert "anyOf" not in props["name"]
        assert "anyOf" not in props["flagged"]

    def test_edit_command_schema_nullable_fields(self) -> None:
        """Nullable UNSET fields appear as anyOf[real_type, null] — exactly two branches."""
        props = EditTaskCommand.model_json_schema()["properties"]
        assert len(props["note"]["anyOf"]) == 2
        note_types = {b.get("type") for b in props["note"]["anyOf"]}
        assert note_types == {"string", "null"}
        assert len(props["dueDate"]["anyOf"]) == 2
        due_types = {b.get("type") for b in props["dueDate"]["anyOf"]}
        assert due_types == {"string", "null"}

    def test_edit_actions_schema_all_optional(self) -> None:
        """EditTaskActions: tags, move, lifecycle are all optional."""
        schema = EditTaskActions.model_json_schema()
        assert schema.get("required", []) == []

    def test_tag_action_schema_fields(self) -> None:
        """TagAction: add/remove are arrays, replace is nullable array."""
        props = TagAction.model_json_schema()["properties"]
        assert props["add"]["type"] == "array"
        assert props["remove"]["type"] == "array"
        replace_types = {b.get("type") for b in props["replace"]["anyOf"]}
        assert replace_types == {"array", "null"}
