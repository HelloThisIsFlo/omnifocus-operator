"""Shared value objects for the contracts layer: TagAction, MoveAction.

These are renamed from TagActionSpec and MoveToSpec respectively, with
identical fields and validators.
"""

from __future__ import annotations

from typing import Any, Literal

from pydantic import model_validator
from pydantic.json_schema import GenerateJsonSchema

from omnifocus_operator.contracts.base import (
    UNSET,
    CommandModel,
    _clean_unset_from_schema,
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

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = "{model}",
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: Literal["validation", "serialization"] = "validation",
        *,
        union_format: Literal["any_of", "primitive_type_array"] = "any_of",
    ) -> dict[str, Any]:
        """Override to produce a clean JSON schema without _Unset type."""
        schema = super().model_json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
            union_format=union_format,
        )
        return _clean_unset_from_schema(schema)


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

    @classmethod
    def model_json_schema(
        cls,
        by_alias: bool = True,
        ref_template: str = "{model}",
        schema_generator: type[GenerateJsonSchema] = GenerateJsonSchema,
        mode: Literal["validation", "serialization"] = "validation",
        *,
        union_format: Literal["any_of", "primitive_type_array"] = "any_of",
    ) -> dict[str, Any]:
        """Override to produce a clean JSON schema without _Unset type."""
        schema = super().model_json_schema(
            by_alias=by_alias,
            ref_template=ref_template,
            schema_generator=schema_generator,
            mode=mode,
            union_format=union_format,
        )
        return _clean_unset_from_schema(schema)


__all__ = ["MoveAction", "TagAction"]
