"""Tests for base model config, enums, and common models (MODL-07)."""

from __future__ import annotations

from datetime import datetime, timezone

import pytest
from pydantic import ValidationError

from omnifocus_operator.models import (
    ActionableEntity,
    EntityStatus,
    OmniFocusBaseModel,
    OmniFocusEntity,
    RepetitionRule,
    ReviewInterval,
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
    """Verify OmniFocusBaseModel ConfigDict: alias_generator, validate_by_name, validate_by_alias."""

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
        dt = datetime(2024, 1, 15, 10, 30, tzinfo=timezone.utc)
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
