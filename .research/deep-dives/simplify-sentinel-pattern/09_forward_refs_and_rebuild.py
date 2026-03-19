"""Test forward reference resolution and model_rebuild() for passing approaches.

Important because the real codebase uses `from __future__ import annotations`
which makes all annotations strings that get resolved later.

Run: uv run python .research/deep-dives/simplify-sentinel-pattern/09_forward_refs_and_rebuild.py
"""

from __future__ import annotations

import json
from typing import Any, TypeAlias, TypeVar, Union

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


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


# ─── Generic aliases (approach 2) ─────────────────────────────────────────

Patch = Union[T, _Unset]
Clearable = Union[T, None, _Unset]


# ─── Test 1: Forward reference to another model ───────────────────────────

class SubAction(BaseModel):
    model_config = ConfigDict(extra="forbid")
    target: str

class MainModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Patch[str] = UNSET
    note: Clearable[str] = UNSET
    action: Patch[SubAction] = UNSET  # nested model reference


# ─── Test 2: model_rebuild with update_forward_refs ───────────────────────

# Simulate a case where the model references a type not yet defined
class Container(BaseModel):
    model_config = ConfigDict(extra="forbid")
    items: Patch[list[Item]] = UNSET  # type: ignore[type-arg]

class Item(BaseModel):
    name: str
    value: int

# Rebuild to resolve forward ref
Container.model_rebuild()


# ─── Test 3: Concrete TypeAlias (approach 4) with forward refs ─────────────

PatchStr: TypeAlias = str | _Unset

class ConcreteModel(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: PatchStr = UNSET


# ─── Run checks ───────────────────────────────────────────────────────────

def check(name: str, model_cls: type) -> None:
    print(f"\n=== {name} ===")
    try:
        schema = model_cls.model_json_schema()
        raw = json.dumps(schema, indent=2)

        has_defs = "$defs" in schema
        # SubAction $def is expected (it's a real nested model, not an alias)
        alias_defs = [k for k in schema.get("$defs", {})
                      if k.startswith(("Patch_", "Clearable_"))]

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

        # Show schema compactly
        print(f"  $defs keys: {list(schema.get('$defs', {}).keys())}")
        props = schema.get("properties", {})
        for k, v in props.items():
            print(f"  {k}: {json.dumps(v)}")

    except Exception as e:
        print(f"FAIL: {e}")

    # Test instantiation
    try:
        inst = model_cls.model_validate({"name": "test"})
        print(f"  Instantiation: OK (name={inst.name!r})")
    except Exception as e:
        print(f"  Instantiation: FAIL ({e})")


def main() -> None:
    print("=" * 60)
    print("  Forward refs and model_rebuild()")
    print("=" * 60)

    check("Approach 2: Nested model (SubAction)", MainModel)
    check("Approach 2: Forward ref + model_rebuild", Container)
    check("Approach 4: Concrete TypeAlias", ConcreteModel)


if __name__ == "__main__":
    main()
