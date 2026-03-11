"""Write models for OmniFocus task creation and editing.

These models define the input (spec) and output (result) contracts
for write operations. They are intentionally simpler than the rich
read models -- write specs contain only user-settable fields.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any, Literal

from pydantic import GetCoreSchemaHandler, model_validator
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import CoreSchema, core_schema

from omnifocus_operator.models.base import OmniFocusBaseModel

if TYPE_CHECKING:
    from pydantic import AwareDatetime


# --- UNSET sentinel ---
# Distinguishes "field omitted" (no change) from "field set to null" (clear).
# Used as default for all optional fields on patch models.


class _Unset:
    """Singleton sentinel for omitted fields in patch models."""

    _instance: _Unset | None = None

    def __new__(cls) -> _Unset:
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance

    def __repr__(self) -> str:
        return "UNSET"

    def __bool__(self) -> bool:
        return False

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        """Tell Pydantic how to validate _Unset.

        Accepts the UNSET singleton during validation but never
        appears in JSON schema (handled by model_json_schema override).
        """
        return core_schema.is_instance_schema(cls)


UNSET = _Unset()


class TaskCreateSpec(OmniFocusBaseModel):
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


class MoveToSpec(OmniFocusBaseModel):
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


class TagActionSpec(OmniFocusBaseModel):
    """Tag operations for task editing.

    Either ``replace`` (standalone) or ``add``/``remove`` (combinable).
    Mutual exclusivity is enforced by the model validator.
    """

    add: list[str] | _Unset = UNSET
    remove: list[str] | _Unset = UNSET
    replace: list[str] | None | _Unset = UNSET

    @model_validator(mode="after")
    def _tag_mutual_exclusivity(self) -> TagActionSpec:
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


class ActionsSpec(OmniFocusBaseModel):
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


class TaskEditSpec(OmniFocusBaseModel):
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


def _clean_unset_from_schema(schema: dict[str, Any]) -> dict[str, Any]:
    """Remove _Unset references from a JSON schema.

    Walks the schema and strips anyOf branches that reference _Unset,
    simplifying to the real types. Also removes _Unset from $defs.
    """
    # Remove _Unset from $defs
    defs = schema.get("$defs", {})
    defs.pop("_Unset", None)

    # Clean properties
    props = schema.get("properties", {})
    for _key, prop in props.items():
        if "anyOf" in prop:
            branches = [b for b in prop["anyOf"] if not (b.get("$ref", "").endswith("/_Unset"))]
            if len(branches) == 1:
                # Single type remaining -- flatten
                prop.clear()
                prop.update(branches[0])
            elif branches:
                prop["anyOf"] = branches

    # Clean nested $defs (MoveToSpec etc.)
    for _def_name, def_schema in defs.items():
        def_props = def_schema.get("properties", {})
        for _key, prop in def_props.items():
            if "anyOf" in prop:
                branches = [b for b in prop["anyOf"] if not (b.get("$ref", "").endswith("/_Unset"))]
                if len(branches) == 1:
                    prop.clear()
                    prop.update(branches[0])
                elif branches:
                    prop["anyOf"] = branches

    # Remove empty $defs
    if not defs:
        schema.pop("$defs", None)

    return schema
