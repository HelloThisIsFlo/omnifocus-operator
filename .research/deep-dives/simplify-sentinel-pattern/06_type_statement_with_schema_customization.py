"""Approach 6: Python 3.12 `type` statement with schema customization.

We know `type Patch[T] = T | _Unset` creates $defs noise.
Can we suppress that with:
- json_schema_extra on model_config
- Custom __get_pydantic_json_schema__
- GenerateJsonSchema subclass
- model_json_schema(mode=..., schema_generator=...)

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/06_type_statement_with_schema_customization.py
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic.json_schema import GenerateJsonSchema
from pydantic_core import CoreSchema, core_schema


# ─── Sentinel ──────────────────────────────────────────────────────────────

class _Unset:
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
        cls, _source_type: Any, _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.is_instance_schema(cls)

UNSET = _Unset()


# ─── Python 3.12 type aliases ─────────────────────────────────────────────

type Patch[T] = T | _Unset
type Clearable[T] = T | None | _Unset


# ─── First, confirm the problem ───────────────────────────────────────────

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class EditTaskBasic(CommandModel):
    id: str
    name: Patch[str] = UNSET
    flagged: Patch[bool] = UNSET
    note: Clearable[str] = UNSET
    estimated_minutes: Clearable[float] = UNSET


# ─── Approach 6a: json_schema_extra to strip $defs ────────────────────────

def strip_alias_defs(schema: dict[str, Any]) -> None:
    """Remove $defs entries that are just alias indirections."""
    defs = schema.get("$defs", {})
    if not defs:
        return

    # Find alias refs that are just transparent wrappers
    alias_keys = [k for k in defs if k.startswith(("Patch_", "Clearable_"))]
    if not alias_keys:
        return

    # For each alias, inline its definition into properties that reference it
    for key in alias_keys:
        ref_str = f"#/$defs/{key}"
        alias_def = defs[key]

        # Walk properties and replace $ref with the inlined definition
        for prop_name, prop_def in schema.get("properties", {}).items():
            if prop_def.get("$ref") == ref_str:
                schema["properties"][prop_name] = alias_def
            # Also check inside anyOf
            if "anyOf" in prop_def:
                new_any_of = []
                for item in prop_def["anyOf"]:
                    if item.get("$ref") == ref_str:
                        # Inline the alias definition
                        if "anyOf" in alias_def:
                            new_any_of.extend(alias_def["anyOf"])
                        else:
                            new_any_of.append(alias_def)
                    else:
                        new_any_of.append(item)
                schema["properties"][prop_name]["anyOf"] = new_any_of

        del defs[key]

    if not defs:
        del schema["$defs"]


class EditTaskJsonExtra(CommandModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=strip_alias_defs,
    )
    id: str
    name: Patch[str] = UNSET
    flagged: Patch[bool] = UNSET
    note: Clearable[str] = UNSET
    estimated_minutes: Clearable[float] = UNSET


# ─── Approach 6b: Custom GenerateJsonSchema ───────────────────────────────

class CleanAliasJsonSchema(GenerateJsonSchema):
    """Schema generator that inlines Patch/Clearable alias references."""

    def generate(self, schema: CoreSchema, mode: str = "validation") -> dict[str, Any]:
        result = super().generate(schema, mode)
        strip_alias_defs(result)
        return result


# ─── Check ─────────────────────────────────────────────────────────────────

def check_schema(name: str, schema: dict[str, Any]) -> None:
    raw = json.dumps(schema, indent=2)
    print(f"\n=== {name} ===\n")
    print(raw)

    problems = []
    if "$defs" in schema:
        problems.append(f"Has $defs: {list(schema['$defs'].keys())}")
    if "_Unset" in raw or "_UnsetType" in raw:
        problems.append("Sentinel leaked")
    if '"default"' in raw:
        problems.append("Default leaked")

    props = schema.get("properties", {})
    if props.get("name", {}).get("type") != "string":
        problems.append(f"name type wrong: {props.get('name')}")
    note_prop = props.get("note", {})
    if "anyOf" not in note_prop:
        problems.append(f"note missing anyOf: {note_prop}")

    print()
    if problems:
        print(f"FAIL: {'; '.join(problems)}")
    else:
        print("PASS: Clean schema, no $defs, no default leak")

    print("\n--- Property summary ---")
    for k, v in props.items():
        print(f"  {k}: {json.dumps(v)}")


def main() -> None:
    print("=" * 60)
    print("  Approach 6: type statement + schema customization")
    print("=" * 60)

    # First, show the problem
    check_schema("6-baseline: type statement (no fix)", EditTaskBasic.model_json_schema())

    # 6a: json_schema_extra
    check_schema("6a: json_schema_extra strips alias $defs", EditTaskJsonExtra.model_json_schema())

    # 6b: Custom schema generator
    check_schema(
        "6b: Custom GenerateJsonSchema",
        EditTaskBasic.model_json_schema(schema_generator=CleanAliasJsonSchema),
    )

    # Semantics still work?
    print("\n--- Semantics ---")
    cmd = EditTaskBasic(id="t1")
    print(f"Defaults: name={cmd.name!r}, note={cmd.note!r}")
    cmd2 = EditTaskBasic(id="t2", name="Hi", note=None)
    print(f"Set+clear: name={cmd2.name!r}, note={cmd2.note!r}")


if __name__ == "__main__":
    main()
