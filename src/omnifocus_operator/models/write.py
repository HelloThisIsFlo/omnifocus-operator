"""Write models for OmniFocus task creation and editing.

These models define the input (spec) and output (result) contracts
for write operations. They are intentionally simpler than the rich
read models -- write specs contain only user-settable fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import ConfigDict, model_validator
from pydantic.json_schema import GenerateJsonSchema

from omnifocus_operator.contracts.base import UNSET, _clean_unset_from_schema, _Unset
from omnifocus_operator.models.base import OmniFocusBaseModel

if TYPE_CHECKING:
    from pydantic import AwareDatetime


class WriteModel(OmniFocusBaseModel):
    """Base for write-side models. Rejects unknown fields at validation time."""

    model_config = ConfigDict(extra="forbid")


class TaskCreateSpec(WriteModel):
    """Input model for task creation.

    Only ``name`` is required. All other fields default to ``None``,
    meaning OmniFocus will use its own defaults (e.g. unflagged, no
    due date, inbox placement).
    """

    name: str
    parent: str | None = None
    tags: list[str] | None = None
    due_date: AwareDatetime | None = None
    defer_date: AwareDatetime | None = None
    planned_date: AwareDatetime | None = None
    flagged: bool | None = None
    estimated_minutes: float | None = None
    note: str | None = None


class TaskCreateResult(OmniFocusBaseModel):
    """Result model returned after creating a task.

    Contains the minimal confirmation data: whether it succeeded,
    the OmniFocus-assigned ID, and the task name.
    """

    success: bool
    id: str
    name: str


# --- Edit models ---


class MoveToSpec(WriteModel):
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
    def _exactly_one_key(self) -> MoveToSpec:
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


class TagActionSpec(WriteModel):
    """Tag operations for task editing.

    Either ``replace`` (standalone) or ``add``/``remove`` (combinable).
    Incompatible modes are rejected by the model validator.
    """

    add: list[str] | _Unset = UNSET
    remove: list[str] | _Unset = UNSET
    replace: list[str] | None | _Unset = UNSET

    @model_validator(mode="after")
    def _validate_incompatible_tag_edit_modes(self) -> TagActionSpec:
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


class ActionsSpec(WriteModel):
    """Stateful operations grouped under the actions block.

    Contains tag operations, movement, and lifecycle (reserved).
    """

    tags: TagActionSpec | _Unset = UNSET
    move: MoveToSpec | _Unset = UNSET
    lifecycle: Literal["complete", "drop"] | _Unset = UNSET

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


class TaskEditSpec(WriteModel):
    """Patch model for task editing.

    Only ``id`` is required. All other fields default to ``UNSET``
    (omitted = no change). Setting a clearable field to ``None``
    clears it. Setting a value updates it.

    Stateful operations (tags, move, lifecycle) live under ``actions``.
    """

    # Required -- which task to edit
    id: str

    # Value-only fields (no None -- these can't be "cleared")
    name: str | _Unset = UNSET
    flagged: bool | _Unset = UNSET

    # Clearable fields (None = clear the value)
    note: str | None | _Unset = UNSET
    due_date: AwareDatetime | None | _Unset = UNSET
    defer_date: AwareDatetime | None | _Unset = UNSET
    planned_date: AwareDatetime | None | _Unset = UNSET
    estimated_minutes: float | None | _Unset = UNSET

    # Stateful operations
    actions: ActionsSpec | _Unset = UNSET

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


class TaskEditResult(OmniFocusBaseModel):
    """Result model returned after editing a task."""

    success: bool
    id: str
    name: str
    warnings: list[str] | None = None


# Resolve forward references now that all classes are defined.
# Previously handled by models/__init__.py, now self-contained so
# write.py remains usable via direct import during migration.
from pydantic import AwareDatetime as _AwareDatetime  # noqa: E402

_write_ns: dict[str, type] = {
    "AwareDatetime": _AwareDatetime,
    "TagActionSpec": TagActionSpec,
    "MoveToSpec": MoveToSpec,
    "ActionsSpec": ActionsSpec,
}
WriteModel.model_rebuild(_types_namespace=_write_ns)
TaskCreateSpec.model_rebuild(_types_namespace=_write_ns)
TaskCreateResult.model_rebuild(_types_namespace=_write_ns)
TagActionSpec.model_rebuild(_types_namespace=_write_ns)
ActionsSpec.model_rebuild(_types_namespace=_write_ns)
TaskEditSpec.model_rebuild(_types_namespace=_write_ns)
TaskEditResult.model_rebuild(_types_namespace=_write_ns)
MoveToSpec.model_rebuild(_types_namespace=_write_ns)
