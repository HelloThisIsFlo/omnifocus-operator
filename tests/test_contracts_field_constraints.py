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

from omnifocus_operator.contracts.base import UNSET
from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand


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
