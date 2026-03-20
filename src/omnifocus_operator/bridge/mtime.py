"""MtimeSource protocol and FileMtimeSource -- data-source freshness checks.

MtimeSource defines a pluggable interface for checking whether the OmniFocus
data source has changed.  FileMtimeSource is the production implementation
that monitors a filesystem path's modification time using ``st_mtime_ns``
(nanosecond precision).
"""

from __future__ import annotations

import asyncio
import os
from typing import Protocol, runtime_checkable

__all__ = [
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


class FileMtimeSource(MtimeSource):
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
