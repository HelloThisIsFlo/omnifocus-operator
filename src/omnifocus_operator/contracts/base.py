"""Base contract infrastructure: StrictModel, CommandModel, QueryModel, UNSET sentinel.

StrictModel is the base for all agent-facing contract models with extra="forbid".
CommandModel (write-side) and QueryModel (read-side) are siblings that inherit from it.
"""

from __future__ import annotations

from typing import Any, TypeGuard, TypeVar, Union

from pydantic import BaseModel, ConfigDict, GetCoreSchemaHandler
from pydantic_core import CoreSchema, PydanticUndefined, core_schema

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


def is_set[T](value: T | _Unset) -> TypeGuard[T]:
    """True if value was explicitly provided (not UNSET)."""
    return not isinstance(value, _Unset)


def is_non_default(model: BaseModel, field_name: str) -> bool:
    """True if the named field has a value differing from its declared default.

    Value-aware predicate that dispatches on field type:
    - ``Patch[T]`` field (default=UNSET) -> equivalent to ``is_set``: a value
      that is not the ``_Unset`` sentinel is non-default.
    - Regular field with a concrete ``Field(default=...)`` -> compares
      ``getattr(model, field_name)`` against ``model_fields[field_name].default``
      via stdlib ``!=``.
    - Regular field with ``Field(default_factory=...)`` -> calls the factory
      once to produce a fresh baseline instance and compares against it.
    - Required field (no default, no factory) -> always non-default (if the
      field were unset, Pydantic validation would have rejected the model).

    Reads the default from Pydantic's ``model_fields``. Pydantic v2 stores the
    literal default on ``FieldInfo.default`` for ``Field(default=[...])``,
    which makes mutable-default comparison correct out of the box
    (e.g. ``Field(default=[AvailabilityFilter.REMAINING])`` produces a
    FieldInfo whose ``.default`` is the literal list).

    **List equality is order-sensitive** -- stdlib ``==`` on lists compares
    element-wise in order. This is intentional and is the contract. For
    single-element defaults (like the current ``availability=[REMAINING]``)
    ordering is moot. If a future default is a multi-element list,
    reordering it at the contract level would be an API-breaking change
    (schema version bump), not a runtime concern -- the drift test at CI
    gates any classification/default mismatch.

    Introduced in Phase 57-05 (UAT-57 G4 fix) so ``_SUBTREE_PRUNING_FIELDS``
    can classify non-Patch filter fields (e.g. ``availability``) alongside
    Patch fields under a single value-aware predicate.
    """
    value = getattr(model, field_name)
    if isinstance(value, _Unset):
        return False
    field_info = type(model).model_fields[field_name]
    if field_info.default is PydanticUndefined:
        # default_factory path, or a required field.
        if field_info.default_factory is None:
            # Required field (no default, no factory) -- always set.
            return True
        baseline = field_info.default_factory()  # type: ignore[call-arg]
    else:
        baseline = field_info.default
    return bool(value != baseline)


def unset_to_none[T](value: T | _Unset) -> T | None:
    """Convert UNSET to None for service/repo boundary translation."""
    if isinstance(value, _Unset):
        return None
    return value


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
    "QueryModel",
    "StrictModel",
    "_Unset",
    "is_non_default",
    "is_set",
    "unset_to_none",
]
