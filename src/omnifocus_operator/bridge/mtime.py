"""MtimeSource protocol and implementations -- data-source freshness checks.

MtimeSource defines a pluggable interface for checking whether the OmniFocus
data source has changed.  FileMtimeSource is the production implementation
that monitors a filesystem path's modification time using ``st_mtime_ns``
(nanosecond precision).  ConstantMtimeSource always returns 0 for use with
InMemoryBridge (no cache invalidation).
"""

from __future__ import annotations

import asyncio
import os
from typing import Protocol, runtime_checkable

__all__ = [
    "ConstantMtimeSource",
    "FileMtimeSource",
    "MtimeSource",
]


@runtime_checkable
class MtimeSource(Protocol):
    """Protocol for checking data-source freshness.

    Implementations return an integer nanosecond mtime.  A change in the
    returned value signals that the underlying data has been modified and
    the repository cache should be refreshed.
    """

    async def get_mtime_ns(self) -> int: ...


class FileMtimeSource:
    """Production mtime source backed by filesystem stat.

    Calls ``os.stat`` via ``asyncio.to_thread`` to avoid blocking the
    event loop, and returns ``stat_result.st_mtime_ns`` for nanosecond
    precision.
    """

    def __init__(self, path: str) -> None:
        self._path = path

    async def get_mtime_ns(self) -> int:
        """Return the modification time of *path* in nanoseconds."""
        stat_result = await asyncio.to_thread(os.stat, self._path)
        return stat_result.st_mtime_ns


class ConstantMtimeSource:
    """MtimeSource that always returns 0 -- no cache invalidation.

    Designed for use with ``InMemoryBridge`` where the underlying data
    never changes on disk.  Because the mtime is constant, the repository
    will load once and serve from cache thereafter.
    """

    async def get_mtime_ns(self) -> int:
        """Always return 0 (data is never stale)."""
        return 0
