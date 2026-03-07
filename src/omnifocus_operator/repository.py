"""Repository module -- caching layer between service and bridge.

Combines the ``MtimeSource`` protocol and implementations with the
``OmniFocusRepository`` caching repository.

MtimeSource defines a pluggable interface for checking whether the OmniFocus
data source has changed.  FileMtimeSource is the production implementation
that monitors a filesystem path's modification time using ``st_mtime_ns``
(nanosecond precision).  ConstantMtimeSource always returns 0 for use with
InMemoryBridge (no cache invalidation).

OmniFocusRepository loads a full ``DatabaseSnapshot`` via the bridge, serves
reads from an in-memory cache, and refreshes only when the ``MtimeSource``
reports a change.

Design decisions (from phase 04 research + user choices):
- Fail-fast: errors propagate raw to the caller, no stale fallback.
- No retry/cooldown: next ``get_snapshot()`` simply tries again.
- The ENTIRE get_snapshot() flow (mtime check + conditional refresh)
  runs under the lock so all reads block while a refresh is in progress.
"""

from __future__ import annotations

import asyncio
import os
from typing import TYPE_CHECKING, Any, Protocol, runtime_checkable

from omnifocus_operator.models.snapshot import DatabaseSnapshot

if TYPE_CHECKING:
    from omnifocus_operator.bridge.protocol import Bridge

__all__ = [
    "ConstantMtimeSource",
    "FileMtimeSource",
    "MtimeSource",
    "OmniFocusRepository",
]


# ---------------------------------------------------------------------------
# MtimeSource protocol and implementations
# ---------------------------------------------------------------------------


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


# ---------------------------------------------------------------------------
# OmniFocusRepository
# ---------------------------------------------------------------------------


class OmniFocusRepository:
    """Caching repository that loads snapshots from the bridge.

    Parameters
    ----------
    bridge:
        Bridge implementation used to fetch OmniFocus data.
    mtime_source:
        Source of modification timestamps used to decide when the cache
        is stale and a new bridge dump is needed.
    """

    def __init__(self, bridge: Bridge, mtime_source: MtimeSource) -> None:
        self._bridge = bridge
        self._mtime_source = mtime_source
        self._lock = asyncio.Lock()
        self._snapshot: DatabaseSnapshot | None = None
        self._last_mtime_ns: int = 0

    async def get_snapshot(self) -> DatabaseSnapshot:
        """Return the current ``DatabaseSnapshot``, refreshing if stale.

        The mtime source is checked on every call.  If the mtime has
        changed (or the cache is empty), a fresh dump is fetched from the
        bridge and cached.  Concurrent callers share the same lock so
        only one dump runs at a time.

        Raises
        ------
        BridgeError
            If the bridge fails during a dump.
        pydantic.ValidationError
            If the bridge response cannot be parsed.
        OSError
            If the mtime source fails (e.g. missing path).
        """
        async with self._lock:
            current_mtime = await self._mtime_source.get_mtime_ns()

            if self._snapshot is None or current_mtime != self._last_mtime_ns:
                self._snapshot = await self._refresh(current_mtime)

            return self._snapshot

    async def _refresh(self, current_mtime: int) -> DatabaseSnapshot:
        """Fetch a fresh snapshot from the bridge and update cache state.

        On success, updates ``_snapshot`` and ``_last_mtime_ns``.
        On failure, cache is **not** modified (preserves old or None).
        """
        raw: dict[str, Any] = await self._bridge.send_command("snapshot")
        snapshot = DatabaseSnapshot.model_validate(raw)
        self._last_mtime_ns = current_mtime
        return snapshot
