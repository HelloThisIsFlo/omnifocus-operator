"""Approach 4: Simple concrete TypeAlias without generics.

Just define PatchStr, PatchBool, ClearableStr, etc. for each type used.
Ugly but maybe produces clean schema.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/04_concrete_typealias_no_generics.py
"""

from __future__ import annotations

import json
from typing import Any, Literal, TypeAlias

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
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


# ─── Concrete type aliases ─────────────────────────────────────────────────

# Patch: can update, cannot clear (no None)
PatchStr: TypeAlias = str | _Unset
PatchBool: TypeAlias = bool | _Unset
PatchListStr: TypeAlias = list[str] | _Unset

# Clearable: can update, can clear (None = clear)
ClearableStr: TypeAlias = str | None | _Unset
ClearableFloat: TypeAlias = float | None | _Unset
ClearableListStr: TypeAlias = list[str] | None | _Unset


# ─── Test model (mirrors real EditTask fields) ────────────────────────────

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class EditTaskCommand(CommandModel):
    id: str
    name: PatchStr = UNSET
    flagged: PatchBool = UNSET
    note: ClearableStr = UNSET
    due_date: ClearableStr = UNSET
    estimated_minutes: ClearableFloat = UNSET
    tags: PatchListStr = UNSET
    replace_tags: ClearableListStr = UNSET


# ─── Check ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  Approach 4: Concrete TypeAlias (no generics)")
    print("=" * 60)

    schema = EditTaskCommand.model_json_schema()
    raw = json.dumps(schema, indent=2)
    print(f"\n{raw}")

    problems = []
    if "$defs" in schema:
        problems.append(f"Has $defs: {list(schema['$defs'].keys())}")
    if "_Unset" in raw or "_UnsetType" in raw:
        problems.append("Sentinel leaked")
    if '"default"' in raw:
        problems.append("Default leaked")
    if "PatchStr" in raw or "ClearableStr" in raw:
        problems.append("Alias name leaked")

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

    # Semantics
    print("\n--- Semantics ---")
    cmd = EditTaskCommand(id="t1")
    print(f"Defaults: name={cmd.name!r}, note={cmd.note!r}")
    cmd2 = EditTaskCommand(id="t2", name="Hi", note=None, tags=["a"])
    print(f"Set+clear: name={cmd2.name!r}, note={cmd2.note!r}, tags={cmd2.tags!r}")


if __name__ == "__main__":
    main()
