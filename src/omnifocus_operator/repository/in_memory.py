"""InMemoryRepository -- returns a pre-built snapshot without bridge interaction."""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.models.snapshot import DatabaseSnapshot

__all__ = ["InMemoryRepository"]


class InMemoryRepository:
    """Repository backed by a pre-built ``DatabaseSnapshot``.

    Useful for testing where no bridge, adapter, or caching is needed.
    Simply returns the snapshot passed at construction time.
    """

    def __init__(self, snapshot: DatabaseSnapshot) -> None:
        self._snapshot = snapshot

    async def get_snapshot(self) -> DatabaseSnapshot:
        """Return the pre-built snapshot."""
        return self._snapshot
