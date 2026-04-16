"""Shared value objects for the contracts layer: TagAction, MoveAction, NoteAction."""

from __future__ import annotations

from typing import Any

from pydantic import Field, field_validator, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    MOVE_ACTION_DOC,
    MOVE_AFTER,
    MOVE_BEFORE,
    MOVE_BEGINNING,
    MOVE_ENDING,
    NOTE_ACTION_APPEND,
    NOTE_ACTION_DOC,
    NOTE_ACTION_REPLACE,
    TAG_ACTION_ADD,
    TAG_ACTION_DOC,
    TAG_ACTION_REMOVE,
    TAG_ACTION_REPLACE,
)
from omnifocus_operator.agent_messages.errors import (
    MOVE_EXACTLY_ONE_KEY,
    MOVE_NULL_ANCHOR,
    MOVE_NULL_CONTAINER,
    NOTE_APPEND_WITH_REPLACE,
    NOTE_NO_OPERATION,
    TAG_NO_OPERATION,
    TAG_REPLACE_WITH_ADD_REMOVE,
)
from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrClear,
    is_set,
)


class TagAction(CommandModel):
    __doc__ = TAG_ACTION_DOC

    add: Patch[list[str]] = Field(
        default=UNSET,
        description=TAG_ACTION_ADD,
    )
    remove: Patch[list[str]] = Field(
        default=UNSET,
        description=TAG_ACTION_REMOVE,
    )
    replace: PatchOrClear[list[str]] = Field(
        default=UNSET,
        description=TAG_ACTION_REPLACE,
    )

    @model_validator(mode="after")
    def _validate_incompatible_tag_edit_modes(self) -> TagAction:
        has_replace = is_set(self.replace)
        has_add = is_set(self.add)
        has_remove = is_set(self.remove)
        if has_replace and (has_add or has_remove):
            msg = TAG_REPLACE_WITH_ADD_REMOVE
            raise ValueError(msg)
        if not has_replace and not has_add and not has_remove:
            msg = TAG_NO_OPERATION
            raise ValueError(msg)
        return self


class NoteAction(CommandModel):
    __doc__ = NOTE_ACTION_DOC

    append: Patch[str] = Field(default=UNSET, description=NOTE_ACTION_APPEND)
    replace: PatchOrClear[str] = Field(default=UNSET, description=NOTE_ACTION_REPLACE)

    @model_validator(mode="after")
    def _validate_incompatible_note_edit_modes(self) -> NoteAction:
        has_append = is_set(self.append)
        has_replace = is_set(self.replace)
        if has_append and has_replace:
            msg = NOTE_APPEND_WITH_REPLACE
            raise ValueError(msg)
        if not has_append and not has_replace:
            msg = NOTE_NO_OPERATION
            raise ValueError(msg)
        return self


class MoveAction(CommandModel):
    __doc__ = MOVE_ACTION_DOC

    beginning: Patch[str] = Field(default=UNSET, description=MOVE_BEGINNING)
    ending: Patch[str] = Field(default=UNSET, description=MOVE_ENDING)
    before: Patch[str] = Field(default=UNSET, description=MOVE_BEFORE)
    after: Patch[str] = Field(default=UNSET, description=MOVE_AFTER)

    @field_validator("beginning", "ending", mode="before")
    @classmethod
    def _reject_null_container(cls, v: object, info: Any) -> object:
        if v is None:
            msg = MOVE_NULL_CONTAINER.format(field=info.field_name)
            raise ValueError(msg)
        return v

    @field_validator("before", "after", mode="before")
    @classmethod
    def _reject_null_anchor(cls, v: object, info: Any) -> object:
        if v is None:
            msg = MOVE_NULL_ANCHOR.format(field=info.field_name)
            raise ValueError(msg)
        return v

    @model_validator(mode="after")
    def _exactly_one_key(self) -> MoveAction:
        keys_set = sum(
            1 for v in (self.beginning, self.ending, self.before, self.after) if is_set(v)
        )
        if keys_set != 1:
            msg = MOVE_EXACTLY_ONE_KEY
            raise ValueError(msg)
        return self


__all__ = ["MoveAction", "NoteAction", "TagAction"]
