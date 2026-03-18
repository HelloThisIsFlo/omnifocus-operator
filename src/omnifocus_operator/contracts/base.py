"""Base contract infrastructure: CommandModel, UNSET sentinel.

CommandModel is the base class for all command-layer models (agent instructions,
repo payloads). It inherits OmniFocusBaseModel's camelCase aliasing and adds
extra="forbid" to reject unknown fields at validation time.
"""

from __future__ import annotations

from typing import Any

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


class CommandModel(OmniFocusBaseModel):
    """Base for all command-layer models. Rejects unknown fields at validation time."""

    model_config = ConfigDict(extra="forbid")


__all__ = ["UNSET", "CommandModel", "_Unset"]
