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
import logging
from typing import TYPE_CHECKING, Any

from omnifocus_operator.bridge.adapter import adapt_snapshot
from omnifocus_operator.models.snapshot import AllEntities

logger = logging.getLogger("omnifocus_operator")

if TYPE_CHECKING:
    from omnifocus_operator.bridge.mtime import MtimeSource
    from omnifocus_operator.contracts.protocols import Bridge
    from omnifocus_operator.contracts.use_cases.create_task import (
        CreateTaskRepoPayload,
        CreateTaskRepoResult,
    )
    from omnifocus_operator.contracts.use_cases.edit_task import (
        EditTaskRepoPayload,
        EditTaskRepoResult,
    )
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
                logger.debug("BridgeRepository.get_all: cache miss/stale, refreshing via bridge")
                self._cached = await self._refresh(current_mtime)
            else:
                logger.debug(
                    "BridgeRepository.get_all: cache hit, tasks=%d, projects=%d, tags=%d",
                    len(self._cached.tasks),
                    len(self._cached.projects),
                    len(self._cached.tags),
                )

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

    async def add_task(self, payload: CreateTaskRepoPayload) -> CreateTaskRepoResult:
        """Create a task via bridge and invalidate cache.

        Serializes the typed payload to a camelCase dict and sends via bridge.
        """
        from omnifocus_operator.contracts.use_cases.create_task import CreateTaskRepoResult

        raw = payload.model_dump(by_alias=True, exclude_none=True)

        logger.debug("BridgeRepository.add_task: sending to bridge")
        result = await self._bridge.send_command("add_task", raw)
        # Invalidate cache so next get_all fetches fresh data
        self._cached = None
        logger.debug("BridgeRepository.add_task: cache invalidated, id=%s", result["id"])

        return CreateTaskRepoResult(id=result["id"], name=result["name"])

    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult:
        """Edit a task via bridge and invalidate cache."""
        from omnifocus_operator.contracts.use_cases.edit_task import EditTaskRepoResult

        raw = payload.model_dump(by_alias=True, exclude_unset=True)

        logger.debug("BridgeRepository.edit_task: sending to bridge")
        result = await self._bridge.send_command("edit_task", raw)
        self._cached = None
        logger.debug("BridgeRepository.edit_task: cache invalidated, id=%s", result.get("id"))
        return EditTaskRepoResult(id=result["id"], name=result["name"])

    async def _refresh(self, current_mtime: int) -> AllEntities:
        """Fetch fresh data from the bridge and update cache state.

        On success, updates ``_cached`` and ``_last_mtime_ns``.
        On failure, cache is **not** modified (preserves old or None).
        """
        logger.debug("BridgeRepository._refresh: fetching full snapshot via bridge")
        raw: dict[str, Any] = await self._bridge.send_command("get_all")
        # Transform bridge-format -> new model shape (no-op if already new shape)
        adapt_snapshot(raw)
        result = AllEntities.model_validate(raw)
        self._last_mtime_ns = current_mtime
        logger.debug(
            "BridgeRepository._refresh: tasks=%d, projects=%d, tags=%d",
            len(result.tasks),
            len(result.projects),
            len(result.tags),
        )
        return result
