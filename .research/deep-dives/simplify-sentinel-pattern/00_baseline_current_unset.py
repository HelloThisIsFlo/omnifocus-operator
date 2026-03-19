"""Baseline: verify the current _Unset class produces clean schema.

This is the reference point. All alias approaches must match this output.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/00_baseline_current_unset.py
"""

from __future__ import annotations

import json
from typing import Any

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


# ─── Current _Unset implementation (copied from contracts/base.py) ──────────

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
        return core_schema.is_instance_schema(cls)

UNSET = _Unset()


# ─── Test model using plain unions (current style) ─────────────────────────

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

class EditTaskCommand(CommandModel):
    id: str
    name: str | _Unset = UNSET
    flagged: bool | _Unset = UNSET
    note: str | None | _Unset = UNSET
    due_date: str | None | _Unset = UNSET
    estimated_minutes: float | None | _Unset = UNSET


# ─── Check ─────────────────────────────────────────────────────────────────

def main() -> None:
    schema = EditTaskCommand.model_json_schema()
    raw = json.dumps(schema, indent=2)
    print("=== BASELINE: Current _Unset class with plain unions ===\n")
    print(raw)

    problems = []
    if "$defs" in schema:
        problems.append("Has $defs entries")
    if "_Unset" in raw or "_UnsetType" in raw:
        problems.append("Sentinel leaked into schema")
    if '"default"' in raw:
        problems.append("Default leaked into schema")

    # Check property types
    props = schema.get("properties", {})
    if props.get("name", {}).get("type") != "string":
        problems.append(f"name type wrong: {props.get('name')}")
    # note should allow null (anyOf with string + null)
    note_prop = props.get("note", {})
    if "anyOf" not in note_prop:
        problems.append(f"note missing anyOf: {note_prop}")

    print()
    if problems:
        print(f"FAIL: {', '.join(problems)}")
    else:
        print("PASS: Clean schema, no $defs, no default leak, correct property types")

    # Print compact summary for comparison
    print("\n--- Property summary ---")
    for k, v in props.items():
        print(f"  {k}: {json.dumps(v)}")

if __name__ == "__main__":
    main()
