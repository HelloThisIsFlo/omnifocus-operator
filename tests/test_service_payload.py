"""Unit tests for PayloadBuilder -- pure data transformation, no dependencies.

Tests verify that AddTaskRepoPayload and EditTaskRepoPayload are correctly
assembled from command data and domain results. No repos, no stubs, no async.
"""

from __future__ import annotations

from datetime import UTC, date, datetime

from omnifocus_operator.contracts.shared.repetition_rule import (
    RepetitionRuleRepoPayload,
)
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand
from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.models.repetition_rule import (
    Frequency,
)
from omnifocus_operator.service.payload import PayloadBuilder

# ---------------------------------------------------------------------------
# build_add
# ---------------------------------------------------------------------------


class TestBuildAdd:
    """PayloadBuilder.build_add assembles AddTaskRepoPayload."""

    def test_build_add_minimal(self) -> None:
        """Name-only command produces payload with name and flagged=False."""
        builder = PayloadBuilder()
        command = AddTaskCommand(name="Buy milk")
        payload = builder.build_add(command, resolved_tag_ids=None)

        assert payload.name == "Buy milk"
        assert payload.parent is None
        assert payload.tag_ids is None
        assert payload.due_date is None
        assert payload.defer_date is None
        assert payload.planned_date is None
        assert payload.flagged is False
        assert payload.estimated_minutes is None
        assert payload.note is None

    def test_build_add_full(self) -> None:
        """All fields populated produces complete payload."""
        builder = PayloadBuilder()
        command = AddTaskCommand(
            name="Full task",
            parent="proj-1",
            tags=["Work"],  # tags resolved externally
            due_date=datetime(2026, 3, 15, 10, 0, tzinfo=UTC),
            defer_date=datetime(2026, 3, 10, 8, 0, tzinfo=UTC),
            planned_date=datetime(2026, 3, 12, 9, 0, tzinfo=UTC),
            flagged=True,
            estimated_minutes=45.0,
            note="Some note",
        )
        payload = builder.build_add(command, resolved_tag_ids=["tag-work"])

        assert payload.name == "Full task"
        assert payload.parent == "proj-1"
        assert payload.tag_ids == ["tag-work"]
        assert payload.flagged is True
        assert payload.estimated_minutes == 45.0
        assert payload.note == "Some note"

    def test_build_add_with_tags(self) -> None:
        """Resolved tag IDs are set on payload."""
        builder = PayloadBuilder()
        command = AddTaskCommand(name="Tagged", tags=["Work", "Home"])
        payload = builder.build_add(command, resolved_tag_ids=["tag-1", "tag-2"])
        assert payload.tag_ids == ["tag-1", "tag-2"]

    def test_build_add_dates_as_iso(self) -> None:
        """Datetime values serialized to ISO strings."""
        builder = PayloadBuilder()
        due = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
        defer = datetime(2026, 4, 20, 8, 0, tzinfo=UTC)
        planned = datetime(2026, 4, 25, 9, 0, tzinfo=UTC)
        command = AddTaskCommand(
            name="Dated",
            due_date=due,
            defer_date=defer,
            planned_date=planned,
        )
        payload = builder.build_add(command, resolved_tag_ids=None)

        assert payload.due_date == due.isoformat()
        assert payload.defer_date == defer.isoformat()
        assert payload.planned_date == planned.isoformat()


# ---------------------------------------------------------------------------
# build_edit
# ---------------------------------------------------------------------------


class TestBuildEdit:
    """PayloadBuilder.build_edit assembles EditTaskRepoPayload."""

    def test_build_edit_name_only(self) -> None:
        """Command with only name set produces payload with id + name."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1", name="New Name")
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.id == "t1"
        assert payload.name == "New Name"
        assert payload.note is None
        assert payload.flagged is None

    def test_build_edit_note_null_clears(self) -> None:
        """note='' (normalized from None by DomainLogic) passes through."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1", note="")  # was None, normalized upstream
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.note == ""

    def test_build_edit_note_none_passes_through(self) -> None:
        """PayloadBuilder does not interpret null semantics -- passes None through.
        DomainLogic normalizes note=None to '' before PayloadBuilder sees it."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1", note=None)
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        # PayloadBuilder no longer converts None->'' -- that's DomainLogic's job
        assert payload.note is None

    def test_build_edit_dates(self) -> None:
        """Dates serialized to ISO strings, None stays None (clear)."""
        builder = PayloadBuilder()
        due = datetime(2026, 5, 1, 10, 0, tzinfo=UTC)
        command = EditTaskCommand(id="t1", due_date=due, defer_date=None)
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.due_date == due.isoformat()
        assert payload.defer_date is None  # None = clear

    def test_build_edit_lifecycle(self) -> None:
        """Lifecycle action passed through to payload."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1")
        payload = builder.build_edit(
            command, lifecycle="complete", add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.lifecycle == "complete"

    def test_build_edit_tags(self) -> None:
        """Tag add/remove IDs passed through to payload."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1")
        payload = builder.build_edit(
            command,
            lifecycle=None,
            add_tag_ids=["tag-new"],
            remove_tag_ids=["tag-old"],
            move_to=None,
        )

        assert payload.add_tag_ids == ["tag-new"]
        assert payload.remove_tag_ids == ["tag-old"]

    def test_build_edit_move_to(self) -> None:
        """Move dict wrapped in MoveToRepoPayload."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1")
        move_dict = {"position": "ending", "container_id": "proj-1"}
        payload = builder.build_edit(
            command,
            lifecycle=None,
            add_tag_ids=None,
            remove_tag_ids=None,
            move_to=move_dict,
        )

        assert payload.move_to is not None
        assert payload.move_to.position == "ending"
        assert payload.move_to.container_id == "proj-1"

    def test_build_edit_minimal_unset(self) -> None:
        """All _Unset fields produce payload with only id."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1")
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.id == "t1"
        # Only 'id' should be in model_fields_set
        assert payload.model_fields_set == {"id"}

    def test_build_edit_flagged(self) -> None:
        """Flagged field passed through."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1", flagged=True)
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.flagged is True

    def test_build_edit_estimated_minutes(self) -> None:
        """Estimated minutes passed through."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1", estimated_minutes=30.0)
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.estimated_minutes == 30.0

    def test_build_edit_estimated_minutes_null_clears(self) -> None:
        """estimated_minutes=None passes through as None (clear)."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1", estimated_minutes=None)
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.estimated_minutes is None
        assert "estimated_minutes" in payload.model_fields_set

    def test_build_edit_note_with_value(self) -> None:
        """note with a string value passes through."""
        builder = PayloadBuilder()
        command = EditTaskCommand(id="t1", note="Hello")
        payload = builder.build_edit(
            command, lifecycle=None, add_tag_ids=None, remove_tag_ids=None, move_to=None
        )

        assert payload.note == "Hello"


# ---------------------------------------------------------------------------
# build_add: repetition rule
# ---------------------------------------------------------------------------


class TestBuildAddRepetitionRule:
    """PayloadBuilder.build_add repetition rule slotting."""

    def test_no_repetition_rule(self) -> None:
        """No repetition rule -> payload.repetition_rule is None."""
        builder = PayloadBuilder()
        command = AddTaskCommand(name="Plain task")
        payload = builder.build_add(command, resolved_tag_ids=None)
        assert payload.repetition_rule is None

    def test_pre_built_payload_slotted(self) -> None:
        """Pre-built RepetitionRuleRepoPayload is passed through to the repo payload."""
        builder = PayloadBuilder()
        repo_payload = RepetitionRuleRepoPayload(
            frequency=Frequency(type="daily", interval=3),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        command = AddTaskCommand(name="Repeating")
        payload = builder.build_add(
            command, resolved_tag_ids=None, repetition_rule_payload=repo_payload
        )
        assert payload.repetition_rule is repo_payload


# ---------------------------------------------------------------------------
# build_edit: repetition rule
# ---------------------------------------------------------------------------


class TestBuildEditRepetitionRule:
    """PayloadBuilder.build_edit with repetition rule parameters."""

    def _build_edit(
        self,
        command: EditTaskCommand,
        repetition_rule_payload: RepetitionRuleRepoPayload | None = None,
        repetition_rule_clear: bool = False,
    ):
        builder = PayloadBuilder()
        return builder.build_edit(
            command,
            lifecycle=None,
            add_tag_ids=None,
            remove_tag_ids=None,
            move_to=None,
            repetition_rule_payload=repetition_rule_payload,
            repetition_rule_clear=repetition_rule_clear,
        )

    def test_no_repetition_change(self) -> None:
        """No repetition args -> repetition_rule not in fields_set."""
        command = EditTaskCommand(id="t1")
        payload = self._build_edit(command)
        assert "repetition_rule" not in payload.model_fields_set

    def test_set_repetition_rule(self) -> None:
        """Providing a repo payload -> sets repetition_rule on payload."""
        repo_payload = RepetitionRuleRepoPayload(
            frequency=Frequency(type="daily"),
            schedule=Schedule.REGULARLY,
            based_on=BasedOn.DUE_DATE,
        )
        command = EditTaskCommand(id="t1")
        payload = self._build_edit(command, repetition_rule_payload=repo_payload)
        assert payload.repetition_rule is repo_payload
        assert "repetition_rule" in payload.model_fields_set

    def test_clear_repetition_rule(self) -> None:
        """repetition_rule_clear=True -> repetition_rule is None AND in fields_set."""
        command = EditTaskCommand(id="t1")
        payload = self._build_edit(command, repetition_rule_clear=True)
        assert payload.repetition_rule is None
        assert "repetition_rule" in payload.model_fields_set
