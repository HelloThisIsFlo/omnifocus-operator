"""BridgeOnlyRepository -- caching repository that loads data via the bridge.

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

from omnifocus_operator.config import SYSTEM_LOCATIONS
from omnifocus_operator.contracts.protocols import Repository
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoResult
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoResult
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.repository.bridge_only.adapter import adapt_snapshot
from omnifocus_operator.repository.bridge_write_mixin import BridgeWriteMixin
from omnifocus_operator.repository.pagination import paginate

logger = logging.getLogger(__name__)

if TYPE_CHECKING:
    from omnifocus_operator.bridge.mtime import MtimeSource
    from omnifocus_operator.contracts.protocols import Bridge
    from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoPayload
    from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoPayload
    from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult
    from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
    from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesRepoQuery
    from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery
    from omnifocus_operator.models.folder import Folder
    from omnifocus_operator.models.perspective import Perspective
    from omnifocus_operator.models.project import Project
    from omnifocus_operator.models.tag import Tag
    from omnifocus_operator.models.task import Task

__all__ = ["BridgeOnlyRepository"]

# ---------------------------------------------------------------------------
# Date field mapping (query field prefix -> Task model attribute name)
# ---------------------------------------------------------------------------

_BRIDGE_FIELD_MAP: dict[str, str] = {
    "due": "inherited_due_date",
    "defer": "inherited_defer_date",
    "planned": "inherited_planned_date",
    "completed": "inherited_completion_date",
    "dropped": "inherited_drop_date",
    "added": "added",
    "modified": "modified",
}

# Project-specific field map: projects have no inherited fields (cannot inherit from folders).
# All date filters use direct fields instead of inherited fields.
_BRIDGE_PROJECT_FIELD_MAP: dict[str, str] = {
    "due": "due_date",
    "defer": "defer_date",
    "planned": "planned_date",
    "completed": "completion_date",
    "dropped": "drop_date",
    "added": "added",
    "modified": "modified",
}

# Lifecycle date fields use additive semantics: remaining tasks (None attribute)
# pass through alongside lifecycle items matching the date bounds.
_LIFECYCLE_DATE_FIELDS = {"completed", "dropped"}


def _apply_date_filters[T](
    items: list[T],
    query: object,
    field_map: dict[str, str],
) -> list[T]:
    """Filter items by date _after/_before bounds using the given field map.

    For lifecycle fields (completed, dropped), uses additive semantics:
    items with None pass through alongside date-scoped items.
    For regular fields, items with None are excluded.
    """
    for field_name, attr_name in field_map.items():
        after_val = getattr(query, f"{field_name}_after", None)
        before_val = getattr(query, f"{field_name}_before", None)
        if field_name in _LIFECYCLE_DATE_FIELDS:
            if after_val is not None:
                items = [
                    item
                    for item in items
                    if getattr(item, attr_name) is None or getattr(item, attr_name) >= after_val
                ]
            if before_val is not None:
                items = [
                    item
                    for item in items
                    if getattr(item, attr_name) is None or getattr(item, attr_name) < before_val
                ]
        else:
            if after_val is not None:
                items = [
                    item
                    for item in items
                    if getattr(item, attr_name) is not None
                    and getattr(item, attr_name) >= after_val
                ]
            if before_val is not None:
                items = [
                    item
                    for item in items
                    if getattr(item, attr_name) is not None
                    and getattr(item, attr_name) < before_val
                ]
    return items


class BridgeOnlyRepository(BridgeWriteMixin, Repository):
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
                logger.debug(
                    "BridgeOnlyRepository.get_all: cache miss/stale, refreshing via bridge"
                )
                self._cached = await self._refresh(current_mtime)
            else:
                logger.debug(
                    "BridgeOnlyRepository.get_all: cache hit, tasks=%d, projects=%d, tags=%d",
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

    async def add_task(self, payload: AddTaskRepoPayload) -> AddTaskRepoResult:
        """Create a task via bridge and invalidate cache.

        Serializes the typed payload to a camelCase dict and sends via bridge.
        """
        logger.debug("BridgeOnlyRepository.add_task: sending to bridge")
        result = await self._send_to_bridge("add_task", payload)
        self._cached = None  # Visible cache invalidation
        logger.debug("BridgeOnlyRepository.add_task: cache invalidated, id=%s", result["id"])

        return AddTaskRepoResult(id=result["id"], name=result["name"])

    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult:
        """Edit a task via bridge and invalidate cache."""
        logger.debug("BridgeOnlyRepository.edit_task: sending to bridge")
        result = await self._send_to_bridge("edit_task", payload)
        self._cached = None  # Visible cache invalidation
        logger.debug("BridgeOnlyRepository.edit_task: cache invalidated, id=%s", result.get("id"))
        return EditTaskRepoResult(id=result["id"], name=result["name"])

    async def list_tasks(self, query: ListTasksRepoQuery) -> ListRepoResult[Task]:
        """Fetch-all + Python filter for tasks (fallback path)."""
        all_entities = await self.get_all()
        items = list(all_entities.tasks)

        if query.in_inbox is not None:
            inbox_id = SYSTEM_LOCATIONS["inbox"].id
            if query.in_inbox:
                items = [t for t in items if t.project.id == inbox_id]
            else:
                items = [t for t in items if t.project.id != inbox_id]
        if query.flagged is not None:
            items = [t for t in items if t.inherited_flagged == query.flagged]
        if query.task_id_scope is not None:
            pid_set = set(query.task_id_scope)
            items = [t for t in items if t.project.id in pid_set]
        if query.tag_ids is not None:
            tid_set = set(query.tag_ids)
            items = [t for t in items if any(tag.id in tid_set for tag in t.tags)]
        if query.estimated_minutes_max is not None:
            items = [
                t
                for t in items
                if t.estimated_minutes is not None
                and t.estimated_minutes <= query.estimated_minutes_max
            ]
        avail_set = set(query.availability)
        items = [t for t in items if t.availability in avail_set]
        if query.search is not None:
            lower_search = query.search.lower()
            items = [
                t
                for t in items
                if lower_search in t.name.lower() or (t.note and lower_search in t.note.lower())
            ]

        # Date filters (all 7 dimensions)
        items = _apply_date_filters(items, query, _BRIDGE_FIELD_MAP)

        # Deterministic ordering for pagination
        items.sort(key=lambda t: t.id)

        return paginate(items, query.limit, query.offset)

    async def list_projects(self, query: ListProjectsRepoQuery) -> ListRepoResult[Project]:
        """Fetch-all + Python filter for projects (fallback path)."""
        all_entities = await self.get_all()
        items = list(all_entities.projects)

        avail_set = set(query.availability)
        items = [p for p in items if p.availability in avail_set]
        if query.folder_ids is not None:
            fid_set = set(query.folder_ids)
            items = [p for p in items if p.folder is not None and p.folder.id in fid_set]
        if query.flagged is not None:
            items = [p for p in items if p.flagged == query.flagged]
        if query.review_due_before is not None:
            items = [
                p
                for p in items
                if p.next_review_date is not None and p.next_review_date <= query.review_due_before
            ]
        if query.search is not None:
            lower_search = query.search.lower()
            items = [
                p
                for p in items
                if lower_search in p.name.lower() or (p.note and lower_search in p.note.lower())
            ]

        # Date filters (all 7 dimensions) -- uses project-specific field map
        items = _apply_date_filters(items, query, _BRIDGE_PROJECT_FIELD_MAP)

        # Deterministic ordering for pagination
        items.sort(key=lambda p: p.id)

        return paginate(items, query.limit, query.offset)

    async def list_tags(self, query: ListTagsRepoQuery) -> ListRepoResult[Tag]:
        """Fetch-all + Python filter for tags."""
        all_entities = await self.get_all()
        items = list(all_entities.tags)
        if query.availability:
            avail_set = set(query.availability)
            items = [t for t in items if t.availability in avail_set]
        if query.search is not None:
            lower_search = query.search.lower()
            items = [t for t in items if lower_search in t.name.lower()]
        return paginate(items, query.limit, query.offset)

    async def list_folders(self, query: ListFoldersRepoQuery) -> ListRepoResult[Folder]:
        """Fetch-all + Python filter for folders."""
        all_entities = await self.get_all()
        items = list(all_entities.folders)
        if query.availability:
            avail_set = set(query.availability)
            items = [f for f in items if f.availability in avail_set]
        if query.search is not None:
            lower_search = query.search.lower()
            items = [f for f in items if lower_search in f.name.lower()]
        return paginate(items, query.limit, query.offset)

    async def list_perspectives(
        self, query: ListPerspectivesRepoQuery
    ) -> ListRepoResult[Perspective]:
        """Fetch-all + Python filter for perspectives."""
        all_entities = await self.get_all()
        items = list(all_entities.perspectives)
        if query.search is not None:
            lower_search = query.search.lower()
            items = [p for p in items if lower_search in p.name.lower()]
        return paginate(items, query.limit, query.offset)

    async def get_edge_child_id(self, parent_id: str, edge: str) -> str | None:
        """Return the first or last child task ID from the cached snapshot."""
        all_entities = await self.get_all()
        inbox_id = SYSTEM_LOCATIONS["inbox"].id

        if parent_id == inbox_id:
            # Inbox: direct inbox children (project == $inbox, no parent task)
            children = [
                t for t in all_entities.tasks if t.project.id == inbox_id and t.parent.task is None
            ]
        else:
            # Regular container: tasks whose direct parent matches
            children = [
                t
                for t in all_entities.tasks
                if (t.parent.task is not None and t.parent.task.id == parent_id)
                or (t.parent.project is not None and t.parent.project.id == parent_id)
            ]

        if not children:
            return None
        # Bridge returns tasks in display order; first/last by position
        return children[0].id if edge == "first" else children[-1].id

    async def _refresh(self, current_mtime: int) -> AllEntities:
        """Fetch fresh data from the bridge and update cache state.

        On success, updates ``_cached`` and ``_last_mtime_ns``.
        On failure, cache is **not** modified (preserves old or None).
        """
        logger.debug("BridgeOnlyRepository._refresh: fetching full snapshot via bridge")
        raw: dict[str, Any] = await self._bridge.send_command("get_all")
        # Transform bridge-format -> new model shape (no-op if already new shape)
        adapt_snapshot(raw)
        result = AllEntities.model_validate(raw)
        self._last_mtime_ns = current_mtime
        logger.debug(
            "BridgeOnlyRepository._refresh: tasks=%d, projects=%d, tags=%d",
            len(result.tasks),
            len(result.projects),
            len(result.tags),
        )
        return result
