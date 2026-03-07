"""Repository protocol -- structural typing interface for OmniFocus data access."""

from __future__ import annotations

from typing import TYPE_CHECKING, Protocol, runtime_checkable

if TYPE_CHECKING:
    from omnifocus_operator.models.snapshot import AllEntities

__all__ = ["Repository"]


@runtime_checkable
class Repository(Protocol):
    """Protocol for OmniFocus data repositories.

    Any class with a matching ``async get_all`` method satisfies this
    protocol via structural subtyping -- no inheritance required.
    """

    async def get_all(self) -> AllEntities:
        """Return all OmniFocus entities."""
        ...
