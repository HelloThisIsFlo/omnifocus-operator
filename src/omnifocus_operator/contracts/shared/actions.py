"""Shared value objects for the contracts layer: TagAction, MoveAction."""

from __future__ import annotations

from pydantic import Field, model_validator

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
    """Tag operations for task editing.

    Either ``replace`` (standalone) or ``add``/``remove`` (combinable).
    Incompatible modes are rejected.
    """

    add: Patch[list[str]] = Field(
        default=UNSET,
        description="Tag names (case-insensitive) or IDs to add; you can mix both. "
        "Non-existent names are rejected. Ambiguous names return an error.",
    )
    remove: Patch[list[str]] = Field(
        default=UNSET,
        description="Tag names (case-insensitive) or IDs to remove; you can mix both. "
        "Non-existent names are rejected. Ambiguous names return an error.",
    )
    replace: PatchOrNone[list[str]] = Field(
        default=UNSET,
        description="Replace all tags with this list. Tag names (case-insensitive) or IDs; "
        "you can mix both. Non-existent names are rejected. Ambiguous names return an error. "
        "Pass null or [] to clear all tags.",
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
    """Specifies where to move a task.

    Exactly one key must be set. The key doubles as both the position
    and the reference point:

    - ``beginning``/``ending``: ID of the container (project or task),
      or ``null`` for inbox.
    - ``before``/``after``: ID of a sibling task (parent is inferred).
    """

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
