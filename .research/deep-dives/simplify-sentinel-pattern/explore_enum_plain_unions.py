"""Exploration: Enum sentinel with plain unions (no type aliases).

Run with: uv run python .research/deep-dives/simplify-sentinel-pattern/explore_enum_plain_unions.py

Compares against the Patch[T] alias approach to see if the $defs noise
and default leakage are caused by the aliases or the Enum itself.
"""

from __future__ import annotations

from enum import Enum
from typing import Any

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema


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


class CommandModel(BaseModel):
    model_config = ConfigDict(extra="forbid")


class EditTaskCommand(CommandModel):
    id: str
    name: str | _UnsetType = UNSET
    flagged: bool | _UnsetType = UNSET
    note: str | None | _UnsetType = UNSET
    due_date: str | None | _UnsetType = UNSET


def main() -> None:
    import json

    schema = EditTaskCommand.model_json_schema()
    print(json.dumps(schema, indent=2))

    raw = json.dumps(schema)
    has_default = '"default"' in raw
    has_defs = '"$defs"' in raw
    print(f"\ndefault leaks? {has_default}")
    print(f"$defs noise?   {has_defs}")


if __name__ == "__main__":
    main()
