"""Shared value objects for the contracts layer: TagAction, MoveAction."""

from __future__ import annotations

from pydantic import Field, model_validator

from omnifocus_operator.agent_messages.descriptions import (
    MOVE_ACTION_DOC,
    TAG_ACTION_ADD,
    TAG_ACTION_DOC,
    TAG_ACTION_REMOVE,
    TAG_ACTION_REPLACE,
)
from omnifocus_operator.agent_messages.errors import (
    MOVE_EXACTLY_ONE_KEY,
    TAG_NO_OPERATION,
    TAG_REPLACE_WITH_ADD_REMOVE,
)
from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    Patch,
    PatchOrNone,
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
    replace: PatchOrNone[list[str]] = Field(
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


class MoveAction(CommandModel):
    __doc__ = MOVE_ACTION_DOC

    beginning: PatchOrNone[str] = UNSET
    ending: PatchOrNone[str] = UNSET
    before: Patch[str] = UNSET
    after: Patch[str] = UNSET

    @model_validator(mode="after")
    def _exactly_one_key(self) -> MoveAction:
        keys_set = sum(
            1 for v in (self.beginning, self.ending, self.before, self.after) if is_set(v)
        )
        if keys_set != 1:
            msg = MOVE_EXACTLY_ONE_KEY
            raise ValueError(msg)
        return self


__all__ = ["MoveAction", "TagAction"]
