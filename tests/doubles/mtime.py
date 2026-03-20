"""ConstantMtimeSource -- test double that never triggers cache invalidation."""

from __future__ import annotations

from omnifocus_operator.bridge.mtime import MtimeSource


class ConstantMtimeSource(MtimeSource):
    """MtimeSource that always returns 0 -- no cache invalidation.

    Used with test doubles (InMemoryBridge, SimulatorBridge) where
    cache staleness detection is not needed.  Because the mtime is constant,
    the repository will load once and serve from cache thereafter.
    """

    async def get_mtime_ns(self) -> int:
        """Always return 0 (data is never stale)."""
        return 0
