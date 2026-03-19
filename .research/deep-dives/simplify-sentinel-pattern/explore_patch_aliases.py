"""Exploration: Can Pydantic handle Patch[T] / Clearable[T] type aliases?

Run with: uv run python .research/deep-dives/simplify-sentinel-pattern/explore_patch_aliases.py

Tests three things:
1. Does Pydantic resolve Patch[T] / Clearable[T] in model fields?
2. Does model_json_schema() produce clean output (no _UnsetType)?
3. Do the semantics work: UNSET vs None vs value?
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

# ─── Sentinel ───────────────────────────────────────────

class _UnsetType(Enum):
    UNSET = "UNSET"

    @classmethod
    def __get_pydantic_core_schema__(
        cls,
        _source_type: Any,
        _handler: GetCoreSchemaHandler,
    ) -> CoreSchema:
        return core_schema.is_instance_schema(cls)

    def __repr__(self) -> str:
        return "UNSET"

UNSET = _UnsetType.UNSET

# ─── Type aliases (Python 3.12+) ───────────────────────

type Patch[T] = T | _UnsetType
type Clearable[T] = T | None | _UnsetType

# ─── Base model ─────────────────────────────────────────

class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")

    def changed_fields(self) -> dict[str, Any]:
        return {
            name: value
            for name, value in self.__dict__.items()
            if not isinstance(value, _UnsetType)
        }

# ─── Test model ─────────────────────────────────────────

class EditTaskCommand(CommandModel):
    id: str
    name: Patch[str] = UNSET
    flagged: Patch[bool] = UNSET
    note: Clearable[str] = UNSET
    due_date: Clearable[str] = UNSET
    actions: Patch[str] = UNSET  # simplified, just testing the alias


# ─── Exploration ────────────────────────────────────────

def section(title: str) -> None:
    print(f"\n{'─' * 60}")
    print(f"  {title}")
    print(f"{'─' * 60}")


def main() -> None:
    # 1. Can we even define the model?
    section("1. Model definition")
    print("EditTaskCommand defined successfully")
    print(f"Fields: {list(EditTaskCommand.model_fields.keys())}")

    # 2. Schema generation
    section("2. JSON schema")
    import json
    try:
        schema = EditTaskCommand.model_json_schema()
        print(json.dumps(schema, indent=2))
        raw = json.dumps(schema)
        if "_Unset" in raw or "_UnsetType" in raw:
            print("\n⚠️  PROBLEM: sentinel leaked into schema!")
        else:
            print("\n✅ Schema is clean — no sentinel leakage")
    except Exception as e:
        print(f"❌ Schema generation failed: {e}")

    # 3. Semantics: construct with various field states
    section("3. Patch semantics")

    # All defaults (only id provided)
    cmd = EditTaskCommand(id="t1")
    print(f"Only id:        name={cmd.name!r}, note={cmd.note!r}")
    print(f"  changed_fields: {cmd.changed_fields()}")

    # Set name, clear note
    cmd2 = EditTaskCommand(id="t2", name="Updated", note=None)
    print(f"Set+clear:      name={cmd2.name!r}, note={cmd2.note!r}")
    print(f"  changed_fields: {cmd2.changed_fields()}")

    # Set everything
    cmd3 = EditTaskCommand(id="t3", name="Full", flagged=True, note="hello", due_date="2026-01-01")
    print(f"Full:           name={cmd3.name!r}, note={cmd3.note!r}, flagged={cmd3.flagged!r}")
    print(f"  changed_fields: {cmd3.changed_fields()}")

    # 4. Truthiness of UNSET (the __bool__ change)
    section("4. UNSET truthiness")
    print(f"bool(UNSET) = {bool(UNSET)}")
    print(f"UNSET is UNSET = {UNSET is UNSET}")
    print(f"isinstance(UNSET, _UnsetType) = {isinstance(UNSET, _UnsetType)}")

    # 5. model_validate from dict (simulates agent JSON input)
    section("5. model_validate from dict (agent input)")
    try:
        from_agent = EditTaskCommand.model_validate({"id": "t4", "note": None, "flagged": True})
        print(f"Parsed:         name={from_agent.name!r}, note={from_agent.note!r}, flagged={from_agent.flagged!r}")
        print(f"  changed_fields: {from_agent.changed_fields()}")
    except Exception as e:
        print(f"❌ model_validate failed: {e}")

    # 6. Extra field rejection (extra=forbid still works?)
    section("6. Extra field rejection")
    try:
        EditTaskCommand.model_validate({"id": "t5", "bogus": "x"})
        print("❌ Should have rejected bogus field!")
    except Exception as e:
        print(f"✅ Rejected: {e.__class__.__name__}")

    # 7. Required field only
    section("7. Required fields")
    print(f"Required: {[k for k, v in EditTaskCommand.model_fields.items() if v.is_required()]}")


if __name__ == "__main__":
    main()
