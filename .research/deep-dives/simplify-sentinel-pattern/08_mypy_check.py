"""Mypy compatibility check for passing approaches.

Run: uv run mypy .research/deep-dives/simplify-sentinel-pattern/08_mypy_check.py --no-error-summary --show-error-codes

Expected: zero errors. Each approach is annotated with expected behavior.
"""

from __future__ import annotations

from typing import Any, TypeAlias, TypeVar, Union

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


# Approach 2: TypeVar + Union generic aliases
# mypy resolves Patch[str] to Union[str, _Unset]. Type narrowing works.

Patch = Union[T, _Unset]
Clearable = Union[T, None, _Unset]

class Model2(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Patch[str] = UNSET
    note: Clearable[str] = UNSET

def use_model2(m: Model2) -> str:
    if isinstance(m.name, _Unset):
        return "unset"
    return m.name  # mypy knows this is str after narrowing

def use_clearable2(m: Model2) -> str | None:
    if isinstance(m.note, _Unset):
        return "unset"
    return m.note  # mypy knows this is str | None


# Approach 4: Concrete TypeAlias (no generics)
# Plain aliases, fully transparent to mypy.

PatchStr: TypeAlias = str | _Unset
PatchBool: TypeAlias = bool | _Unset
ClearableStr: TypeAlias = str | None | _Unset
ClearableFloat: TypeAlias = float | None | _Unset

class Model4(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: PatchStr = UNSET
    flagged: PatchBool = UNSET
    note: ClearableStr = UNSET
    estimated_minutes: ClearableFloat = UNSET

def use_model4(m: Model4) -> str:
    if isinstance(m.name, _Unset):
        return "unset"
    return m.name
