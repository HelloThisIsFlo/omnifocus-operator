"""Approach 3: Annotated with metadata marker.

Use typing.Annotated to attach metadata. The idea: Annotated[T | _Unset, PatchField()]
The metadata is invisible to Pydantic schema unless we make it a validator/schema modifier.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/03_annotated_metadata.py
"""

from __future__ import annotations

import json
from typing import Annotated, Any, TypeVar, Union

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


# ─── Metadata markers ─────────────────────────────────────────────────────

class PatchField:
    """Marker: field supports update but not clear."""
    pass

class ClearableField:
    """Marker: field supports update AND clear (None = clear)."""
    pass


# ─── Approach 3a: Annotated with concrete types ───────────────────────────
# Annotated[str | _Unset, PatchField()] — explicit per type

PatchStr = Annotated[str | _Unset, PatchField()]
PatchBool = Annotated[bool | _Unset, PatchField()]
ClearableStr = Annotated[str | None | _Unset, ClearableField()]
ClearableFloat = Annotated[float | None | _Unset, ClearableField()]


# ─── Approach 3b: Annotated with generic helper function ──────────────────
# def Patch(t): return Annotated[Union[t, _Unset], PatchField()]
# This can't be a true generic type alias, but maybe a function works?

def Patch(t: type) -> Any:
    """Create Annotated[t | _Unset, PatchField()] dynamically."""
    return Annotated[Union[t, _Unset], PatchField()]

def Clearable(t: type) -> Any:
    """Create Annotated[t | None | _Unset, ClearableField()] dynamically."""
    return Annotated[Union[t, None, _Unset], ClearableField()]


# ─── Test models ───────────────────────────────────────────────────────────

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


# 3a: Concrete Annotated aliases
class EditTaskConcrete(CommandModel):
    id: str
    name: PatchStr = UNSET
    flagged: PatchBool = UNSET
    note: ClearableStr = UNSET
    due_date: ClearableStr = UNSET
    estimated_minutes: ClearableFloat = UNSET


# 3b: Function-based (if it works)
try:
    class EditTaskFunction(CommandModel):
        id: str
        name: Patch(str) = UNSET  # type: ignore[valid-type]
        flagged: Patch(bool) = UNSET  # type: ignore[valid-type]
        note: Clearable(str) = UNSET  # type: ignore[valid-type]
        due_date: Clearable(str) = UNSET  # type: ignore[valid-type]
        estimated_minutes: Clearable(float) = UNSET  # type: ignore[valid-type]

    FUNCTION_MODEL_WORKS = True
except Exception as e:
    FUNCTION_MODEL_WORKS = False
    print(f"Function-based model FAILED: {e}")


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
        if "PatchField" in raw or "ClearableField" in raw:
            problems.append("Metadata marker leaked into schema")

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
            print("PASS: Clean schema, no $defs, no default leak, no metadata leak")
    except Exception as e:
        print(f"FAIL: Schema generation error: {e}")


def main() -> None:
    print("=" * 60)
    print("  Approach 3: Annotated with metadata")
    print("=" * 60)

    check_schema("3a: Concrete Annotated (PatchStr, ClearableStr)", EditTaskConcrete)

    if FUNCTION_MODEL_WORKS:
        check_schema("3b: Function-based Patch(str), Clearable(str)", EditTaskFunction)  # type: ignore[possibly-undefined]
    else:
        print("\n=== 3b: Function-based ===")
        print("SKIP: Could not define model")

    # Test semantics for concrete version
    print("\n--- Semantics (concrete) ---")
    cmd = EditTaskConcrete(id="t1")
    print(f"Defaults: name={cmd.name!r}, note={cmd.note!r}")
    cmd2 = EditTaskConcrete(id="t2", name="Hi", note=None)
    print(f"Set+clear: name={cmd2.name!r}, note={cmd2.note!r}")


if __name__ == "__main__":
    main()
