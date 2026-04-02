"""Tests for repository-layer repetition rule serialization.

Tests that serialize_repetition_rule produces correct bridge-format dicts
for various frequency types, schedules, and end conditions.
"""

from __future__ import annotations

from datetime import date

from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoPayload
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    EndByDate,
    EndByOccurrences,
    Frequency,
)
from omnifocus_operator.repository.bridge_write_mixin import BridgeWriteMixin
from omnifocus_operator.repository.rrule.serialize import serialize_repetition_rule

# ---------------------------------------------------------------------------
# serialize_repetition_rule
# ---------------------------------------------------------------------------


class TestSerializeRepetitionRule:
    """serialize_repetition_rule: core types -> bridge-format dict."""

    def test_daily_regularly(self) -> None:
        """Daily frequency with regularly schedule."""
        result = serialize_repetition_rule(
            RepetitionRuleRepoPayload(
                frequency=Frequency(type="daily", interval=3),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
            )
        )
        assert result["ruleString"] == "FREQ=DAILY;INTERVAL=3"
        assert result["scheduleType"] == "Regularly"
        assert result["anchorDateKey"] == "DueDate"
        assert result["catchUpAutomatically"] is False

    def test_from_completion_schedule(self) -> None:
        """From-completion schedule -> scheduleType=FromCompletion, catchUp=False."""
        result = serialize_repetition_rule(
            RepetitionRuleRepoPayload(
                frequency=Frequency(type="daily"),
                schedule=Schedule.FROM_COMPLETION,
                based_on=BasedOn.DEFER_DATE,
            )
        )
        assert result["scheduleType"] == "FromCompletion"
        assert result["catchUpAutomatically"] is False
        assert result["anchorDateKey"] == "DeferDate"

    def test_regularly_with_catch_up(self) -> None:
        """Regularly with catch-up -> scheduleType=Regularly, catchUp=True."""
        result = serialize_repetition_rule(
            RepetitionRuleRepoPayload(
                frequency=Frequency(type="daily"),
                schedule=Schedule.REGULARLY_WITH_CATCH_UP,
                based_on=BasedOn.DUE_DATE,
            )
        )
        assert result["scheduleType"] == "Regularly"
        assert result["catchUpAutomatically"] is True

    def test_with_end_by_occurrences(self) -> None:
        """End by occurrences -> ruleString contains COUNT."""
        result = serialize_repetition_rule(
            RepetitionRuleRepoPayload(
                frequency=Frequency(type="daily"),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
                end=EndByOccurrences(occurrences=10),
            )
        )
        assert "COUNT=10" in result["ruleString"]

    def test_with_end_by_date(self) -> None:
        """End by date -> ruleString contains UNTIL."""
        result = serialize_repetition_rule(
            RepetitionRuleRepoPayload(
                frequency=Frequency(type="daily"),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
                end=EndByDate(date=date(2026, 12, 31)),
            )
        )
        assert "UNTIL=" in result["ruleString"]

    def test_defer_date_based_on(self) -> None:
        """BasedOn.DEFER_DATE -> anchorDateKey=DeferDate."""
        result = serialize_repetition_rule(
            RepetitionRuleRepoPayload(
                frequency=Frequency(type="daily"),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DEFER_DATE,
            )
        )
        assert result["anchorDateKey"] == "DeferDate"


# ---------------------------------------------------------------------------
# BridgeWriteMixin._dump_payload
# ---------------------------------------------------------------------------


class TestDumpPayload:
    """BridgeWriteMixin._dump_payload: intercepts repetition rule for bridge serialization."""

    def _dump(self, payload: EditTaskRepoPayload) -> dict:
        mixin = BridgeWriteMixin()
        return mixin._dump_payload(payload)

    def test_no_repetition_rule(self) -> None:
        """Payload without repetition_rule -> standard model_dump, no interception."""
        payload = EditTaskRepoPayload(id="t1", name="updated")
        result = self._dump(payload)
        assert result["id"] == "t1"
        assert result["name"] == "updated"
        assert "repetitionRule" not in result

    def test_clear_repetition_rule(self) -> None:
        """Payload with repetition_rule=None (clear) -> None passed through, not intercepted."""
        payload = EditTaskRepoPayload(id="t1", repetition_rule=None)
        result = self._dump(payload)
        assert result["repetitionRule"] is None

    def test_set_repetition_rule(self) -> None:
        """Payload with structured repetition_rule -> re-serialized to bridge format."""
        payload = EditTaskRepoPayload(
            id="t1",
            repetition_rule=RepetitionRuleRepoPayload(
                frequency=Frequency(type="daily", interval=2),
                schedule=Schedule.REGULARLY,
                based_on=BasedOn.DUE_DATE,
            ),
        )
        result = self._dump(payload)
        rep = result["repetitionRule"]
        assert rep["ruleString"] == "FREQ=DAILY;INTERVAL=2"
        assert rep["scheduleType"] == "Regularly"
        assert rep["anchorDateKey"] == "DueDate"
        assert rep["catchUpAutomatically"] is False
