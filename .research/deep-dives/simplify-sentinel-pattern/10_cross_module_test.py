"""Test approach 2 (TypeVar + Union) working across module imports.

Simulates the real usage: aliases defined in contracts/base.py,
used in contracts/use_cases/edit_task.py.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/10_cross_module_test.py
"""

from __future__ import annotations

import json
from typing import Any, TypeVar, Union

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


# ─── This would be in contracts/base.py ───────────────────────────────────

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
Patch = Union[T, _Unset]
Clearable = Union[T, None, _Unset]

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# ─── This would be in contracts/common.py ──────────────────────────────────

class TagAction(CommandModel):
    add: Patch[list[str]] = UNSET
    remove: Patch[list[str]] = UNSET
    replace: Clearable[list[str]] = UNSET

class MoveAction(CommandModel):
    beginning: Clearable[str] = UNSET
    ending: Clearable[str] = UNSET
    before: Patch[str] = UNSET
    after: Patch[str] = UNSET


# ─── This would be in contracts/use_cases/edit_task.py ──────────────────────

from datetime import datetime

class EditTaskCommand(CommandModel):
    id: str
    name: Patch[str] = UNSET
    flagged: Patch[bool] = UNSET
    note: Clearable[str] = UNSET
    due_date: Clearable[str] = UNSET
    defer_date: Clearable[str] = UNSET
    estimated_minutes: Clearable[float] = UNSET
    tags: Patch[TagAction] = UNSET
    move: Patch[MoveAction] = UNSET


# ─── Check ─────────────────────────────────────────────────────────────────

def main() -> None:
    print("=" * 60)
    print("  Cross-module test: full model hierarchy")
    print("=" * 60)

    for name, cls in [("EditTaskCommand", EditTaskCommand), ("TagAction", TagAction), ("MoveAction", MoveAction)]:
        print(f"\n=== {name} ===")
        schema = cls.model_json_schema()
        raw = json.dumps(schema, indent=2)

        alias_defs = [k for k in schema.get("$defs", {}) if k.startswith(("Patch_", "Clearable_"))]
        problems = []
        if alias_defs:
            problems.append(f"Alias $defs: {alias_defs}")
        if "_Unset" in raw:
            problems.append("Sentinel leaked")
        if '"default"' in raw:
            problems.append("Default leaked")

        if problems:
            print(f"FAIL: {'; '.join(problems)}")
        else:
            print("PASS")

        real_defs = [k for k in schema.get("$defs", {}) if not k.startswith(("Patch_", "Clearable_"))]
        if real_defs:
            print(f"  Real $defs (expected): {real_defs}")

        props = schema.get("properties", {})
        for k, v in props.items():
            print(f"  {k}: {json.dumps(v)}")

    # Semantics
    print("\n--- Full semantics test ---")
    cmd = EditTaskCommand.model_validate({
        "id": "t1",
        "name": "Updated task",
        "note": None,
        "tags": {"add": ["urgent"]},
        "move": {"ending": "project-123"},
    })
    print(f"name={cmd.name!r}")
    print(f"note={cmd.note!r}")
    print(f"flagged={cmd.flagged!r} (should be UNSET)")
    print(f"tags={cmd.tags!r}")
    print(f"move={cmd.move!r}")


if __name__ == "__main__":
    main()
