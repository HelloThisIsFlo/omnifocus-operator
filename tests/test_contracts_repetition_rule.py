"""Tests for repetition rule contract models.

Tests RepetitionRuleAddSpec, RepetitionRuleEditSpec, RepetitionRuleRepoPayload,
FrequencyAddSpec, FrequencyEditSpec, and their integration into
AddTaskCommand/EditTaskCommand and repo payload models.
"""

from __future__ import annotations

from datetime import date

import pytest
from pydantic import ValidationError

from omnifocus_operator.contracts.base import is_set
from omnifocus_operator.contracts.shared.repetition_rule import (
    FrequencyAddSpec,
    FrequencyEditSpec,
    OrdinalWeekdaySpec,
    RepetitionRuleAddSpec,
    RepetitionRuleEditSpec,
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.contracts.use_cases.add.tasks import (
    AddTaskCommand,
    AddTaskRepoPayload,
)
from omnifocus_operator.contracts.use_cases.edit.tasks import (
    EditTaskCommand,
    EditTaskRepoPayload,
)
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.contracts.shared.repetition_rule import (
    EndByDateSpec,
    EndByOccurrencesSpec,
)


class TestRepetitionRuleAddSpec:
    """Tests for RepetitionRuleAddSpec (all-required creation spec)."""

    def test_valid_minimal(self) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
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
                frequency=FrequencyAddSpec(type="daily"),
                based_on=BasedOn.DUE_DATE,
            )

    def test_missing_based_on_raises(self) -> None:
        with pytest.raises(ValidationError):
            RepetitionRuleAddSpec(
                frequency=FrequencyAddSpec(type="daily"),
                schedule=Schedule.REGULARLY,
            )

    def test_with_end_by_date(self) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
            end=EndByDateSpec(date=date(2026, 12, 31)),
        )
        assert isinstance(spec.end, EndByDateSpec)
        assert spec.end.date == date(2026, 12, 31)

    def test_end_none_is_valid(self) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=FrequencyAddSpec(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
            end=None,
        )
        assert spec.end is None

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            RepetitionRuleAddSpec(
                frequency=FrequencyAddSpec(type="daily"),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
                extra_field="x",
            )

    @pytest.mark.parametrize(
        "frequency",
        [
            FrequencyAddSpec(type="minutely"),
            FrequencyAddSpec(type="hourly"),
            FrequencyAddSpec(type="daily"),
            FrequencyAddSpec(type="weekly"),
            FrequencyAddSpec(type="weekly", on_days=["MO", "WE"]),
            FrequencyAddSpec(type="monthly"),
            FrequencyAddSpec(type="monthly", on={"second": "tuesday"}),
            FrequencyAddSpec(type="monthly", on_dates=[1, 15]),
            FrequencyAddSpec(type="yearly"),
        ],
        ids=[
            "minutely",
            "hourly",
            "daily",
            "weekly",
            "weekly_with_days",
            "monthly",
            "monthly_with_on",
            "monthly_with_on_dates",
            "yearly",
        ],
    )
    def test_all_6_frequency_types_valid(self, frequency: FrequencyAddSpec) -> None:
        spec = RepetitionRuleAddSpec(
            frequency=frequency,
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        assert spec.frequency.type == frequency.type


class TestFrequencyAddSpecValidation:
    """FrequencyAddSpec has the same validators as Frequency."""

    def test_cross_type_on_days_with_daily_raises(self) -> None:
        with pytest.raises(ValidationError, match="on_days is not valid for type 'daily'"):
            FrequencyAddSpec(type="daily", on_days=["MO"])

    def test_cross_type_on_with_weekly_raises(self) -> None:
        with pytest.raises(ValidationError, match="on is not valid for type 'weekly'"):
            FrequencyAddSpec(type="weekly", on={"first": "monday"})

    def test_mutual_exclusion_raises(self) -> None:
        with pytest.raises(ValidationError, match="mutually exclusive"):
            FrequencyAddSpec(type="monthly", on={"first": "monday"}, on_dates=[1])

    def test_extra_field_rejected(self) -> None:
        with pytest.raises(ValidationError, match="extra"):
            FrequencyAddSpec(type="daily", bogus="x")


class TestOrdinalWeekdaySpec:
    """Tests for OrdinalWeekdaySpec (write-side CommandModel)."""

    def test_valid_single_field(self) -> None:
        spec = OrdinalWeekdaySpec(last="friday")
        assert spec.last == "friday"

    def test_extra_field_rejected(self) -> None:
        """CommandModel base rejects unknown fields."""
        with pytest.raises(ValidationError, match="extra"):
            OrdinalWeekdaySpec(unknown_field="x")

    def test_case_normalization(self) -> None:
        spec = OrdinalWeekdaySpec(first="MONDAY")
        assert spec.first == "monday"

    def test_at_most_one_rejects_multiple(self) -> None:
        with pytest.raises(ValidationError, match="on must specify exactly one ordinal"):
            OrdinalWeekdaySpec(first="monday", last="friday")

    def test_coercion_from_dict(self) -> None:
        """FrequencyAddSpec coerces dict to OrdinalWeekdaySpec."""
        spec = FrequencyAddSpec(type="monthly", on={"second": "tuesday"})
        assert isinstance(spec.on, OrdinalWeekdaySpec)
        assert spec.on.second == "tuesday"

    def test_edit_spec_coercion_from_dict(self) -> None:
        """FrequencyEditSpec coerces dict to OrdinalWeekdaySpec."""
        spec = FrequencyEditSpec(on={"second": "tuesday"})
        assert isinstance(spec.on, OrdinalWeekdaySpec)


class TestFrequencyEditSpec:
    """FrequencyEditSpec is a patch container with per-field normalization validators."""

    def test_all_unset_is_valid(self) -> None:
        spec = FrequencyEditSpec()
        assert not is_set(spec.type)
        assert not is_set(spec.interval)
        assert not is_set(spec.on_days)
        assert not is_set(spec.on)
        assert not is_set(spec.on_dates)

    def test_type_only(self) -> None:
        spec = FrequencyEditSpec(type="weekly")
        assert spec.type == "weekly"
        assert not is_set(spec.interval)

    def test_interval_only(self) -> None:
        spec = FrequencyEditSpec(interval=5)
        assert spec.interval == 5
        assert not is_set(spec.type)

    def test_on_days_set(self) -> None:
        spec = FrequencyEditSpec(on_days=["MO", "FR"])
        assert spec.on_days == ["MO", "FR"]

    def test_on_days_clear(self) -> None:
        """PatchOrClear: None means clear on_days."""
        spec = FrequencyEditSpec(on_days=None)
        assert is_set(spec.on_days)
        assert spec.on_days is None

    def test_on_set(self) -> None:
        spec = FrequencyEditSpec(on={"first": "monday"})
        assert isinstance(spec.on, OrdinalWeekdaySpec)
        assert spec.on.first == "monday"

    def test_on_clear(self) -> None:
        spec = FrequencyEditSpec(on=None)
        assert is_set(spec.on)
        assert spec.on is None

    def test_on_dates_set(self) -> None:
        spec = FrequencyEditSpec(on_dates=[1, 15])
        assert spec.on_dates == [1, 15]

    def test_on_dates_clear(self) -> None:
        spec = FrequencyEditSpec(on_dates=None)
        assert is_set(spec.on_dates)
        assert spec.on_dates is None

    def test_no_cross_type_validation(self) -> None:
        """FrequencyEditSpec is a patch container -- can set on_days without type."""
        spec = FrequencyEditSpec(on_days=["MO"])
        assert spec.on_days == ["MO"]
        assert not is_set(spec.type)

    def test_no_mutual_exclusion_validation(self) -> None:
        """FrequencyEditSpec allows both on and on_dates (service layer validates after merge)."""
        spec = FrequencyEditSpec(on={"first": "monday"}, on_dates=[1])
        assert isinstance(spec.on, OrdinalWeekdaySpec)
        assert spec.on.first == "monday"
        assert spec.on_dates == [1]


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
        spec = RepetitionRuleEditSpec(frequency=FrequencyEditSpec(interval=5))
        assert is_set(spec.frequency)
        assert spec.frequency.interval == 5
        assert not is_set(spec.schedule)

    def test_end_none_clears(self) -> None:
        """PatchOrClear: None means clear the end condition."""
        spec = RepetitionRuleEditSpec(end=None)
        assert is_set(spec.end)
        assert spec.end is None

    def test_end_set(self) -> None:
        spec = RepetitionRuleEditSpec(end=EndByOccurrencesSpec(occurrences=10))
        assert isinstance(spec.end, EndByOccurrencesSpec)
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
                frequency=FrequencyAddSpec(type="daily"),
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
