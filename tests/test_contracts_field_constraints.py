"""Field constraint tests for write-side command models.

Verifies that AddTaskCommand and EditTaskCommand enforce:
- Non-empty name (min_length=1, whitespace-only rejected)
- AddTaskCommand.flagged defaults to False (not None)
"""

from __future__ import annotations

import pytest
from pydantic import ValidationError

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
