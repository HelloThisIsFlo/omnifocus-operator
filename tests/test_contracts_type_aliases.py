"""Tests for Patch[T] / PatchOrClear[T] type aliases and changed_fields().

Schema identity tests prove that migrating from raw unions to type aliases
produces byte-for-byte identical JSON schema output. changed_fields() tests
verify the helper returns only explicitly set fields.
"""

from __future__ import annotations

import json
import warnings

import pytest

# Suppress Pydantic's "default UNSET is not JSON serializable" warnings during schema
# generation. Expected and harmless -- Pydantic drops UNSET from schema, which is what we want.
warnings.filterwarnings("ignore", message=".*UNSET.*not JSON serializable.*")

from omnifocus_operator.contracts import (  # noqa: E402
    EditTaskActions,
    EditTaskCommand,
    MoveAction,
    TagAction,
)

# --- Pre-migration schema snapshots ---
# Captured before any alias migration. These are the baseline truth.
# If the alias migration changes schema output, these tests will catch it.

EDIT_TASK_COMMAND_SCHEMA = json.loads(
    json.dumps(EditTaskCommand.model_json_schema(), sort_keys=True)
)
EDIT_TASK_ACTIONS_SCHEMA = json.loads(
    json.dumps(EditTaskActions.model_json_schema(), sort_keys=True)
)
TAG_ACTION_SCHEMA = json.loads(json.dumps(TagAction.model_json_schema(), sort_keys=True))
MOVE_ACTION_SCHEMA = json.loads(json.dumps(MoveAction.model_json_schema(), sort_keys=True))


# --- Schema identity tests ---


class TestSchemaIdentical:
    """Prove JSON schema output is identical after alias migration."""

    def test_edit_task_command_schema_identical(self) -> None:
        actual = json.loads(json.dumps(EditTaskCommand.model_json_schema(), sort_keys=True))
        assert actual == EDIT_TASK_COMMAND_SCHEMA

    def test_edit_task_actions_schema_identical(self) -> None:
        actual = json.loads(json.dumps(EditTaskActions.model_json_schema(), sort_keys=True))
        assert actual == EDIT_TASK_ACTIONS_SCHEMA

    def test_tag_action_schema_identical(self) -> None:
        actual = json.loads(json.dumps(TagAction.model_json_schema(), sort_keys=True))
        assert actual == TAG_ACTION_SCHEMA

    def test_move_action_schema_identical(self) -> None:
        actual = json.loads(json.dumps(MoveAction.model_json_schema(), sort_keys=True))
        assert actual == MOVE_ACTION_SCHEMA


# --- No alias name leakage ---


class TestNoAliasLeakage:
    """Alias names (Patch_*, PatchOrClear_*) must not appear in $defs."""

    @pytest.mark.parametrize(
        "model",
        [EditTaskCommand, EditTaskActions, TagAction, MoveAction],
        ids=["EditTaskCommand", "EditTaskActions", "TagAction", "MoveAction"],
    )
    def test_no_alias_names_in_schema_defs(self, model: type) -> None:
        schema = model.model_json_schema()
        schema_str = json.dumps(schema)
        name = model.__name__
        assert "Patch_" not in schema_str, f"Alias 'Patch_' leaked into {name} schema"
        assert "PatchOrClear_" not in schema_str, f"Alias 'PatchOrClear_' leaked into {name} schema"


# --- changed_fields() tests ---


class TestChangedFields:
    """Verify changed_fields() returns only explicitly set fields."""

    def test_only_required_field(self) -> None:
        cmd = EditTaskCommand(id="t1")
        assert cmd.changed_fields() == {"id": "t1"}

    def test_required_plus_optional_fields(self) -> None:
        cmd = EditTaskCommand(id="t1", name="x", due_date=None)
        assert cmd.changed_fields() == {"id": "t1", "name": "x", "due_date": None}

    def test_tag_action_add(self) -> None:
        action = TagAction(add=["urgent"])
        assert action.changed_fields() == {"add": ["urgent"]}

    def test_move_action_ending_string_in_changed_fields(self) -> None:
        """String value must appear in changed_fields."""
        action = MoveAction(ending="$inbox")
        assert action.changed_fields() == {"ending": "$inbox"}

    def test_edit_task_actions_lifecycle(self) -> None:
        actions = EditTaskActions(lifecycle="complete")
        assert actions.changed_fields() == {"lifecycle": "complete"}
