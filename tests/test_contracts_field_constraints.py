"""Field constraint tests for write-side command models.

Verifies that AddTaskCommand and EditTaskCommand enforce:
- Non-empty name (min_length=1, whitespace-only rejected)
- AddTaskCommand.flagged defaults to False (not None)
- MoveAction null rejection for all four fields
- TagAction.replace still accepts None (PatchOrClear)
- Date fields accept str (naive, aware, date-only) and reject invalid strings
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

from omnifocus_operator.contracts.base import UNSET, is_set
from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand, AddTaskRepoPayload
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand, EditTaskRepoPayload
from omnifocus_operator.models.enums import TaskType


class TestNameConstraints:
    """Task name must be non-empty and non-whitespace."""

    def test_add_empty_name_rejected(self) -> None:
        """AddTaskCommand(name='') raises ValidationError."""
        with pytest.raises(ValidationError):
            AddTaskCommand(name="")

    def test_add_whitespace_name_rejected(self) -> None:
        """AddTaskCommand(name='   ') raises ValidationError."""
        with pytest.raises(ValidationError):
            AddTaskCommand(name="   ")

    def test_edit_empty_name_rejected(self) -> None:
        """EditTaskCommand(id='x', name='') raises ValidationError."""
        with pytest.raises(ValidationError):
            EditTaskCommand(id="x", name="")

    def test_edit_whitespace_name_rejected(self) -> None:
        """EditTaskCommand(id='x', name='   ') raises ValidationError."""
        with pytest.raises(ValidationError):
            EditTaskCommand(id="x", name="   ")

    def test_add_single_char_valid(self) -> None:
        """Single character name is valid (boundary)."""
        cmd = AddTaskCommand(name="x")
        assert cmd.name == "x"

    def test_add_normal_name_valid(self) -> None:
        """Normal name works fine."""
        cmd = AddTaskCommand(name="Buy milk")
        assert cmd.name == "Buy milk"

    def test_edit_normal_name_valid(self) -> None:
        """Normal name on edit works fine."""
        cmd = EditTaskCommand(id="x", name="New name")
        assert cmd.name == "New name"


class TestFlaggedDefault:
    """AddTaskCommand.flagged defaults to False, not None."""

    def test_flagged_defaults_to_false(self) -> None:
        """Omitting flagged gives False, not None."""
        cmd = AddTaskCommand(name="Valid")
        assert cmd.flagged is False

    def test_flagged_true_works(self) -> None:
        """Explicit True is accepted."""
        cmd = AddTaskCommand(name="Valid", flagged=True)
        assert cmd.flagged is True

    def test_flagged_false_works(self) -> None:
        """Explicit False is accepted."""
        cmd = AddTaskCommand(name="Valid", flagged=False)
        assert cmd.flagged is False

    def test_flagged_none_rejected(self) -> None:
        """None is not a valid value for flagged (it's bool, not Optional[bool])."""
        with pytest.raises(ValidationError):
            AddTaskCommand(name="Valid", flagged=None)


class TestMoveActionNullRejection:
    """MoveAction rejects null for all four fields with educational errors."""

    def test_beginning_null_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            MoveAction(beginning=None)
        assert "beginning cannot be null" in str(exc_info.value)

    def test_ending_null_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            MoveAction(ending=None)
        assert "ending cannot be null" in str(exc_info.value)

    def test_before_null_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            MoveAction(before=None)
        assert "before cannot be null" in str(exc_info.value)

    def test_after_null_rejected(self) -> None:
        with pytest.raises(ValidationError) as exc_info:
            MoveAction(after=None)
        assert "after cannot be null" in str(exc_info.value)

    def test_beginning_string_accepted(self) -> None:
        action = MoveAction(beginning="$inbox")
        assert action.beginning == "$inbox"

    def test_ending_string_accepted(self) -> None:
        action = MoveAction(ending="someProject")
        assert action.ending == "someProject"


class TestAddTaskCommandParentNullRejection:
    """AddTaskCommand.parent uses Patch[str] with null rejection."""

    def test_parent_null_rejected(self) -> None:
        """AddTaskCommand(name='test', parent=None) raises ValidationError."""
        with pytest.raises(ValidationError) as exc_info:
            AddTaskCommand(name="test", parent=None)
        assert "parent cannot be null" in str(exc_info.value)

    def test_parent_omitted_is_unset(self) -> None:
        """AddTaskCommand(name='test') succeeds — parent is UNSET."""
        cmd = AddTaskCommand(name="test")
        assert cmd.parent is UNSET

    def test_parent_inbox_accepted(self) -> None:
        """AddTaskCommand(name='test', parent='$inbox') succeeds."""
        cmd = AddTaskCommand(name="test", parent="$inbox")
        assert cmd.parent == "$inbox"

    def test_parent_string_accepted(self) -> None:
        """AddTaskCommand(name='test', parent='someProject') succeeds."""
        cmd = AddTaskCommand(name="test", parent="someProject")
        assert cmd.parent == "someProject"


class TestTagActionReplaceStillAcceptsNone:
    """TagAction.replace uses PatchOrClear -- None means 'clear all tags'."""

    def test_replace_none_accepted(self) -> None:
        action = TagAction(replace=None)
        assert action.replace is None

    def test_replace_empty_list_accepted(self) -> None:
        action = TagAction(replace=[])
        assert action.replace == []


class TestDateFieldStrType:
    """Date fields on command models accept str (naive-local principle).

    Naive, aware, and date-only ISO strings are all accepted.
    Invalid strings are rejected with an educational error.
    """

    def test_add_naive_datetime_accepted(self) -> None:
        """Naive datetime string is the preferred input."""
        cmd = AddTaskCommand(name="Test", due_date="2026-07-15T17:00:00")
        assert cmd.due_date == "2026-07-15T17:00:00"

    def test_add_aware_datetime_accepted(self) -> None:
        """Aware datetime string is accepted (converted to local by service)."""
        cmd = AddTaskCommand(name="Test", due_date="2026-07-15T17:00:00Z")
        assert cmd.due_date == "2026-07-15T17:00:00Z"

    def test_add_date_only_accepted(self) -> None:
        """Date-only string is accepted (midnight appended by service)."""
        cmd = AddTaskCommand(name="Test", due_date="2026-07-15")
        assert cmd.due_date == "2026-07-15"

    def test_add_offset_datetime_accepted(self) -> None:
        """Datetime with offset is accepted."""
        cmd = AddTaskCommand(name="Test", due_date="2026-07-15T17:00:00+02:00")
        assert cmd.due_date == "2026-07-15T17:00:00+02:00"

    def test_add_invalid_string_rejected(self) -> None:
        """Non-ISO string is rejected with educational error."""
        with pytest.raises(ValidationError, match="Invalid date format"):
            AddTaskCommand(name="Test", due_date="not-a-date")

    def test_edit_naive_datetime_accepted(self) -> None:
        cmd = EditTaskCommand(id="x", due_date="2026-07-15T17:00:00")
        assert cmd.due_date == "2026-07-15T17:00:00"

    def test_edit_aware_datetime_accepted(self) -> None:
        cmd = EditTaskCommand(id="x", due_date="2026-07-15T17:00:00Z")
        assert cmd.due_date == "2026-07-15T17:00:00Z"

    def test_edit_date_only_accepted(self) -> None:
        cmd = EditTaskCommand(id="x", due_date="2026-07-15")
        assert cmd.due_date == "2026-07-15"

    def test_edit_invalid_string_rejected(self) -> None:
        with pytest.raises(ValidationError, match="Invalid date format"):
            EditTaskCommand(id="x", due_date="garbage")

    def test_add_defer_date_naive_accepted(self) -> None:
        cmd = AddTaskCommand(name="Test", defer_date="2026-07-10T08:00:00")
        assert cmd.defer_date == "2026-07-10T08:00:00"

    def test_add_planned_date_naive_accepted(self) -> None:
        cmd = AddTaskCommand(name="Test", planned_date="2026-07-12T09:00:00")
        assert cmd.planned_date == "2026-07-12T09:00:00"


# ---------------------------------------------------------------------------
# FLAG-08: derived read-only flags rejected on write commands
# ---------------------------------------------------------------------------

_DERIVED_READONLY_FLAGS = (
    "hasNote",
    "hasRepetition",
    "hasAttachments",
    "hasChildren",
    "dependsOnChildren",
    "isSequential",
)


class TestAddTaskCommandRejectsDerivedFlags:
    """FLAG-08: derived read-only flags MUST be rejected on AddTaskCommand.

    Rejection is the generic Pydantic 'extra_forbidden' error -- no custom
    educational messaging. JSON Schema already communicates which fields are
    writable; a bespoke message on these six fields would leak the derivation
    logic into the error surface for negligible agent-UX gain (T-56-15).
    """

    @pytest.mark.parametrize("field_name", _DERIVED_READONLY_FLAGS)
    def test_add_task_command_rejects_derived_flag(self, field_name: str) -> None:
        with pytest.raises(ValidationError) as excinfo:
            AddTaskCommand.model_validate({"name": "hello", field_name: True})
        errors = excinfo.value.errors()
        matching = [
            e
            for e in errors
            if e.get("type") == "extra_forbidden" and field_name in e.get("loc", ())
        ]
        assert matching, f"Expected extra_forbidden error on {field_name!r}; got {errors}"

    def test_add_task_command_error_contains_no_custom_message_for_derived_flags(
        self,
    ) -> None:
        """The rejection message is the generic Pydantic one -- not a custom string."""
        with pytest.raises(ValidationError) as excinfo:
            AddTaskCommand.model_validate({"name": "hello", "hasNote": True})
        error_text = str(excinfo.value)
        # Generic pydantic messaging must be present.
        assert "Extra inputs" in error_text or "extra_forbidden" in error_text
        # Negative assertion: no bespoke educational language planted for FLAG-08.
        forbidden_custom_phrases = ["derived", "read-only", "cannot be written"]
        for phrase in forbidden_custom_phrases:
            assert phrase not in error_text.lower(), (
                f"Unexpected custom educational text {phrase!r} in rejection -- "
                "FLAG-08 locks the behavior to the generic Pydantic schema error."
            )


class TestEditTaskCommandRejectsDerivedFlags:
    """FLAG-08: same rejection guarantee on EditTaskCommand."""

    @pytest.mark.parametrize("field_name", _DERIVED_READONLY_FLAGS)
    def test_edit_task_command_rejects_derived_flag(self, field_name: str) -> None:
        with pytest.raises(ValidationError) as excinfo:
            EditTaskCommand.model_validate({"id": "task-abc123", field_name: True})
        errors = excinfo.value.errors()
        matching = [
            e
            for e in errors
            if e.get("type") == "extra_forbidden" and field_name in e.get("loc", ())
        ]
        assert matching, f"Expected extra_forbidden error on {field_name!r}; got {errors}"


# ---------------------------------------------------------------------------
# Plan 56-06: new writable fields on AddTaskCommand / EditTaskCommand
# ---------------------------------------------------------------------------


class TestAddTaskCommandAcceptsNewTypeFields:
    """PROP-01/PROP-02: AddTaskCommand accepts `completesWithChildren` + `type`.

    Patch semantics: omit = use preference default (service resolves), value =
    use value. `null` rejected for both (booleans have no cleared state;
    `type` = enum). `"singleActions"` rejected NATURALLY via the `TaskType`
    enum -- no custom messaging (PROP-03 lock).
    """

    def test_accepts_completes_with_children_true(self) -> None:
        cmd = AddTaskCommand.model_validate({"name": "x", "completesWithChildren": True})
        assert cmd.completes_with_children is True

    def test_accepts_completes_with_children_false(self) -> None:
        cmd = AddTaskCommand.model_validate({"name": "x", "completesWithChildren": False})
        assert cmd.completes_with_children is False

    def test_rejects_completes_with_children_null(self) -> None:
        with pytest.raises(ValidationError):
            AddTaskCommand.model_validate({"name": "x", "completesWithChildren": None})

    def test_accepts_type_parallel(self) -> None:
        cmd = AddTaskCommand.model_validate({"name": "x", "type": "parallel"})
        assert cmd.type == TaskType.PARALLEL

    def test_accepts_type_sequential(self) -> None:
        cmd = AddTaskCommand.model_validate({"name": "x", "type": "sequential"})
        assert cmd.type == TaskType.SEQUENTIAL

    def test_rejects_type_single_actions_via_enum_no_custom_message(self) -> None:
        """singleActions is rejected by Pydantic's enum validator — no custom
        messaging (PROP-03 lock). Must NOT leak task-vs-project derivation
        logic into the error surface (T-56-20)."""
        with pytest.raises(ValidationError) as excinfo:
            AddTaskCommand.model_validate({"name": "x", "type": "singleActions"})
        errors = excinfo.value.errors()
        types = {e.get("type") for e in errors}
        assert any(t in types for t in ("enum", "literal_error")), (
            f"Expected enum/literal_error; got {types}"
        )
        # Confirm no custom messaging planted (PROP-03 lock).
        error_text = str(excinfo.value).lower()
        forbidden_custom = [
            "project only",
            "use projects instead",
            "only applies to projects",
            "project-only",
        ]
        for phrase in forbidden_custom:
            assert phrase not in error_text, (
                f"Custom message {phrase!r} found — PROP-03 says no custom error."
            )

    def test_rejects_type_null(self) -> None:
        with pytest.raises(ValidationError):
            AddTaskCommand.model_validate({"name": "x", "type": None})

    def test_omitting_both_fields_succeeds(self) -> None:
        cmd = AddTaskCommand.model_validate({"name": "x"})
        assert not is_set(cmd.completes_with_children)
        assert not is_set(cmd.type)
        assert cmd.completes_with_children is UNSET
        assert cmd.type is UNSET


class TestEditTaskCommandAcceptsNewTypeFields:
    """PROP-01/PROP-02 on edit: standard Patch semantics (omit = no change)."""

    def test_accepts_completes_with_children_patch_true(self) -> None:
        cmd = EditTaskCommand.model_validate({"id": "t1", "completesWithChildren": True})
        assert cmd.completes_with_children is True

    def test_accepts_completes_with_children_patch_false(self) -> None:
        cmd = EditTaskCommand.model_validate({"id": "t1", "completesWithChildren": False})
        assert cmd.completes_with_children is False

    def test_rejects_completes_with_children_null(self) -> None:
        with pytest.raises(ValidationError):
            EditTaskCommand.model_validate({"id": "t1", "completesWithChildren": None})

    def test_accepts_type_parallel(self) -> None:
        cmd = EditTaskCommand.model_validate({"id": "t1", "type": "parallel"})
        assert cmd.type == TaskType.PARALLEL

    def test_accepts_type_sequential(self) -> None:
        cmd = EditTaskCommand.model_validate({"id": "t1", "type": "sequential"})
        assert cmd.type == TaskType.SEQUENTIAL

    def test_rejects_type_single_actions(self) -> None:
        with pytest.raises(ValidationError) as excinfo:
            EditTaskCommand.model_validate({"id": "t1", "type": "singleActions"})
        errors = excinfo.value.errors()
        types = {e.get("type") for e in errors}
        assert any(t in types for t in ("enum", "literal_error")), (
            f"Expected enum/literal_error; got {types}"
        )

    def test_rejects_type_null(self) -> None:
        with pytest.raises(ValidationError):
            EditTaskCommand.model_validate({"id": "t1", "type": None})

    def test_omitting_both_fields_succeeds(self) -> None:
        cmd = EditTaskCommand.model_validate({"id": "t1"})
        assert not is_set(cmd.completes_with_children)
        assert not is_set(cmd.type)


class TestAddTaskRepoPayloadRequiresBothNewFields:
    """AddTaskRepoPayload: service MUST resolve both fields before building."""

    def test_accepts_both_fields_set(self) -> None:
        payload = AddTaskRepoPayload(name="x", completes_with_children=True, type="parallel")
        assert payload.completes_with_children is True
        assert payload.type == "parallel"

    def test_rejects_missing_completes_with_children(self) -> None:
        with pytest.raises(ValidationError):
            AddTaskRepoPayload(name="x", type="parallel")  # type: ignore[call-arg]

    def test_rejects_missing_type(self) -> None:
        with pytest.raises(ValidationError):
            AddTaskRepoPayload(name="x", completes_with_children=True)  # type: ignore[call-arg]

    def test_rejects_missing_both_new_fields(self) -> None:
        with pytest.raises(ValidationError):
            AddTaskRepoPayload(name="x")  # type: ignore[call-arg]


class TestEditTaskRepoPayloadNewFieldsOptional:
    """EditTaskRepoPayload: both fields optional (None = no change)."""

    def test_accepts_neither_field(self) -> None:
        payload = EditTaskRepoPayload(id="t1")
        assert payload.completes_with_children is None
        assert payload.type is None

    def test_accepts_completes_with_children_only(self) -> None:
        payload = EditTaskRepoPayload(id="t1", completes_with_children=False)
        assert payload.completes_with_children is False
        assert payload.type is None

    def test_accepts_type_only(self) -> None:
        payload = EditTaskRepoPayload(id="t1", type="sequential")
        assert payload.type == "sequential"
        assert payload.completes_with_children is None
