"""Tests for OperatorService, ConstantMtimeSource, and bridge factory.

Covers the service layer (thin passthrough to repository), the constant
mtime source (always returns 0 for InMemoryBridge usage), and the bridge
factory function (creates the appropriate bridge implementation).
"""

from __future__ import annotations

import logging
from datetime import UTC, date, datetime
from typing import TYPE_CHECKING
from unittest.mock import AsyncMock

import pytest
from pydantic import ValidationError

from omnifocus_operator.bridge import BridgeError
from omnifocus_operator.bridge.mtime import MtimeSource
from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
from omnifocus_operator.contracts.shared.repetition_rule import (
    EndByDateSpec,
    EndByOccurrencesSpec,
    FrequencyAddSpec,
    FrequencyEditSpec,
    RepetitionRuleAddSpec,
    RepetitionRuleEditSpec,
)
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand, AddTaskResult
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskActions,
    EditTaskCommand,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    OrdinalWeekday,
)
from omnifocus_operator.service import ErrorOperatorService, OperatorService
from omnifocus_operator.service.domain import DomainLogic
from tests.doubles import ConstantMtimeSource

from .conftest import make_project_dict, make_tag_dict, make_task_dict

if TYPE_CHECKING:
    from omnifocus_operator.repository import BridgeOnlyRepository

# ---------------------------------------------------------------------------
# OperatorService
# ---------------------------------------------------------------------------


class TestOperatorService:
    """OperatorService delegates to repository and passes through results."""

    async def test_get_all_data_returns_snapshot(self, service: OperatorService) -> None:
        result = await service.get_all_data()

        assert len(result.tasks) == 1
        assert len(result.projects) == 1
        assert len(result.tags) == 1
        assert len(result.folders) == 1
        assert len(result.perspectives) == 1

    async def test_get_all_data_delegates_to_repository(self, service: OperatorService) -> None:
        """Service returns a complete snapshot from the repository."""
        result = await service.get_all_data()

        # BridgeOnlyRepository deserializes fresh each call; verify structural equality
        assert len(result.tasks) == 1
        assert result.tasks[0].id == "task-001"
        assert len(result.projects) == 1
        assert result.projects[0].id == "proj-001"

    async def test_get_all_data_propagates_errors(self) -> None:
        """Service propagates errors from the repository unchanged."""

        mock_repo = AsyncMock()
        mock_repo.get_all.side_effect = BridgeError("snapshot", "connection lost")
        service = OperatorService(repository=mock_repo)

        with pytest.raises(BridgeError, match="connection lost"):
            await service.get_all_data()

    async def test_get_task_delegates_to_repository(self, service: OperatorService) -> None:
        """Service.get_task delegates to repository and returns result."""
        result = await service.get_task("task-001")
        assert result is not None
        assert result.id == "task-001"

    async def test_get_task_raises_when_not_found(self, service: OperatorService) -> None:
        with pytest.raises(ValueError, match="Task not found: nonexistent"):
            await service.get_task("nonexistent")

    async def test_get_project_delegates_to_repository(self, service: OperatorService) -> None:
        result = await service.get_project("proj-001")
        assert result is not None
        assert result.id == "proj-001"

    async def test_get_project_raises_when_not_found(self, service: OperatorService) -> None:
        with pytest.raises(ValueError, match="Project not found: nonexistent"):
            await service.get_project("nonexistent")

    async def test_get_tag_delegates_to_repository(self, service: OperatorService) -> None:
        result = await service.get_tag("tag-001")
        assert result is not None
        assert result.id == "tag-001"

    async def test_get_tag_raises_when_not_found(self, service: OperatorService) -> None:
        with pytest.raises(ValueError, match="Tag not found: nonexistent"):
            await service.get_tag("nonexistent")


# ---------------------------------------------------------------------------
# OperatorService.add_task
# ---------------------------------------------------------------------------


class TestAddTask:
    """Service.add_task validates inputs and delegates to repository."""

    async def test_create_minimal(self, service: OperatorService) -> None:
        """Name-only command creates task and returns AddTaskResult."""
        result = await service.add_task(AddTaskCommand(name="Buy milk"))

        assert isinstance(result, AddTaskResult)
        assert result.success is True
        assert result.name == "Buy milk"

    async def test_create_with_parent_project(self, service: OperatorService) -> None:
        """Parent ID matching a project resolves successfully."""
        result = await service.add_task(AddTaskCommand(name="Sub task", parent="proj-001"))
        assert result.success is True

    async def test_create_with_parent_task(self, service: OperatorService) -> None:
        """Parent ID matching a task (not project) resolves successfully."""
        result = await service.add_task(AddTaskCommand(name="Sub task", parent="task-001"))
        assert result.success is True

    async def test_no_parent_inbox(self, service: OperatorService) -> None:
        """No parent -> task goes to inbox."""
        result = await service.add_task(AddTaskCommand(name="Inbox task"))
        assert result.success is True

    async def test_parent_not_found(self, service: OperatorService) -> None:
        """Non-existent parent raises ValueError."""
        with pytest.raises(ValueError, match="Parent not found: nonexistent-id"):
            await service.add_task(AddTaskCommand(name="Task", parent="nonexistent-id"))

    @pytest.mark.snapshot(tags=[make_tag_dict(id="tag-work", name="Work")])
    async def test_tags_by_name(self, service: OperatorService) -> None:
        """Case-insensitive tag name resolution."""
        # "work" (lowercase) should match "Work"
        result = await service.add_task(AddTaskCommand(name="Task", tags=["work"]))
        assert result.success is True

    @pytest.mark.snapshot(tags=[make_tag_dict(id="tag-work", name="Work")])
    async def test_tags_by_id_fallback(self, service: OperatorService) -> None:
        """Tag name that doesn't match tries ID fallback."""
        # "tag-work" as name doesn't match, but as ID it does
        result = await service.add_task(AddTaskCommand(name="Task", tags=["tag-work"]))
        assert result.success is True

    async def test_tag_not_found(self, service: OperatorService) -> None:
        """Non-existent tag raises ValueError."""
        with pytest.raises(ValueError, match="Tag not found"):
            await service.add_task(AddTaskCommand(name="Task", tags=["nonexistent"]))

    @pytest.mark.snapshot(
        tags=[make_tag_dict(id="tag-a", name="Work"), make_tag_dict(id="tag-b", name="Work")]
    )
    async def test_tag_ambiguous(self, service: OperatorService) -> None:
        """Multiple tags with same name raises ValueError with IDs and resolution guidance."""
        with pytest.raises(ValueError, match="Ambiguous tag") as exc_info:
            await service.add_task(AddTaskCommand(name="Task", tags=["Work"]))
        # Error should include both IDs and resolution guidance
        assert "tag-a" in str(exc_info.value)
        assert "tag-b" in str(exc_info.value)
        assert "specify by ID" in str(exc_info.value)

    @pytest.mark.snapshot(tags=[make_tag_dict(id="tag-work", name="Work")])
    async def test_all_fields(self, service: OperatorService) -> None:
        """AddTaskCommand with all fields creates task successfully."""
        command = AddTaskCommand(
            name="Full task",
            parent="proj-001",
            tags=["Work"],
            due_date=datetime(2026, 3, 15, 10, 0, tzinfo=UTC),
            defer_date=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
            planned_date=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            flagged=True,
            estimated_minutes=45.0,
            note="Some note",
        )
        result = await service.add_task(command)
        assert result.success is True

    async def test_empty_name(self, service: OperatorService) -> None:
        """Empty string name raises ValidationError at model level."""
        with pytest.raises(ValidationError):
            AddTaskCommand(name="")

    async def test_whitespace_name(self, service: OperatorService) -> None:
        """Whitespace-only name raises ValidationError at model level."""
        with pytest.raises(ValidationError):
            AddTaskCommand(name="   ")

    async def test_validation_before_write(self) -> None:
        """Validation error prevents repository.add_task from being called."""

        mock_repo = AsyncMock()
        mock_repo.get_project.return_value = None
        mock_repo.get_task.return_value = None
        service = OperatorService(repository=mock_repo)

        with pytest.raises(ValueError, match="Parent not found"):
            await service.add_task(AddTaskCommand(name="Task", parent="bad-id"))

        mock_repo.add_task.assert_not_called()

    async def test_create_hierarchy_in_inbox(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Parent task in inbox, then child under that parent (UAT #5)."""
        # Create parent in inbox (no parent field)
        parent_result = await service.add_task(AddTaskCommand(name="Parent task"))
        assert parent_result.success is True

        # Create child under that parent
        child_result = await service.add_task(
            AddTaskCommand(name="Child task", parent=parent_result.id)
        )
        assert child_result.success is True

        # Verify child exists in repo
        child = await repo.get_task(child_result.id)
        assert child is not None
        assert child.name == "Child task"

    @pytest.mark.snapshot(
        tags=[
            make_tag_dict(id="tag-a", name="Urgent"),
            make_tag_dict(id="tag-b", name="Work"),
            make_tag_dict(id="tag-c", name="Home"),
        ]
    )
    async def test_multiple_tags(self, service: OperatorService) -> None:
        """Task with three tags resolves all successfully (UAT #7)."""
        result = await service.add_task(
            AddTaskCommand(name="Multi-tag task", tags=["Urgent", "Work", "Home"])
        )
        assert result.success is True

    async def test_planned_date_only(self, service: OperatorService) -> None:
        """Task with only plannedDate set (no due/defer) succeeds (UAT #11)."""
        result = await service.add_task(
            AddTaskCommand(
                name="Planned-only task",
                planned_date=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            )
        )
        assert result.success is True

    async def test_emoji_and_special_chars(self, service: OperatorService) -> None:
        """Task name with emoji and special characters round-trips (UAT #18)."""
        name = '🎯 Buy <milk> & "eggs"'
        result = await service.add_task(AddTaskCommand(name=name))

        assert result.success is True
        assert result.name == name

    async def test_fractional_estimated_minutes(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Fractional estimatedMinutes preserved through round-trip (UAT #19)."""
        result = await service.add_task(
            AddTaskCommand(name="Fractional estimate", estimated_minutes=150.5)
        )
        assert result.success is True

        task = await repo.get_task(result.id)
        assert task is not None
        assert task.estimated_minutes == 150.5

    async def test_unknown_fields_rejected(self) -> None:
        """Extra fields in model_validate raise ValidationError (STRCT-01)."""

        with pytest.raises(ValidationError, match="bogus_field"):
            AddTaskCommand.model_validate({"name": "Task", "bogus_field": "should be rejected"})


# ---------------------------------------------------------------------------
# OperatorService.add_task: repetition rule (ADD-01 through ADD-14)
# ---------------------------------------------------------------------------


class TestAddTaskRepetitionRule:
    """Service.add_task with repetition rule configurations."""

    async def test_daily_basic(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """ADD-01: Daily frequency with all root fields -> success."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Daily", repetition_rule=spec))
        assert result.success is True

        # Verify bridge received correct payload
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "daily"

    async def test_all_6_frequency_types(self, service: OperatorService) -> None:
        """ADD-02: All 6 frequency types succeed."""
        frequencies = [
            FrequencyAddSpec(type="minutely"),
            FrequencyAddSpec(type="hourly"),
            FrequencyAddSpec(type="daily"),
            FrequencyAddSpec(type="weekly"),
            FrequencyAddSpec(type="weekly", on_days=["MO", "FR"]),
            FrequencyAddSpec(type="monthly"),
            FrequencyAddSpec(type="monthly", on={"second": "tuesday"}),
            FrequencyAddSpec(type="monthly", on_dates=[1, 15]),
            FrequencyAddSpec(type="yearly"),
        ]
        for freq in frequencies:
            spec = RepetitionRuleAddSpec(
                frequency=freq,
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
            )
            result = await service.add_task(
                AddTaskCommand(name=f"Freq {freq.type}", repetition_rule=spec)
            )
            assert result.success is True, f"Failed for type {freq.type}"

    async def test_interval(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """ADD-03: Custom interval preserved."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily", interval=3),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Every 3 days", repetition_rule=spec))
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.interval == 3

    async def test_weekly_on_days_normalize(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """ADD-04: on_days normalized to uppercase."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="weekly", on_days=["mo", "fr"]),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Weekly", repetition_rule=spec))
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        # on_days should be uppercase after normalization
        assert task.repetition_rule.frequency.type == "weekly"
        assert task.repetition_rule.frequency.on_days == ["MO", "FR"]

    async def test_weekly_bare(self, service: OperatorService) -> None:
        """ADD-05: WeeklyFrequency (no on_days) succeeds."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="weekly"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Weekly bare", repetition_rule=spec))
        assert result.success is True

    async def test_monthly_day_of_week(self, service: OperatorService) -> None:
        """ADD-06: Monthly with on (day-of-week pattern) succeeds."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="monthly", on={"second": "tuesday"}),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="2nd Tue", repetition_rule=spec))
        assert result.success is True

    async def test_monthly_day_in_month(self, service: OperatorService) -> None:
        """ADD-07: Monthly with on_dates (day-in-month pattern) succeeds."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="monthly", on_dates=[1, 15]),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="1st&15th", repetition_rule=spec))
        assert result.success is True

    async def test_empty_on_dates_normalizes_to_monthly(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """ADD-08: Empty onDates -> normalized to monthly, warning included."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="monthly", on_dates=[]),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Empty onDates", repetition_rule=spec))
        assert result.success is True
        assert result.warnings is not None
        assert any("monthly" in w.lower() for w in result.warnings)

        # Verify the stored rule is plain monthly
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "monthly"

    async def test_from_completion_schedule(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """ADD-09: from_completion schedule produces correct bridge payload."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.FROM_COMPLETION,
            based_on=BasedOn.DEFER_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="FC", repetition_rule=spec))
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.schedule == Schedule.FROM_COMPLETION

    async def test_defer_date_based_on(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """ADD-10: based_on=defer_date -> anchorDateKey=DeferDate."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DEFER_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Deferred", repetition_rule=spec))
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.based_on == BasedOn.DEFER_DATE

    async def test_end_by_date(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """ADD-11: EndByDate -> ruleString contains UNTIL."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
            end=EndByDateSpec(date=date(2026, 12, 31)),
        )
        result = await service.add_task(AddTaskCommand(name="Until date", repetition_rule=spec))
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.end is not None

    async def test_end_by_occurrences(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """ADD-12: EndByOccurrences -> ruleString contains COUNT."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
            end=EndByOccurrencesSpec(occurrences=10),
        )
        result = await service.add_task(AddTaskCommand(name="10 times", repetition_rule=spec))
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.end is not None

    async def test_no_end_condition(self, service: OperatorService) -> None:
        """ADD-13: No end condition -> ruleString has no UNTIL/COUNT."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Forever", repetition_rule=spec))
        assert result.success is True

    async def test_default_interval(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """ADD-14: Omitted interval defaults to 1."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),  # interval defaults to 1
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="Default", repetition_rule=spec))
        task = await repo.get_task(result.id)
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.interval == 1

    async def test_invalid_interval_rejected(self, service: OperatorService) -> None:
        """Invalid interval (0) -> ValueError from model validator."""
        with pytest.raises(ValueError, match=r"(?i)interval|greater than or equal"):
            FrequencyAddSpec(type="daily", interval=0)

    async def test_from_completion_with_on_days_warns(self, service: OperatorService) -> None:
        """from_completion + onDays -> BYDAY edge case warning in result."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="weekly", on_days=["MO", "FR"]),
            schedule=Schedule.FROM_COMPLETION,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="FC+BYDAY", repetition_rule=spec))
        assert result.success is True
        assert result.warnings is not None
        assert any("from_completion" in w and "onDays" in w for w in result.warnings)

    async def test_from_completion_without_on_days_no_byday_warn(
        self, service: OperatorService
    ) -> None:
        """from_completion + daily (no onDays) -> no BYDAY warning."""
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily", interval=3),
            schedule=Schedule.FROM_COMPLETION,
            based_on=BasedOn.DEFER_DATE,
        )
        result = await service.add_task(AddTaskCommand(name="FC daily", repetition_rule=spec))
        assert result.success is True
        # May have other warnings (e.g. anchor date), but not the BYDAY one
        if result.warnings:
            assert not any("from_completion" in w and "onDays" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# OperatorService.edit_task
# ---------------------------------------------------------------------------


class TestEditTask:
    """Service.edit_task validates inputs and delegates to repository."""

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Old Name", flagged=True)])
    async def test_patch_name_only(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Editing only name leaves other fields unchanged (EDIT-01)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="New Name"))

        assert result.success is True
        assert result.name == "New Name"
        # Verify other fields unchanged
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True  # unchanged

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_patch_note_only(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Editing only note leaves other fields unchanged."""

        result = await service.edit_task(EditTaskCommand(id="task-001", note="New note"))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.note == "New note"

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", flagged=False)])
    async def test_patch_flagged_only(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Editing only flagged leaves other fields unchanged."""

        result = await service.edit_task(EditTaskCommand(id="task-001", flagged=True))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", dueDate="2026-04-01T10:00:00+00:00")]
    )
    async def test_clear_due_date(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Setting due_date=None clears it (EDIT-01)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", due_date=None))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.due_date is None

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_set_due_date(self, service: OperatorService) -> None:
        """Setting due_date to a value updates it (EDIT-02)."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", due_date=datetime(2026, 5, 1, 10, 0, tzinfo=UTC))
        )
        assert result.success is True

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_set_estimated_minutes(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Setting estimated_minutes updates it (EDIT-02)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", estimated_minutes=30.0))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.estimated_minutes == 30.0

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-old", "name": "Old"}])],
        tags=[make_tag_dict(id="tag-new", name="NewTag")],
    )
    async def test_tag_replace(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """actions.tags.replace=["tag1"] replaces all tags (EDIT-03)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=["NewTag"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-new"

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
        tags=[
            make_tag_dict(id="tag-a", name="A"),
            make_tag_dict(id="tag-b", name="B"),
        ],
    )
    async def test_tag_add(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """actions.tags.add=["tag2"] adds without removing (EDIT-04)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["B"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 2
        tag_ids = {t.id for t in task.tags}
        assert "tag-a" in tag_ids
        assert "tag-b" in tag_ids

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                tags=[{"id": "tag-a", "name": "A"}, {"id": "tag-b", "name": "B"}],
            )
        ],
        tags=[
            make_tag_dict(id="tag-a", name="A"),
            make_tag_dict(id="tag-b", name="B"),
        ],
    )
    async def test_tag_remove(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """actions.tags.remove=["tag1"] removes specific tag (EDIT-05)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(remove=["A"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-b"

    async def test_incompatible_tag_edit_modes_replace_with_add(self) -> None:
        """TagAction(replace=..., add=...) raises ValueError (EDIT-06)."""

        with pytest.raises(ValidationError, match="Cannot use 'replace' with 'add' or 'remove'"):
            TagAction(replace=["a"], add=["b"])

    async def test_incompatible_tag_edit_modes_replace_with_remove(self) -> None:
        """TagAction(replace=..., remove=...) raises ValueError."""

        with pytest.raises(ValidationError, match="Cannot use 'replace' with 'add' or 'remove'"):
            TagAction(replace=["a"], remove=["b"])

    async def test_incompatible_tag_edit_modes_empty(self) -> None:
        """TagAction() with no fields raises ValueError."""

        with pytest.raises(ValidationError, match="tags must specify at least one of"):
            TagAction()

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                tags=[{"id": "tag-a", "name": "A"}],
            )
        ],
        tags=[
            make_tag_dict(id="tag-a", name="A"),
            make_tag_dict(id="tag-b", name="B"),
        ],
    )
    async def test_add_and_remove_tags_together(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """actions.tags with add + remove together is allowed (EDIT-06)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["B"], remove=["A"])),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-b"

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", inInbox=True)],
    )
    async def test_move_to_project_ending(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Move task to project via ending (EDIT-07)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is not None
        # OmniFocus sets both parent (root task) and project to the same ID
        # for top-level tasks in a project. The adapter's _adapt_parent_ref
        # sees parent is not None and produces type="task".
        # Golden master scenario_16 confirms this is real OmniFocus behavior.
        assert task.parent.type == "task"
        assert task.parent.id == "proj-001"
        assert task.in_inbox is False

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="task-001", name="Task"),
            make_task_dict(id="task-parent", name="Parent Task"),
        ],
    )
    async def test_move_to_task_beginning(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Move task under another task via beginning (EDIT-07)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(beginning="task-parent")),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "task"
        assert task.parent.id == "task-parent"

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                parent="proj-001",
                project="proj-001",
                inInbox=False,
            )
        ],
    )
    async def test_move_to_inbox(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Move task to inbox via ending=null (EDIT-08)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending=None)),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.parent is None
        assert task.in_inbox is True

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="task-parent", name="Parent"),
            make_task_dict(
                id="task-child",
                name="Child",
                parent="task-parent",
            ),
        ],
    )
    async def test_cycle_detection(self, service: OperatorService) -> None:
        """Moving task under its own child raises ValueError."""

        # task-parent -> task-child (child's parent is task-parent)
        with pytest.raises(ValueError, match="circular reference"):
            await service.edit_task(
                EditTaskCommand(
                    id="task-parent",
                    actions=EditTaskActions(move=MoveAction(beginning="task-child")),
                )
            )

    async def test_task_not_found(self, service: OperatorService) -> None:
        """Non-existent task raises ValueError."""

        with pytest.raises(ValueError, match="Task not found"):
            await service.edit_task(EditTaskCommand(id="nonexistent"))

    async def test_empty_name(self, service: OperatorService) -> None:
        """Empty name raises ValidationError at model level."""
        with pytest.raises(ValidationError):
            EditTaskCommand(id="task-001", name="")

    async def test_whitespace_name(self, service: OperatorService) -> None:
        """Whitespace-only name raises ValidationError at model level."""
        with pytest.raises(ValidationError):
            EditTaskCommand(id="task-001", name="   ")

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[])],
        tags=[make_tag_dict(id="tag-x", name="X")],
    )
    async def test_warning_remove_tag_not_on_task(self, service: OperatorService) -> None:
        """Removing a tag the task doesn't have produces a warning."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(remove=["X"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("is not on this task" in w for w in result.warnings)
        assert any("(tag-x)" in w for w in result.warnings)

    async def test_no_warnings_when_none(self, service: OperatorService) -> None:
        """No warnings when edit is clean."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Updated"))
        assert result.warnings is None

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", note="Some note")])
    async def test_note_null_clears_note(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """note=None maps to empty string (null-means-clear)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", note=None))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.note == ""

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
        tags=[make_tag_dict(id="tag-a", name="A")],
    )
    async def test_tags_null_clears_all_tags(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """actions.tags.replace=None clears all tags (null-means-clear)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=None)),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.tags == []

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Done Task", status="Completed")]
    )
    async def test_warning_edit_completed_task(self, service: OperatorService) -> None:
        """Editing a completed task produces a warm warning."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Renamed"))
        assert result.warnings is not None
        assert any("completed" in w and "confirm with the user" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Dropped Task", status="Dropped")]
    )
    async def test_warning_edit_dropped_task(self, service: OperatorService) -> None:
        """Editing a dropped task produces a warm warning."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Renamed"))
        assert result.warnings is not None
        assert any("dropped" in w and "confirm with the user" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Done Task", status="Completed")]
    )
    async def test_noop_priority_completed(self, service: OperatorService) -> None:
        """No-op edit on completed task returns only no-op warning, not status warning."""

        # Set name to same value -- no-op should suppress status warning
        result = await service.edit_task(EditTaskCommand(id="task-001", name="Done Task"))
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)
        assert not any("completed" in w for w in result.warnings)
        assert len(result.warnings) == 1

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Dropped Task", status="Dropped")]
    )
    async def test_noop_priority_dropped(self, service: OperatorService) -> None:
        """No-op edit on dropped task returns only no-op warning, not status warning."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Dropped Task"))
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)
        assert not any("dropped" in w for w in result.warnings)
        assert len(result.warnings) == 1

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
        tags=[make_tag_dict(id="tag-a", name="A")],
    )
    async def test_warning_addtags_duplicate(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Adding a tag already on the task produces a warning."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["A"])),
            )
        )
        assert result.warnings is not None
        assert any("already on this task" in w for w in result.warnings)
        assert any("(tag-a)" in w for w in result.warnings)
        # Tag is still present (operation still succeeds)
        task = await repo.get_task("task-001")
        assert task is not None
        assert any(t.id == "tag-a" for t in task.tags)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
        tags=[
            make_tag_dict(id="tag-a", name="A"),
            make_tag_dict(id="tag-b", name="B"),
        ],
    )
    async def test_warning_addtags_duplicate_in_add_remove(self, service: OperatorService) -> None:
        """Adding a tag already present in add_remove mode produces a warning."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["A"], remove=["A"])),
            )
        )
        assert result.warnings is not None
        assert any("already on this task" in w for w in result.warnings)
        assert any("(tag-a)" in w for w in result.warnings)
        # Should NOT warn "is not on this task" for A since A IS on the task
        assert not any("is not on this task" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-x", "name": "X"}])],
        tags=[make_tag_dict(id="tag-x", name="X")],
    )
    async def test_add_tag_warning_resolves_name_from_id(self, service: OperatorService) -> None:
        """add tags with raw ID for tag already on task shows resolved name, not ID."""

        # Pass raw ID instead of name
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["tag-x"])),
            )
        )
        assert result.warnings is not None
        # Warning should show resolved name "X", not the raw ID "tag-x"
        assert any("Tag 'X'" in w and "(tag-x)" in w for w in result.warnings)
        assert not any("Tag 'tag-x'" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[])],
        tags=[make_tag_dict(id="tag-x", name="X")],
    )
    async def test_remove_tag_warning_resolves_name_from_id(self, service: OperatorService) -> None:
        """remove tags with raw ID for tag NOT on task shows resolved name, not ID."""

        # Pass raw ID instead of name
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(remove=["tag-x"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        # Warning should show resolved name "X", not the raw ID "tag-x"
        assert any("Tag 'X'" in w and "(tag-x)" in w for w in result.warnings)
        assert not any("Tag 'tag-x'" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "Alpha"}])],
        tags=[make_tag_dict(id="tag-a", name="Alpha")],
    )
    async def test_add_tag_warning_with_name_still_works(self, service: OperatorService) -> None:
        """add tags with name string still shows name correctly (regression guard)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["Alpha"])),
            )
        )
        assert result.warnings is not None
        assert any("Tag 'Alpha'" in w and "(tag-a)" in w for w in result.warnings)

    async def test_warning_empty_edit(self, service: OperatorService) -> None:
        """Empty edit (only id, no fields) returns warning without calling bridge."""

        result = await service.edit_task(EditTaskCommand(id="task-001"))
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes specified" in w for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Foo")])
    async def test_noop_detection_same_name(self, service: OperatorService) -> None:
        """Editing name to same value triggers no-op detection."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Foo"))
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Foo")])
    async def test_noop_detection_different_name(self, service: OperatorService) -> None:
        """Editing name to different value does not trigger no-op warning."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Bar"))
        assert result.warnings is None

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_set_estimate_and_flag_together(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Edit task with both estimated_minutes and flagged (UAT #3)."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", estimated_minutes=45.0, flagged=True)
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.estimated_minutes == 45.0
        assert task.flagged is True

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_set_defer_and_planned_dates(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Edit task setting defer_date and planned_date (UAT #4)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                defer_date=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
                planned_date=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.defer_date is not None
        assert task.defer_date.isoformat() == "2026-03-10T08:00:00+00:00"
        assert task.planned_date is not None
        assert task.planned_date.isoformat() == "2026-03-12T09:00:00+00:00"

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Old")])
    async def test_multi_field_edit(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Edit task changing name, note, flagged, and estimated_minutes (UAT #5)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                name="New Name",
                note="New note",
                flagged=True,
                estimated_minutes=60.0,
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.name == "New Name"
        assert task.note == "New note"
        assert task.flagged is True
        assert task.estimated_minutes == 60.0

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", flagged=True)])
    async def test_unflag(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """Start with flagged=True, edit to flagged=False (UAT #6)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", flagged=False))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is False

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", note="Some note")])
    async def test_clear_note_with_empty_string(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Edit task with note='' clears note (UAT #9)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", note=""))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.note == ""

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", estimatedMinutes=30.0)])
    async def test_clear_estimated_minutes(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Set estimated_minutes=None clears the estimate (UAT #10)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", estimated_minutes=None))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.estimated_minutes is None

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Original",
                note="Keep me",
                flagged=True,
                estimatedMinutes=45.0,
            )
        ]
    )
    async def test_patch_preserves_untouched_fields(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Editing only name preserves note, flagged, estimatedMinutes (UAT #11)."""

        result = await service.edit_task(EditTaskCommand(id="task-001", name="Updated"))
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.name == "Updated"
        assert task.note == "Keep me"
        assert task.flagged is True
        assert task.estimated_minutes == 45.0

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="task-001", name="Task A"),
            make_task_dict(id="task-002", name="Task B"),
        ],
    )
    async def test_move_after_sibling(self, service: OperatorService) -> None:
        """Move task after a sibling task (UAT #28)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(after="task-002")),
            )
        )
        assert result.success is True

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(id="task-001", name="Task A"),
            make_task_dict(id="task-002", name="Task B"),
        ],
    )
    async def test_move_before_sibling(self, service: OperatorService) -> None:
        """Move task before a sibling task (UAT #29)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(before="task-002")),
            )
        )
        assert result.success is True

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_cycle_self_reference(self, service: OperatorService) -> None:
        """Moving task under itself raises circular reference (UAT #38)."""

        with pytest.raises(ValueError, match="circular reference"):
            await service.edit_task(
                EditTaskCommand(
                    id="task-001",
                    actions=EditTaskActions(move=MoveAction(beginning="task-001")),
                )
            )

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_moveto_anchor_not_found(self, service: OperatorService) -> None:
        """MoveAction with nonexistent anchor raises ValueError (UAT #46)."""

        with pytest.raises(ValueError, match="Anchor task not found"):
            await service.edit_task(
                EditTaskCommand(
                    id="task-001",
                    actions=EditTaskActions(move=MoveAction(after="nonexistent-id")),
                )
            )

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Old Name", inInbox=True)],
    )
    async def test_move_and_edit_combined(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Edit task with both move and field changes (UAT #39)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                name="Renamed",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.name == "Renamed"
        assert task.parent is not None
        assert task.parent.id == "proj-001"

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                dueDate="2026-03-10T07:00:00+00:00",
            )
        ]
    )
    async def test_noop_detection_same_date_different_timezone(
        self, service: OperatorService
    ) -> None:
        """Same absolute time in different timezone triggers no-op (UAT #47)."""

        # Same absolute time but expressed as +01:00
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                due_date=datetime.fromisoformat("2026-03-10T08:00:00+01:00"),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes detected" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                parent="proj-001",
                project="proj-001",
            )
        ],
    )
    async def test_same_container_move_warning(self, service: OperatorService) -> None:
        """Moving task to same container (ending) produces location warning (UAT #70)."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already in this container" in w for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_lifecycle_complete_available_task(self, service: OperatorService) -> None:
        """lifecycle='complete' on available task succeeds without special warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        # No lifecycle-specific warnings for fresh complete
        if result.warnings:
            assert not any("already" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_lifecycle_drop_available_task(self, service: OperatorService) -> None:
        """lifecycle='drop' on available task succeeds without special warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        if result.warnings:
            assert not any("already" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", status="Completed")])
    async def test_lifecycle_complete_already_completed_noop(
        self, service: OperatorService
    ) -> None:
        """Completing an already-completed task is a no-op with warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already complete" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", status="Dropped")])
    async def test_lifecycle_drop_already_dropped_noop(self, service: OperatorService) -> None:
        """Dropping an already-dropped task is a no-op with warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already dropped" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", status="Dropped")])
    async def test_lifecycle_complete_dropped_task_cross_state(
        self, service: OperatorService
    ) -> None:
        """Completing a dropped task succeeds with cross-state warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("dropped" in w and "complete" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", status="Completed")])
    async def test_lifecycle_drop_completed_task_cross_state(
        self, service: OperatorService
    ) -> None:
        """Dropping a completed task succeeds with cross-state warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("completed" in w and "drop" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                repetitionRule={
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_lifecycle_complete_repeating_task_warning(
        self, service: OperatorService
    ) -> None:
        """Completing a repeating task warns about occurrence completion."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("repeating" in w.lower() and "occurrence" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                repetitionRule={
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_lifecycle_drop_repeating_task_warning(self, service: OperatorService) -> None:
        """Dropping a repeating task warns about occurrence skipped."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("repeating" in w.lower() and "skipped" in w.lower() for w in result.warnings)
        assert any("OmniFocus UI" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                status="Dropped",
                repetitionRule={
                    "ruleString": "FREQ=WEEKLY",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_lifecycle_cross_state_repeating_stacked_warnings(
        self, service: OperatorService
    ) -> None:
        """Cross-state + repeating: both warnings stack."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        # Both cross-state and repeating warnings should be present
        all_warnings = " ".join(result.warnings).lower()
        assert "dropped" in all_warnings  # cross-state
        assert "repeating" in all_warnings  # repeating

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", flagged=False)])
    async def test_lifecycle_with_field_edits(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """lifecycle + field edits in same call: both applied."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                flagged=True,
                actions=EditTaskActions(lifecycle="complete"),
            )
        )
        assert result.success is True
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.flagged is True

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_lifecycle_only_not_empty_edit(self, service: OperatorService) -> None:
        """lifecycle-only edit is NOT treated as empty edit."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        # Should NOT have "No changes specified" warning
        if result.warnings:
            assert not any("no changes specified" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", status="Completed")])
    async def test_lifecycle_noop_suppresses_status_warning(self, service: OperatorService) -> None:
        """No-op lifecycle should NOT produce the generic status warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        # Should have no-op warning, but NOT the generic status warning or empty edit warning
        assert any("already complete" in w.lower() for w in result.warnings)
        assert not any(
            "confirm with the user that they intended to edit" in w for w in result.warnings
        )
        assert not any("No changes specified" in w for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", status="Completed")])
    async def test_noop_lifecycle_no_spurious_empty_edit_warning(
        self, service: OperatorService
    ) -> None:
        """No-op lifecycle (complete already-completed) should NOT add 'No changes specified'."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already complete" in w.lower() for w in result.warnings)
        assert not any("No changes specified" in w for w in result.warnings)
        assert len(result.warnings) == 1

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                parent="proj-001",
                project="proj-001",
            )
        ],
    )
    async def test_noop_same_container_move_no_spurious_noop_warning(
        self, service: OperatorService
    ) -> None:
        """Same-container move should NOT add 'No changes detected'."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-001")),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already" in w.lower() for w in result.warnings)
        assert not any("No changes detected" in w for w in result.warnings)
        assert len(result.warnings) == 1

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
        tags=[make_tag_dict(id="tag-a", name="A")],
    )
    async def test_noop_tags_no_spurious_empty_edit_warning(self, service: OperatorService) -> None:
        """Replace tags with identical set should NOT add 'No changes specified'."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=["A"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("already match" in w.lower() for w in result.warnings)
        assert not any("No changes specified" in w for w in result.warnings)
        assert len(result.warnings) == 1

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task", status="Completed")])
    async def test_lifecycle_action_suppresses_status_warning(
        self, service: OperatorService
    ) -> None:
        """Cross-state lifecycle should NOT produce the generic status warning."""

        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="drop"))
        )
        assert result.success is True
        # Should have cross-state warning, but NOT the generic status warning
        if result.warnings:
            assert not any(
                "confirm with the user that they intended to edit" in w for w in result.warnings
            )

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_lifecycle_noop_detection_skips_lifecycle_key(
        self, service: OperatorService
    ) -> None:
        """No-op detection (step 7) should skip the lifecycle key in field comparisons."""

        # lifecycle="complete" on an available task should NOT trigger
        # "No changes detected" (the lifecycle IS a change)
        result = await service.edit_task(
            EditTaskCommand(id="task-001", actions=EditTaskActions(lifecycle="complete"))
        )
        assert result.success is True
        if result.warnings:
            assert not any("no changes detected" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="task-001", name="Task")])
    async def test_empty_actions_block(self, service: OperatorService) -> None:
        """EditTaskActions() with all UNSET fields behaves like empty edit."""

        result = await service.edit_task(EditTaskCommand(id="task-001", actions=EditTaskActions()))
        assert result.success is True
        assert result.warnings is not None
        assert any("No changes" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
        tags=[make_tag_dict(id="tag-a", name="A")],
    )
    async def test_tag_replace_noop_same_tags(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """Replace with same tags produces warning, no bridge tag keys."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(replace=["A"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("Tags already match" in w for w in result.warnings)
        # Tags unchanged
        task = await repo.get_task("task-001")
        assert task is not None
        assert len(task.tags) == 1
        assert task.tags[0].id == "tag-a"

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="task-001", name="Task", tags=[{"id": "tag-a", "name": "A"}])],
        tags=[make_tag_dict(id="tag-a", name="A")],
    )
    async def test_tag_only_noop_produces_warning(self, service: OperatorService) -> None:
        """Tag action that produces empty diff triggers no-op warning."""

        # Add a tag that's already there -- diff is empty
        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(tags=TagAction(add=["A"])),
            )
        )
        assert result.success is True
        assert result.warnings is not None
        # Should have per-tag warning only (no generic empty-edit warning)
        assert any("already on this task" in w for w in result.warnings)
        assert not any("No changes" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="task-001",
                name="Task",
                parent="proj-001",
                project="proj-001",
            )
        ],
        projects=[
            make_project_dict(id="proj-001", name="Test Project"),
            make_project_dict(id="proj-002", name="Other Project"),
        ],
    )
    async def test_different_container_move_no_warning(self, service: OperatorService) -> None:
        """Moving task to different container has no location warning."""

        result = await service.edit_task(
            EditTaskCommand(
                id="task-001",
                actions=EditTaskActions(move=MoveAction(ending="proj-002")),
            )
        )
        assert result.success is True
        # No "already in this container" warning
        if result.warnings:
            assert not any("already in this container" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# OperatorService.edit_task: repetition rule (EDIT-01 through EDIT-16)
# ---------------------------------------------------------------------------

# Bridge-format repetition rule fixtures for seeding InMemoryBridge
_DAILY_RULE = {
    "ruleString": "FREQ=DAILY",
    "scheduleType": "Regularly",
    "anchorDateKey": "DueDate",
    "catchUpAutomatically": False,
}

_WEEKLY_ON_DAYS_RULE = {
    "ruleString": "FREQ=WEEKLY;BYDAY=MO,FR",
    "scheduleType": "Regularly",
    "anchorDateKey": "DueDate",
    "catchUpAutomatically": False,
}

_WEEKLY_ON_DAYS_INTERVAL2_RULE = {
    "ruleString": "FREQ=WEEKLY;INTERVAL=2;BYDAY=MO,FR",
    "scheduleType": "Regularly",
    "anchorDateKey": "DueDate",
    "catchUpAutomatically": False,
}


class TestEditTaskRepetitionRule:
    """Service.edit_task repetition rule: EDIT-01 through EDIT-16."""

    @pytest.mark.snapshot(tasks=[make_task_dict(id="t1", name="Plain")])
    async def test_set_rule_on_non_repeating_task(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-01: Set full rule on non-repeating task."""
        spec = RepetitionRuleEditSpec(
            frequency=FrequencyEditSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "daily"
        assert task.repetition_rule.schedule == Schedule.REGULARLY
        assert task.repetition_rule.based_on == BasedOn.DUE_DATE

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_clear_rule(self, service: OperatorService, repo: BridgeOnlyRepository) -> None:
        """EDIT-02: repetition_rule=None -> clears rule."""
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=None))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is None

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_unset_no_change(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-03: repetition_rule=UNSET (omitted) -> no change."""
        result = await service.edit_task(EditTaskCommand(id="t1", name="Renamed"))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "daily"

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_schedule_only_change(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-04: Only schedule set -> preserves frequency/basedOn/end."""
        spec = RepetitionRuleEditSpec(schedule=Schedule.FROM_COMPLETION)
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.schedule == Schedule.FROM_COMPLETION
        assert task.repetition_rule.frequency.type == "daily"
        assert task.repetition_rule.based_on == BasedOn.DUE_DATE

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_based_on_only_change(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-05: Only based_on set -> preserves frequency/schedule/end."""
        spec = RepetitionRuleEditSpec(based_on=BasedOn.DEFER_DATE)
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.based_on == BasedOn.DEFER_DATE
        assert task.repetition_rule.frequency.type == "daily"

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_add_end_condition(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-06: Only end set -> adds end condition."""
        spec = RepetitionRuleEditSpec(end=EndByOccurrencesSpec(occurrences=10))
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.end is not None

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Repeating",
                repetitionRule={
                    "ruleString": "FREQ=DAILY;COUNT=5",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_clear_end_condition(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-07: end=None -> removes end condition."""
        spec = RepetitionRuleEditSpec(end=None)
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.end is None

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Repeating",
                repetitionRule={
                    "ruleString": "FREQ=DAILY;UNTIL=20261231T000000Z",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_change_end_date_to_occurrences(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-08: End changed from date to occurrences."""
        spec = RepetitionRuleEditSpec(end=EndByOccurrencesSpec(occurrences=20))
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.end is not None

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_same_type_change_interval(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-09/10: Same type, change interval -> merges."""
        spec = RepetitionRuleEditSpec(frequency=FrequencyEditSpec(interval=5))
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "daily"
        assert task.repetition_rule.frequency.interval == 5

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Repeating",
                repetitionRule=_WEEKLY_ON_DAYS_INTERVAL2_RULE,
            )
        ]
    )
    async def test_same_type_change_on_days(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-11: Same type, change on_days -> interval preserved."""
        spec = RepetitionRuleEditSpec(frequency=FrequencyEditSpec(on_days=["TU", "TH"]))
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "weekly"
        assert task.repetition_rule.frequency.on_days == ["TU", "TH"]
        # interval should be preserved from existing (2)
        assert task.repetition_rule.frequency.interval == 2

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Repeating",
                repetitionRule={
                    "ruleString": "FREQ=MONTHLY;BYDAY=2TU",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_same_type_change_monthly_on(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-12: Same monthly_day_of_week type, change on -> interval preserved."""
        spec = RepetitionRuleEditSpec(frequency=FrequencyEditSpec(on={"last": "friday"}))
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "monthly"

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Repeating",
                repetitionRule={
                    "ruleString": "FREQ=MONTHLY;BYDAY=2TU",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_auto_clear_on_when_on_dates_set(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """D-08: Send onDates on monthly task with existing on -> auto-clears on.

        The agent sends {frequency: {onDates: [1, 15]}} to switch from a
        weekday pattern (on: {"second": "tuesday"}) to date-based. The existing
        'on' field should auto-clear, and the new onDates should be applied.
        """
        spec = RepetitionRuleEditSpec(frequency=FrequencyEditSpec(on_dates=[1, 15]))
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "monthly"
        # Agent sent on_dates -> on should be auto-cleared
        assert task.repetition_rule.frequency.on is None
        assert task.repetition_rule.frequency.on_dates == [1, 15]
        # Should have auto-clear warning
        assert result.warnings is not None
        assert any("on was automatically cleared" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Repeating",
                repetitionRule={
                    "ruleString": "FREQ=MONTHLY;BYMONTHDAY=1,15",
                    "scheduleType": "Regularly",
                    "anchorDateKey": "DueDate",
                    "catchUpAutomatically": False,
                },
            )
        ]
    )
    async def test_auto_clear_on_dates_when_on_set(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """D-08: Send on on monthly task with existing onDates -> auto-clears onDates.

        The agent sends {frequency: {on: {"last": "friday"}}} to switch from a
        date-based pattern (onDates: [1, 15]) to weekday. The existing
        'onDates' field should auto-clear, and the new on should be applied.
        """
        spec = RepetitionRuleEditSpec(frequency=FrequencyEditSpec(on={"last": "friday"}))
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "monthly"
        # Agent sent on -> on_dates should be auto-cleared
        assert task.repetition_rule.frequency.on == OrdinalWeekday(last="friday")
        assert task.repetition_rule.frequency.on_dates is None
        # Should have auto-clear warning
        assert result.warnings is not None
        assert any("onDates was automatically cleared" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_type_change_full_replacement(
        self, service: OperatorService, repo: BridgeOnlyRepository
    ) -> None:
        """EDIT-13: Different type with full frequency -> replaces entirely."""
        spec = RepetitionRuleEditSpec(
            frequency=FrequencyEditSpec(type="weekly", on_days=["MO", "WE", "FR"])
        )
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True

        task = await repo.get_task("t1")
        assert task is not None
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "weekly"
        assert task.repetition_rule.frequency.on_days == ["MO", "WE", "FR"]

    @pytest.mark.snapshot(tasks=[make_task_dict(id="t1", name="Plain")])
    async def test_partial_update_no_existing_rule_error(self, service: OperatorService) -> None:
        """EDIT-15: Partial update on task with no existing rule -> ValueError."""
        spec = RepetitionRuleEditSpec(schedule=Schedule.FROM_COMPLETION)
        with pytest.raises(ValueError, match="Cannot partially update"):
            await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_noop_same_rule(self, service: OperatorService) -> None:
        """EDIT-16: Same rule sent back -> no-op with warning."""
        spec = RepetitionRuleEditSpec(
            frequency=FrequencyEditSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True
        assert result.warnings is not None
        assert any("no changes" in w.lower() for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[make_task_dict(id="t1", name="Repeating", repetitionRule=_DAILY_RULE)]
    )
    async def test_noop_same_rule_with_other_field_change(self, service: OperatorService) -> None:
        """EDIT-16 gap: Same rule + name change -> no-op warning AND name applied."""
        spec = RepetitionRuleEditSpec(
            frequency=FrequencyEditSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.edit_task(
            EditTaskCommand(id="t1", name="Renamed", repetition_rule=spec)
        )
        assert result.success is True
        assert result.warnings is not None
        assert any("no changes" in w.lower() for w in result.warnings)
        assert result.name == "Renamed"

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Done",
                status="Completed",
                completionDate="2026-01-01T00:00:00.000Z",
                effectiveCompletionDate="2026-01-01T00:00:00.000Z",
            )
        ]
    )
    async def test_set_rule_on_completed_task_warns(self, service: OperatorService) -> None:
        """Setting repetition on completed task -> generic EDIT_COMPLETED_TASK warning."""
        spec = RepetitionRuleEditSpec(
            frequency=FrequencyEditSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True
        assert result.warnings is not None
        assert any("completed" in w for w in result.warnings)

    @pytest.mark.snapshot(
        tasks=[
            make_task_dict(
                id="t1",
                name="Dropped",
                status="Dropped",
                dropDate="2026-01-01T00:00:00.000Z",
                effectiveDropDate="2026-01-01T00:00:00.000Z",
            )
        ]
    )
    async def test_set_rule_on_dropped_task_warns(self, service: OperatorService) -> None:
        """Setting repetition on dropped task -> generic EDIT_COMPLETED_TASK warning."""
        spec = RepetitionRuleEditSpec(
            frequency=FrequencyEditSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True
        assert result.warnings is not None
        assert any("dropped" in w for w in result.warnings)

    @pytest.mark.snapshot(tasks=[make_task_dict(id="t1", name="Plain")])
    async def test_from_completion_with_on_days_warns(self, service: OperatorService) -> None:
        """from_completion + onDays on edit -> BYDAY edge case warning."""
        spec = RepetitionRuleEditSpec(
            frequency=FrequencyEditSpec(type="weekly", on_days=["WE", "FR"]),
            schedule=Schedule.FROM_COMPLETION,
            based_on=BasedOn.DUE_DATE,
        )
        result = await service.edit_task(EditTaskCommand(id="t1", repetition_rule=spec))
        assert result.success is True
        assert result.warnings is not None
        assert any("from_completion" in w and "onDays" in w for w in result.warnings)


# ---------------------------------------------------------------------------
# ConstantMtimeSource
# ---------------------------------------------------------------------------


class TestConstantMtimeSource:
    """ConstantMtimeSource always returns 0 and satisfies MtimeSource."""

    async def test_always_returns_zero(self) -> None:
        source = ConstantMtimeSource()

        first = await source.get_mtime_ns()
        second = await source.get_mtime_ns()

        assert first == 0
        assert second == 0

    async def test_satisfies_mtime_protocol(self) -> None:
        source = ConstantMtimeSource()

        assert isinstance(source, MtimeSource)


# ---------------------------------------------------------------------------
# ErrorOperatorService
# ---------------------------------------------------------------------------


class TestErrorOperatorService:
    """ErrorOperatorService serves startup errors through tool responses."""

    def test_getattr_raises_runtime_error(self) -> None:

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="OmniFocus Operator failed to start"):
            _ = service._repository

    def test_getattr_raises_for_arbitrary_attribute(self) -> None:

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="bad config"):
            _ = service.some_future_method

    def test_error_message_includes_restart_instruction(self) -> None:

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="Restart the server after fixing"):
            _ = service._repository

    def test_getattr_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:

        service = ErrorOperatorService(ValueError("bad config"))

        with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError):
            _ = service._repository

        assert any("error mode" in r.message.lower() for r in caplog.records)

    def test_does_not_call_super_init(self) -> None:

        service = ErrorOperatorService(ValueError("x"))

        assert "_repository" not in service.__dict__


# ---------------------------------------------------------------------------
# Anchor Date Warning (DomainLogic.check_anchor_date_warning)
# ---------------------------------------------------------------------------


class TestAnchorDateWarning:
    """Unit tests for DomainLogic.check_anchor_date_warning."""

    @pytest.fixture
    def domain(self) -> DomainLogic:
        """DomainLogic with mock dependencies (method is pure, doesn't use them)."""
        return DomainLogic(repo=AsyncMock(), resolver=AsyncMock())

    def test_due_date_missing_returns_warning(self, domain: DomainLogic) -> None:
        warnings = domain.check_anchor_date_warning(
            based_on=BasedOn.DUE_DATE,
            effective_dates={"due_date": None, "defer_date": None, "planned_date": None},
        )
        assert len(warnings) == 1
        assert "due_date" in warnings[0]
        assert "dueDate" in warnings[0]

    def test_due_date_present_no_warning(self, domain: DomainLogic) -> None:
        some_dt = datetime(2026, 6, 1, tzinfo=UTC)
        warnings = domain.check_anchor_date_warning(
            based_on=BasedOn.DUE_DATE,
            effective_dates={"due_date": some_dt, "defer_date": None, "planned_date": None},
        )
        assert warnings == []

    def test_defer_date_missing_returns_warning(self, domain: DomainLogic) -> None:
        warnings = domain.check_anchor_date_warning(
            based_on=BasedOn.DEFER_DATE,
            effective_dates={"due_date": None, "defer_date": None, "planned_date": None},
        )
        assert len(warnings) == 1
        assert "defer_date" in warnings[0]
        assert "deferDate" in warnings[0]

    def test_defer_date_present_no_warning(self, domain: DomainLogic) -> None:
        some_dt = datetime(2026, 6, 1, tzinfo=UTC)
        warnings = domain.check_anchor_date_warning(
            based_on=BasedOn.DEFER_DATE,
            effective_dates={"due_date": None, "defer_date": some_dt, "planned_date": None},
        )
        assert warnings == []

    def test_planned_date_missing_returns_warning(self, domain: DomainLogic) -> None:
        warnings = domain.check_anchor_date_warning(
            based_on=BasedOn.PLANNED_DATE,
            effective_dates={"due_date": None, "defer_date": None, "planned_date": None},
        )
        assert len(warnings) == 1
        assert "planned_date" in warnings[0]
        assert "plannedDate" in warnings[0]

    def test_planned_date_present_no_warning(self, domain: DomainLogic) -> None:
        some_dt = datetime(2026, 6, 1, tzinfo=UTC)
        warnings = domain.check_anchor_date_warning(
            based_on=BasedOn.PLANNED_DATE,
            effective_dates={"due_date": None, "defer_date": None, "planned_date": some_dt},
        )
        assert warnings == []

    def test_warning_mentions_completion_date_fallback(self, domain: DomainLogic) -> None:
        warnings = domain.check_anchor_date_warning(
            based_on=BasedOn.DUE_DATE,
            effective_dates={"due_date": None, "defer_date": None, "planned_date": None},
        )
        assert "completion date" in warnings[0]
