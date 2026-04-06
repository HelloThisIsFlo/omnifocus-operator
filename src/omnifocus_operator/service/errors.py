"""Service-layer exceptions — structured errors for resolver and domain operations."""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.agent_messages.errors import AMBIGUOUS_NAME_MATCH, ENTITY_TYPE_MISMATCH

if TYPE_CHECKING:
    from collections.abc import Sequence

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
        accepted = "/".join(t.value for t in accepted_types)
        super().__init__(
            ENTITY_TYPE_MISMATCH.format(
                value=value,
                resolved_type=resolved_type.value,
                accepted=accepted,
            )
        )


class AmbiguousNameError(ValueError):
    """Multiple entities matched a name query.

    Carries structured data so callers can inspect matches programmatically.
    Subclasses ValueError so existing generic catches still work.
    """

    def __init__(
        self,
        name: str,
        *,
        accepted_types: list[EntityType],
        matches: Sequence[tuple[str, str]],
    ) -> None:
        self.name = name
        self.accepted_types = accepted_types
        self.matches = matches
        entity_type = "/".join(t.value for t in accepted_types)
        match_pairs = ", ".join(f"{mid} ({mname})" for mid, mname in matches)
        super().__init__(
            AMBIGUOUS_NAME_MATCH.format(
                entity_type=entity_type,
                name=name,
                matches=match_pairs,
            )
        )
