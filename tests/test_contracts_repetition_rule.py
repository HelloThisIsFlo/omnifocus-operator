"""Tests for repetition rule contract models.

Tests RepetitionRuleAddSpec, RepetitionRuleEditSpec, RepetitionRuleRepoPayload,
and their integration into AddTaskCommand/EditTaskCommand and repo payload models.
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.contracts.use_cases.add_task import (
    AddTaskCommand,
    AddTaskRepoPayload,
)
from omnifocus_operator.contracts.use_cases.edit_task import (
    EditTaskCommand,
    EditTaskRepoPayload,
)
from omnifocus_operator.contracts.use_cases.repetition_rule import (
    RepetitionRuleAddSpec,
    RepetitionRuleEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    DailyFrequency,
    EndByDate,
    EndByOccurrences,
    HourlyFrequency,
    MinutelyFrequency,
    MonthlyDayInMonthFrequency,
    MonthlyDayOfWeekFrequency,
    MonthlyFrequency,
    WeeklyFrequency,
    WeeklyOnDaysFrequency,
    YearlyFrequency,
)


class TestRepetitionRuleAddSpec:
    """Tests for RepetitionRuleAddSpec (all-required creation spec)."""

    def test_valid_minimal(self) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=DailyFrequency(),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        assert spec.frequency.type == "daily"
        assert spec.schedule == Schedule.REGULARLY
        assert spec.based_on == BasedOn.DUE_DATE
        assert spec.end is None

    def test_missing_frequency_raises(self) -> None:
        with pytest.raises(ValidationError):
            RepetitionRuleAddSpec(
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
            )

    def test_missing_schedule_raises(self) -> None:
        with pytest.raises(ValidationError):
            RepetitionRuleAddSpec(
                frequency=DailyFrequency(),
                based_on=BasedOn.DUE_DATE,
            )

    def test_missing_based_on_raises(self) -> None:
        with pytest.raises(ValidationError):
            RepetitionRuleAddSpec(
                frequency=DailyFrequency(),
                schedule=Schedule.REGULARLY,
            )

    def test_with_end_by_date(self) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=DailyFrequency(),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
            end=EndByDate(date="2026-12-31T00:00:00Z"),
        )
        assert isinstance(spec.end, EndByDate)
        assert spec.end.date == "2026-12-31T00:00:00Z"

    def test_end_none_is_valid(self) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=DailyFrequency(),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
            end=None,
        )
        assert spec.end is None

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            RepetitionRuleAddSpec(
                frequency=DailyFrequency(),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
                extra_field="x",
            )

    @pytest.mark.parametrize(
        "frequency",
        [
            MinutelyFrequency(),
            HourlyFrequency(),
            DailyFrequency(),
            WeeklyFrequency(),
            WeeklyOnDaysFrequency(on_days=["MO", "WE"]),
            MonthlyFrequency(),
            MonthlyDayOfWeekFrequency(on={"second": "tuesday"}),
            MonthlyDayInMonthFrequency(on_dates=[1, 15]),
            YearlyFrequency(),
        ],
        ids=[
            "minutely",
            "hourly",
            "daily",
            "weekly",
            "weekly_on_days",
            "monthly",
            "monthly_day_of_week",
            "monthly_day_in_month",
            "yearly",
        ],
    )
    def test_all_9_frequency_types_valid(self, frequency: object) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=frequency,
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        assert spec.frequency.type == frequency.type


class TestRepetitionRuleEditSpec:
    """Tests for RepetitionRuleEditSpec (patch semantics)."""

    def test_all_unset_is_valid(self) -> None:
        spec = RepetitionRuleEditSpec()
        assert not is_set(spec.frequency)
        assert not is_set(spec.schedule)
        assert not is_set(spec.based_on)
        assert not is_set(spec.end)

    def test_schedule_only(self) -> None:
        spec = RepetitionRuleEditSpec(schedule=Schedule.FROM_COMPLETION)
        assert spec.schedule == Schedule.FROM_COMPLETION
        assert not is_set(spec.frequency)
        assert not is_set(spec.based_on)
        assert not is_set(spec.end)

    def test_frequency_only(self) -> None:
        spec = RepetitionRuleEditSpec(frequency=DailyFrequency(interval=5))
        assert spec.frequency.type == "daily"
        assert spec.frequency.interval == 5
        assert not is_set(spec.schedule)

    def test_end_none_clears(self) -> None:
        """PatchOrClear: None means clear the end condition."""
        spec = RepetitionRuleEditSpec(end=None)
        assert is_set(spec.end)
        assert spec.end is None

    def test_end_set(self) -> None:
        spec = RepetitionRuleEditSpec(end=EndByOccurrences(occurrences=10))
        assert isinstance(spec.end, EndByOccurrences)
        assert spec.end.occurrences == 10


class TestRepetitionRuleRepoPayload:
    """Tests for RepetitionRuleRepoPayload (bridge-ready fields)."""

    def test_all_fields(self) -> None:
        payload = RepetitionRuleRepoPayload(
            rule_string="FREQ=DAILY;INTERVAL=3",
            schedule_type="Regularly",
            anchor_date_key="DueDate",
            catch_up_automatically=False,
        )
        assert payload.rule_string == "FREQ=DAILY;INTERVAL=3"
        assert payload.schedule_type == "Regularly"
        assert payload.anchor_date_key == "DueDate"
        assert payload.catch_up_automatically is False

    def test_camel_case_aliases(self) -> None:
        payload = RepetitionRuleRepoPayload(
            rule_string="FREQ=DAILY",
            schedule_type="Regularly",
            anchor_date_key="DueDate",
            catch_up_automatically=True,
        )
        dumped = payload.model_dump(by_alias=True)
        assert "ruleString" in dumped
        assert "scheduleType" in dumped
        assert "anchorDateKey" in dumped
        assert "catchUpAutomatically" in dumped


class TestCommandIntegration:
    """Tests for repetition rule fields on AddTaskCommand/EditTaskCommand."""

    def test_add_command_with_repetition_rule(self) -> None:
        cmd = AddTaskCommand(
            name="test",
            repetition_rule=RepetitionRuleAddSpec(
                frequency=DailyFrequency(),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
            ),
        )
        assert cmd.repetition_rule is not None
        assert cmd.repetition_rule.frequency.type == "daily"

    def test_add_command_without_repetition_rule(self) -> None:
        cmd = AddTaskCommand(name="test")
        assert cmd.repetition_rule is None

    def test_edit_command_clear_repetition_rule(self) -> None:
        cmd = EditTaskCommand(id="x", repetition_rule=None)
        assert is_set(cmd.repetition_rule)
        assert cmd.repetition_rule is None

    def test_edit_command_unset_repetition_rule(self) -> None:
        cmd = EditTaskCommand(id="x")
        assert not is_set(cmd.repetition_rule)

    def test_edit_command_with_edit_spec(self) -> None:
        cmd = EditTaskCommand(
            id="x",
            repetition_rule=RepetitionRuleEditSpec(
                schedule=Schedule.FROM_COMPLETION,
            ),
        )
        assert is_set(cmd.repetition_rule)
        assert cmd.repetition_rule.schedule == Schedule.FROM_COMPLETION


class TestRepoPayloadIntegration:
    """Tests for repetition rule fields on AddTaskRepoPayload/EditTaskRepoPayload."""

    def test_add_repo_payload_with_repetition_rule(self) -> None:
        payload = AddTaskRepoPayload(
            name="test",
            repetition_rule=RepetitionRuleRepoPayload(
                rule_string="FREQ=DAILY",
                schedule_type="Regularly",
                anchor_date_key="DueDate",
                catch_up_automatically=False,
            ),
        )
        assert payload.repetition_rule is not None

    def test_edit_repo_payload_with_repetition_rule(self) -> None:
        payload = EditTaskRepoPayload(
            id="x",
            repetition_rule=RepetitionRuleRepoPayload(
                rule_string="FREQ=DAILY",
                schedule_type="Regularly",
                anchor_date_key="DueDate",
                catch_up_automatically=False,
            ),
        )
        assert payload.repetition_rule is not None

    def test_edit_repo_payload_clear_repetition_rule(self) -> None:
        payload = EditTaskRepoPayload(id="x", repetition_rule=None)
        assert payload.repetition_rule is None

    def test_edit_repo_payload_dump_with_repetition_rule(self) -> None:
        payload = EditTaskRepoPayload(
            id="x",
            repetition_rule=RepetitionRuleRepoPayload(
                rule_string="FREQ=DAILY",
                schedule_type="Regularly",
                anchor_date_key="DueDate",
                catch_up_automatically=False,
            ),
        )
        dumped = payload.model_dump(by_alias=True, exclude_unset=True)
        assert "repetitionRule" in dumped
        assert dumped["repetitionRule"]["ruleString"] == "FREQ=DAILY"

    def test_edit_repo_payload_dump_without_repetition_rule(self) -> None:
        payload = EditTaskRepoPayload(id="x")
        dumped = payload.model_dump(by_alias=True, exclude_unset=True)
        assert "repetitionRule" not in dumped
