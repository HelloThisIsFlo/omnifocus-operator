"""Base contract infrastructure: CommandModel, UNSET sentinel, schema utilities.

CommandModel is the base class for all command-layer models (agent instructions,
repo payloads). It inherits OmniFocusBaseModel's camelCase aliasing and adds
extra="forbid" to reject unknown fields at validation time.
"""

from __future__ import annotations

from typing import Any

from pydantic import ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from omnifocus_operator.models.base import OmniFocusBaseModel

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


class CommandModel(OmniFocusBaseModel):
    """Base for all command-layer models. Rejects unknown fields at validation time."""

    model_config = ConfigDict(extra="forbid")


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

    # Clean nested $defs (MoveAction etc.)
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


__all__ = ["UNSET", "CommandModel", "_Unset", "_clean_unset_from_schema"]
