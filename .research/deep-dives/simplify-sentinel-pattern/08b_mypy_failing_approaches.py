"""Mypy check for approaches expected to have issues.

Run: uv run mypy .research/deep-dives/simplify-sentinel-pattern/08b_mypy_failing_approaches.py --no-error-summary --show-error-codes

This file documents which approaches fail mypy and how.
"""

from __future__ import annotations

from typing import Any, TypeVar, Union

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


# Approach 7a: __class_getitem__ - mypy doesn't understand runtime behavior
class Patch7:
    def __class_getitem__(cls, item: type) -> Any:
        return Union[item, _Unset]

class Clearable7:
    def __class_getitem__(cls, item: type) -> Any:
        return Union[item, None, _Unset]

class Model7(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: Patch7[str] = UNSET  # type: ignore[type-arg, assignment]
    note: Clearable7[str] = UNSET  # type: ignore[type-arg, assignment]

# mypy sees m.name as Patch7, not str | _Unset
def use_model7(m: Model7) -> str:
    if isinstance(m.name, _Unset):
        return "unset"
    return m.name  # type: ignore[return-value]


# Approach 3b: Function-based Patch(str)
T = TypeVar("T")

def PatchFn(t: type) -> Any:
    from typing import Annotated
    return Annotated[Union[t, _Unset], "patch"]

def ClearableFn(t: type) -> Any:
    from typing import Annotated
    return Annotated[Union[t, None, _Unset], "clearable"]

class Model3b(BaseModel):
    model_config = ConfigDict(extra="forbid")
    name: PatchFn(str) = UNSET  # type: ignore[valid-type]
    note: ClearableFn(str) = UNSET  # type: ignore[valid-type]

# mypy can't resolve function call results as types
def use_model3b(m: Model3b) -> str:
    if isinstance(m.name, _Unset):
        return "unset"
    return m.name  # type: ignore[return-value]
