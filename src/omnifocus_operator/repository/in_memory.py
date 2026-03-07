"""InMemoryRepository -- returns pre-built entities without bridge interaction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.models.snapshot import AllEntities

__all__ = ["InMemoryRepository"]


class InMemoryRepository:
    """Repository backed by a pre-built ``AllEntities`` instance.

    Useful for testing where no bridge, adapter, or caching is needed.
    Simply returns the data passed at construction time.
    """

    def __init__(self, snapshot: AllEntities) -> None:
        self._snapshot = snapshot

    async def get_all(self) -> AllEntities:
        """Return all pre-built entities."""
        return self._snapshot
