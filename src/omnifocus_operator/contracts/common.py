"""Shared value objects for the contracts layer: TagAction, MoveAction."""

from __future__ import annotations

from pydantic import model_validator

from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    _Unset,
)


class TagAction(CommandModel):
    """Tag operations for task editing.

    Either ``replace`` (standalone) or ``add``/``remove`` (combinable).
    Incompatible modes are rejected by the model validator.
    """

    add: list[str] | _Unset = UNSET
    remove: list[str] | _Unset = UNSET
    replace: list[str] | None | _Unset = UNSET

    @model_validator(mode="after")
    def _validate_incompatible_tag_edit_modes(self) -> TagAction:
        has_replace = not isinstance(self.replace, _Unset)
        has_add = not isinstance(self.add, _Unset)
        has_remove = not isinstance(self.remove, _Unset)
        if has_replace and (has_add or has_remove):
            msg = (
                "Cannot use 'replace' with 'add' or 'remove' "
                "-- use either replace mode or add/remove mode"
            )
            raise ValueError(msg)
        if not has_replace and not has_add and not has_remove:
            msg = "tags must specify at least one of: add, remove, replace"
            raise ValueError(msg)
        return self


class MoveAction(CommandModel):
    """Specifies where to move a task.

    Exactly one key must be set. The key doubles as both the position
    and the reference point:

    - ``beginning``/``ending``: ID of the container (project or task),
      or ``None`` for inbox.
    - ``before``/``after``: ID of a sibling task (parent is inferred).
    """

    beginning: str | None | _Unset = UNSET
    ending: str | None | _Unset = UNSET
    before: str | _Unset = UNSET
    after: str | _Unset = UNSET

    @model_validator(mode="after")
    def _exactly_one_key(self) -> MoveAction:
        keys_set = sum(
            1
            for v in (self.beginning, self.ending, self.before, self.after)
            if not isinstance(v, _Unset)
        )
        if keys_set != 1:
            msg = "moveTo must have exactly one key (beginning, ending, before, or after)"
            raise ValueError(msg)
        return self


__all__ = ["MoveAction", "TagAction"]
