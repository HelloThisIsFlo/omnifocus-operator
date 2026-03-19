"""Approach 6a deeper dive: json_schema_extra receives the FINAL schema dict.

The issue: strip_alias_defs mutated the dict but properties still had $ref.
Let's fix the inlining logic properly.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/06b_json_schema_extra_fix.py
"""

# NOTE: Intentionally NOT using `from __future__ import annotations` to see
# if that changes behavior with type statements.

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


class _Unset:
    _instance = None
    def __new__(cls):
        if cls._instance is None:
            cls._instance = object.__new__(cls)
        return cls._instance
    def __repr__(self): return "UNSET"
    def __bool__(self): return False
    @classmethod
    def __get_pydantic_core_schema__(cls, _source_type, _handler):
        return core_schema.is_instance_schema(cls)

UNSET = _Unset()

type Patch[T] = T | _Unset
type Clearable[T] = T | None | _Unset


def strip_alias_defs(schema: dict[str, Any]) -> dict[str, Any]:
    """Inline Patch_/Clearable_ $defs into properties, return cleaned schema."""
    defs = schema.get("$defs", {})
    if not defs:
        return schema

    alias_keys = {k for k in defs if k.startswith(("Patch_", "Clearable_"))}
    if not alias_keys:
        return schema

    # Build ref -> definition map
    ref_map = {f"#/$defs/{k}": defs[k] for k in alias_keys}

    # Replace $ref in properties
    for prop_name, prop_def in schema.get("properties", {}).items():
        ref = prop_def.get("$ref")
        if ref and ref in ref_map:
            # Completely replace the property with the inlined definition
            schema["properties"][prop_name] = ref_map[ref]

    # Remove alias defs
    for k in alias_keys:
        del defs[k]
    if not defs:
        del schema["$defs"]

    return schema


class EditTask(BaseModel):
    model_config = ConfigDict(
        extra="forbid",
        json_schema_extra=strip_alias_defs,
    )
    id: str
    name: Patch[str] = UNSET
    flagged: Patch[bool] = UNSET
    note: Clearable[str] = UNSET
    estimated_minutes: Clearable[float] = UNSET


def main():
    print("=== 6a fixed: json_schema_extra with proper inlining ===\n")
    schema = EditTask.model_json_schema()
    raw = json.dumps(schema, indent=2)
    print(raw)

    problems = []
    if "$defs" in schema:
        problems.append(f"Has $defs: {list(schema['$defs'].keys())}")
    if "_Unset" in raw:
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
        print("PASS: Clean schema after json_schema_extra fix")

    print("\n--- Property summary ---")
    for k, v in props.items():
        print(f"  {k}: {json.dumps(v)}")


if __name__ == "__main__":
    main()
