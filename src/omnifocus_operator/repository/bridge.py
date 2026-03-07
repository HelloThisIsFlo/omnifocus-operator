"""BridgeRepository -- caching repository that loads data via the bridge.

Combines the ``Bridge`` protocol, ``MtimeSource`` for cache invalidation, and
the ``adapt_snapshot`` adapter into a single caching layer.

Design decisions (from phase 04 research + user choices):
- Fail-fast: errors propagate raw to the caller, no stale fallback.
- No retry/cooldown: next ``get_all()`` simply tries again.
- The ENTIRE get_all() flow (mtime check + conditional refresh)
  runs under the lock so all reads block while a refresh is in progress.
"""

from __future__ import annotations

import asyncio
from typing import TYPE_CHECKING, Any

from omnifocus_operator.bridge.adapter import adapt_snapshot
from omnifocus_operator.models.snapshot import AllEntities

if TYPE_CHECKING:
    from omnifocus_operator.bridge.mtime import MtimeSource
    from omnifocus_operator.bridge.protocol import Bridge
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task

__all__ = ["BridgeRepository"]


class BridgeRepository:
    """Caching repository that loads data from the bridge.

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
        self._cached: AllEntities | None = None
        self._last_mtime_ns: int = 0

    async def get_all(self) -> AllEntities:
        """Return all OmniFocus entities, refreshing if stale.

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

            if self._cached is None or current_mtime != self._last_mtime_ns:
                self._cached = await self._refresh(current_mtime)

            return self._cached

    async def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        all_entities = await self.get_all()
        return next((t for t in all_entities.tasks if t.id == task_id), None)

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        all_entities = await self.get_all()
        return next((p for p in all_entities.projects if p.id == project_id), None)

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
        all_entities = await self.get_all()
        return next((t for t in all_entities.tags if t.id == tag_id), None)

    async def _refresh(self, current_mtime: int) -> AllEntities:
        """Fetch fresh data from the bridge and update cache state.

        On success, updates ``_cached`` and ``_last_mtime_ns``.
        On failure, cache is **not** modified (preserves old or None).
        """
        raw: dict[str, Any] = await self._bridge.send_command("snapshot")
        # Transform bridge-format -> new model shape (no-op if already new shape)
        adapt_snapshot(raw)
        result = AllEntities.model_validate(raw)
        self._last_mtime_ns = current_mtime
        return result
