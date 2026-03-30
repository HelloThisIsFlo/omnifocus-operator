"""Base contract infrastructure: StrictModel, CommandModel, QueryModel, UNSET sentinel.

StrictModel is the base for all agent-facing contract models with extra="forbid".
CommandModel (write-side) and QueryModel (read-side) are siblings that inherit from it.
"""

from __future__ import annotations

from typing import Any, TypeGuard, TypeVar, Union

from pydantic import ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, core_schema

from omnifocus_operator.models.base import OmniFocusBaseModel

# --- UNSET sentinel ---
# Distinguishes "field omitted" (no change) from "field set to null" (clear).
# Used as default for all optional fields on patch models.


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
        """Tell Pydantic how to validate _Unset.

        Uses is_instance_schema so Pydantic accepts the UNSET singleton
        during validation but excludes it from JSON schema automatically.
        """
        return core_schema.is_instance_schema(cls)


UNSET = _Unset()

# --- Patch type aliases ---
# Make patch semantics self-documenting in field annotations.
# Pydantic resolves these to plain unions at model creation time --
# JSON schema output is identical to writing the union directly.

T = TypeVar("T")

# Union[] required: pipe syntax breaks TypeVar resolution in Pydantic schema generation.
Patch = Union[T, _Unset]  # noqa: UP007
"""Field can be set or omitted (UNSET). Cannot be cleared to None."""

PatchOrClear = Union[T, None, _Unset]  # noqa: UP007
"""Field can be set, cleared (None), or omitted (UNSET). None means 'clear the value'."""

PatchOrNone = Union[T, None, _Unset]  # noqa: UP007
"""Field can be set, set to None, or omitted (UNSET). None carries domain meaning, not 'clear'.
Same union as PatchOrClear -- the distinct name signals that None is a meaningful value
(e.g., MoveAction.ending = None means 'inbox'), not a clear instruction."""


def is_set[T](value: T | _Unset) -> TypeGuard[T]:
    """True if value was explicitly provided (not UNSET)."""
    return not isinstance(value, _Unset)


class StrictModel(OmniFocusBaseModel):
    """Base for all agent-facing contract models. Rejects unknown fields."""

    model_config = ConfigDict(extra="forbid")


class CommandModel(StrictModel):
    """Write-side contracts: commands, payloads, results, specs, actions."""

    def changed_fields(self) -> dict[str, Any]:
        """Return only fields explicitly set by the caller (UNSET values excluded)."""
        return {name: value for name, value in self.__dict__.items() if is_set(value)}


class QueryModel(StrictModel):
    """Read-side contracts: query filters and pagination."""

    pass


__all__ = [
    "UNSET",
    "CommandModel",
    "Patch",
    "PatchOrClear",
    "PatchOrNone",
    "QueryModel",
    "StrictModel",
    "_Unset",
    "is_set",
]
