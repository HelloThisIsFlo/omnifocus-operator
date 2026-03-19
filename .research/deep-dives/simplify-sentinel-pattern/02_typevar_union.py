"""Approach 2: TypeVar + Union — the pre-3.12 generic approach.

Use Generic[T] base or typing constructs to create parameterized type aliases.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/02_typevar_union.py
"""

from __future__ import annotations

import json
from typing import Any, Generic, TypeVar, Union

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

T = TypeVar("T")


# ─── Approach 2a: Union with TypeVar ──────────────────────────────────────

# Union[T, _Unset] is valid Python typing but can Pydantic resolve it?
Patch = Union[T, _Unset]
Clearable = Union[T, None, _Unset]


class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ─── Test model ────────────────────────────────────────────────────────────

try:
    class EditTaskCommand(CommandModel):
        id: str
        name: Patch[str] = UNSET
        flagged: Patch[bool] = UNSET
        note: Clearable[str] = UNSET
        due_date: Clearable[str] = UNSET
        estimated_minutes: Clearable[float] = UNSET

    MODEL_WORKS = True
    print("Model definition with Union[T, _Unset] aliases: OK")
except Exception as e:
    MODEL_WORKS = False
    print(f"Model definition FAILED: {e}")


# ─── Check ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  Approach 2: TypeVar + Union")
    print("=" * 60)

    if not MODEL_WORKS:
        print("\nFAIL: Could not define model")
        return

    print()
    try:
        schema = EditTaskCommand.model_json_schema()
        raw = json.dumps(schema, indent=2)
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

        # Also test semantics
        print("\n--- Semantics ---")
        cmd = EditTaskCommand(id="t1")
        print(f"Defaults: name={cmd.name!r}, note={cmd.note!r}")

        cmd2 = EditTaskCommand(id="t2", name="Updated", note=None)
        print(f"Set+clear: name={cmd2.name!r}, note={cmd2.note!r}")

    except Exception as e:
        print(f"FAIL: {e}")

    # Also test: does Patch[str] resolve to the same thing as str | _Unset?
    print("\n--- Type identity ---")
    import typing
    print(f"Patch[str] = {Patch[str]}")
    print(f"Clearable[str] = {Clearable[str]}")
    print(f"typing.get_args(Patch[str]) = {typing.get_args(Patch[str])}")


if __name__ == "__main__":
    main()
