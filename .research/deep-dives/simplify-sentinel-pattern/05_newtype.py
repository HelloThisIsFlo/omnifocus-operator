"""Approach 5: NewType — probably won't work but worth checking.

NewType creates a distinct type for type checking. It's NOT generic,
and it doesn't create a union — it wraps a single type.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/05_newtype.py
"""

from __future__ import annotations

import json
from typing import Any, NewType

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


# ─── NewType attempts ─────────────────────────────────────────────────────

# NewType wraps a single type — can we wrap a union?
try:
    PatchStr = NewType("PatchStr", str | _Unset)
    print(f"NewType('PatchStr', str | _Unset) = {PatchStr}")
    NEWTYPE_DEFINED = True
except Exception as e:
    print(f"NewType definition failed: {e}")
    NEWTYPE_DEFINED = False

try:
    ClearableStr = NewType("ClearableStr", str | None | _Unset)
    print(f"NewType('ClearableStr', str | None | _Unset) = {ClearableStr}")
    CLEARABLE_DEFINED = True
except Exception as e:
    print(f"ClearableStr NewType failed: {e}")
    CLEARABLE_DEFINED = False


# ─── Test model ────────────────────────────────────────────────────────────

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


MODEL_WORKS = False
if NEWTYPE_DEFINED and CLEARABLE_DEFINED:
    try:
        class EditTaskCommand(CommandModel):
            id: str
            name: PatchStr = UNSET  # type: ignore[assignment]
            note: ClearableStr = UNSET  # type: ignore[assignment]

        MODEL_WORKS = True
        print("Model definition: OK")
    except Exception as e:
        print(f"Model definition FAILED: {e}")


# ─── Check ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("\n" + "=" * 60)
    print("  Approach 5: NewType")
    print("=" * 60)

    if not MODEL_WORKS:
        print("\nFAIL: Could not define model with NewType aliases")
        return

    try:
        schema = EditTaskCommand.model_json_schema()  # type: ignore[possibly-undefined]
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
            problems.append("NewType name leaked")

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
            print("PASS: Clean schema")

        # Semantics
        print("\n--- Semantics ---")
        cmd = EditTaskCommand(id="t1")
        print(f"Defaults: name={cmd.name!r}, note={cmd.note!r}")
        cmd2 = EditTaskCommand(id="t2", name="Hi", note=None)
        print(f"Set+clear: name={cmd2.name!r}, note={cmd2.note!r}")

    except Exception as e:
        print(f"FAIL: Schema generation error: {e}")


if __name__ == "__main__":
    main()
