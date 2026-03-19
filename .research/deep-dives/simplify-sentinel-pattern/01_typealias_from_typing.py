"""Approach 1: TypeAlias from typing module.

TypeAlias was added in Python 3.10 for explicitly marking type aliases.
Question: can it work with generics? TypeAlias itself isn't generic-capable,
but we can try both a generic attempt and concrete aliases.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/01_typealias_from_typing.py
"""

from __future__ import annotations

import json
from typing import Any, TypeAlias, TypeVar

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


# ─── Approach 1a: TypeAlias with TypeVar (attempt generic) ─────────────────

T = TypeVar("T")

# This is the question: can TypeAlias be made generic?
# TypeAlias is just a marker, it can't take type parameters.
# But we can try using it with the TypeVar in a union:
try:
    # This likely won't work as a true generic — T is unbound
    PatchGeneric: TypeAlias = T | _Unset  # type: ignore[misc]
    ClearableGeneric: TypeAlias = T | None | _Unset  # type: ignore[misc]
    print("TypeAlias with unbound TypeVar: defined (but likely unusable in Pydantic)")
    GENERIC_WORKS = True
except Exception as e:
    print(f"TypeAlias with TypeVar failed at definition: {e}")
    GENERIC_WORKS = False


# ─── Approach 1b: Concrete TypeAlias for each type used ────────────────────

PatchStr: TypeAlias = str | _Unset
PatchBool: TypeAlias = bool | _Unset
ClearableStr: TypeAlias = str | None | _Unset
ClearableFloat: TypeAlias = float | None | _Unset


# ─── Test models ───────────────────────────────────────────────────────────

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# Model using concrete TypeAlias
class EditTaskConcrete(CommandModel):
    id: str
    name: PatchStr = UNSET
    flagged: PatchBool = UNSET
    note: ClearableStr = UNSET
    due_date: ClearableStr = UNSET
    estimated_minutes: ClearableFloat = UNSET


# Model using generic TypeAlias (if it worked)
if GENERIC_WORKS:
    try:
        class EditTaskGeneric(CommandModel):
            id: str
            name: PatchGeneric[str] = UNSET  # type: ignore[type-arg]
            flagged: PatchGeneric[bool] = UNSET  # type: ignore[type-arg]
            note: ClearableGeneric[str] = UNSET  # type: ignore[type-arg]

        GENERIC_MODEL_WORKS = True
    except Exception as e:
        print(f"Generic model definition failed: {e}")
        GENERIC_MODEL_WORKS = False
else:
    GENERIC_MODEL_WORKS = False


# ─── Check ─────────────────────────────────────────────────────────────────

def check_schema(name: str, model_cls: type) -> None:
    print(f"\n=== {name} ===\n")
    try:
        schema = model_cls.model_json_schema()
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
    except Exception as e:
        print(f"FAIL: Schema generation error: {e}")


def main() -> None:
    print("=" * 60)
    print("  Approach 1: TypeAlias from typing")
    print("=" * 60)

    check_schema("1b: Concrete TypeAlias (PatchStr, ClearableStr, etc.)", EditTaskConcrete)

    if GENERIC_MODEL_WORKS:
        check_schema("1a: Generic TypeAlias (PatchGeneric[str], etc.)", EditTaskGeneric)  # type: ignore[possibly-undefined]
    else:
        print("\n=== 1a: Generic TypeAlias ===")
        print("SKIP: Generic TypeAlias didn't produce a usable model")

    print("\n--- Summary ---")
    print("TypeAlias (concrete): defined & usable. Schema check above.")
    print(f"TypeAlias (generic):  {'usable' if GENERIC_MODEL_WORKS else 'NOT usable with Pydantic'}")


if __name__ == "__main__":
    main()
