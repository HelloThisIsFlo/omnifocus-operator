"""Approach 7: Other creative approaches.

7a: Generic class with __class_getitem__ that returns a union type
7b: typing.get_type_hints resolution — do aliases resolve transparently?
7c: __pydantic_init_subclass__ or model_post_init schema patching

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/07_other_approaches.py
"""

from __future__ import annotations

import json
from typing import Any, Union, get_type_hints

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


# ─── Approach 7a: Class with __class_getitem__ returning Union ─────────────

class Patch:
    """Pseudo-generic that returns Union[T, _Unset] when subscripted."""
    def __class_getitem__(cls, item: type) -> Any:
        return Union[item, _Unset]

class Clearable:
    """Pseudo-generic that returns Union[T, None, _Unset] when subscripted."""
    def __class_getitem__(cls, item: type) -> Any:
        return Union[item, None, _Unset]


class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

try:
    class EditTask7a(CommandModel):
        id: str
        name: Patch[str] = UNSET
        flagged: Patch[bool] = UNSET
        note: Clearable[str] = UNSET
        due_date: Clearable[str] = UNSET
        estimated_minutes: Clearable[float] = UNSET

    MODEL_7A = True
    print("7a (class __class_getitem__): Model defined OK")
except Exception as e:
    MODEL_7A = False
    print(f"7a FAILED at model definition: {e}")


# ─── Approach 7b: Check type hint resolution ──────────────────────────────

if MODEL_7A:
    print("\n--- 7b: Type hint resolution ---")
    # Does get_type_hints see the resolved union or the Patch wrapper?
    try:
        hints = get_type_hints(EditTask7a)  # type: ignore[possibly-undefined]
        for field_name in ["name", "note"]:
            print(f"  {field_name}: {hints.get(field_name)}")
    except Exception as e:
        print(f"  get_type_hints failed: {e}")


# ─── Approach 7c: model_rebuild + __class_getitem__ with deferred eval ────

# With `from __future__ import annotations`, all annotations are strings.
# Pydantic resolves them at model_rebuild time. Does __class_getitem__
# still work when the annotation is evaluated from a string?

# Already tested above — if 7a works with `from __future__ import annotations`,
# then string eval + __class_getitem__ works.


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
        if "Patch" in raw or "Clearable" in raw:
            problems.append("Alias class name leaked")

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

    except Exception as e:
        print(f"FAIL: Schema generation error: {e}")


def main() -> None:
    print("=" * 60)
    print("  Approach 7: Other creative approaches")
    print("=" * 60)

    if MODEL_7A:
        check_schema("7a: __class_getitem__ returning Union", EditTask7a)  # type: ignore[possibly-undefined]

        # Semantics
        print("\n--- Semantics ---")
        cmd = EditTask7a(id="t1")
        print(f"Defaults: name={cmd.name!r}, note={cmd.note!r}")
        cmd2 = EditTask7a(id="t2", name="Hi", note=None)
        print(f"Set+clear: name={cmd2.name!r}, note={cmd2.note!r}")
    else:
        print("\n7a: SKIP (model definition failed)")


if __name__ == "__main__":
    main()
