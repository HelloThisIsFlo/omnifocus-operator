"""Service-layer exceptions — structured errors for resolver and domain operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.agent_messages.errors import ENTITY_TYPE_MISMATCH

if TYPE_CHECKING:
    from omnifocus_operator.models.enums import EntityType


class EntityTypeMismatchError(ValueError):
    """A resolved entity's type does not match what the caller accepts.

    Carries structured data so callers can format context-aware messages.
    Subclasses ValueError so existing generic catches still work.
    """

    def __init__(
        self,
        value: str,
        *,
        resolved_type: EntityType,
        accepted_types: list[EntityType],
    ) -> None:
        self.value = value
        self.resolved_type = resolved_type
        self.accepted_types = accepted_types
        accepted = ", ".join(t.value for t in accepted_types)
        super().__init__(
            ENTITY_TYPE_MISMATCH.format(
                value=value,
                resolved_type=resolved_type.value,
                accepted=accepted,
            )
        )
