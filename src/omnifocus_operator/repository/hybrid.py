"""HybridRepository -- SQLite-based OmniFocus data reader.

Reads all 5 entity types (Task, Project, Tag, Folder, Perspective) plus
the TaskToTag join table directly from the OmniFocus SQLite cache file.
Maps rows to Pydantic models with two-axis status (urgency + availability).

Connection semantics: read-only mode (?mode=ro), fresh connection per read.
Blocking I/O wrapped via asyncio.to_thread for the async get_all() interface.
"""

from __future__ import annotations

import asyncio
import os
import pathlib
import plistlib
import re
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from pathlib import Path

    from omnifocus_operator.bridge.protocol import Bridge
    from omnifocus_operator.models.write import TaskCreateResult, TaskCreateSpec

import logging

from omnifocus_operator.models.project import Project
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.models.task import Task

logger = logging.getLogger("omnifocus_operator")

__all__ = ["HybridRepository"]

# Core Foundation epoch: Jan 1, 2001 00:00:00 UTC
_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)

# Default OmniFocus SQLite database path
_DEFAULT_DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)

# -- SQL Queries --

_TASKS_SQL = """
SELECT t.*
FROM Task t
LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
WHERE pi.task IS NULL
"""

_PROJECTS_SQL = """
SELECT t.*, pi.lastReviewDate, pi.nextReviewDate,
       pi.reviewRepetitionString, pi.nextTask, pi.folder,
       pi.effectiveStatus
FROM Task t
JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
"""

_TAGS_SQL = "SELECT * FROM Context"

_FOLDERS_SQL = "SELECT * FROM Folder"

_PERSPECTIVES_SQL = "SELECT * FROM Perspective"

_TASK_TO_TAG_SQL = "SELECT task, tag FROM TaskToTag"


# -- Timezone --


def _get_local_tz() -> ZoneInfo:
    """Get system timezone as ZoneInfo from /etc/localtime symlink (macOS)."""
    tz_path = pathlib.Path("/etc/localtime").resolve()
    tz_name = str(tz_path).split("zoneinfo/")[-1]
    return ZoneInfo(tz_name)


_LOCAL_TZ = _get_local_tz()


# -- Timestamp parsing --


def _parse_timestamp(value: float | str | None) -> str | None:
    """Parse CF epoch float or ISO 8601 string to ISO 8601 with timezone."""
    if value is None:
        return None
    # SQLite may return floats as-is or as strings depending on column affinity.
    # Try numeric conversion first for CF epoch values.
    if isinstance(value, (int, float)):
        dt = _CF_EPOCH + timedelta(seconds=value)
        return dt.isoformat()
    if isinstance(value, str):
        # Check if it's a numeric string (CF epoch stored in TEXT column)
        try:
            numeric = float(value)
            dt = _CF_EPOCH + timedelta(seconds=numeric)
            return dt.isoformat()
        except ValueError:
            pass
        # ISO 8601 string -- ensure timezone info is present
        if value.endswith("Z"):
            return value.replace("Z", "+00:00")
        if "+" not in value and "-" not in value[10:]:
            return value + "+00:00"
        return value
    msg = f"Unexpected timestamp type: {type(value)}"
    raise ValueError(msg)


def _parse_local_datetime(value: str | None) -> str | None:
    """Parse timezone-naive ISO string as local time, return UTC ISO 8601.

    OmniFocus stores dateDue, dateToStart, datePlanned as naive local-time
    strings (e.g. "2026-04-01T10:00:00.000"). This function attaches the
    system timezone (handling DST based on the date itself) and converts
    to UTC.
    """
    if value is None:
        return None
    naive = datetime.fromisoformat(value)
    local_dt = naive.replace(tzinfo=_LOCAL_TZ)
    utc_dt = local_dt.astimezone(UTC)
    return utc_dt.isoformat()


# -- Status mapping --


def _map_urgency(*, overdue: int, due_soon: int) -> str:
    """Map SQLite overdue/dueSoon columns to Urgency enum value."""
    if overdue:
        return "overdue"
    if due_soon:
        return "due_soon"
    return "none"


def _map_task_availability(*, blocked: int, date_completed: object, date_hidden: object) -> str:
    """Map SQLite columns to task Availability enum value."""
    if date_hidden is not None:
        return "dropped"
    if date_completed is not None:
        return "completed"
    if blocked:
        return "blocked"
    return "available"


def _map_project_availability(
    *, effective_status: str | None, date_completed: object, date_hidden: object
) -> str:
    """Map ProjectInfo.effectiveStatus + Task dates to Availability."""
    if date_hidden is not None:
        return "dropped"
    if effective_status == "dropped":
        return "dropped"
    if date_completed is not None:
        return "completed"
    if effective_status == "inactive":
        return "blocked"
    return "available"


def _map_tag_availability(*, allows_next_action: int, date_hidden: object) -> str:
    """Map Context columns to TagAvailability enum value."""
    if date_hidden is not None:
        return "dropped"
    if not allows_next_action:
        return "blocked"
    return "available"


def _map_folder_availability(*, date_hidden: object) -> str:
    """Map Folder.dateHidden to FolderAvailability enum value."""
    if date_hidden is not None:
        return "dropped"
    return "available"


# -- Repetition rule --


_SCHEDULE_TYPE_MAP = {
    "fixed": "regularly",
    "from-assigned": "regularly",
    "due-after-completion": "from_completion",
    "start-after-completion": "from_completion",
    "from-completion": "from_completion",
}

_ANCHOR_DATE_MAP = {
    "dateDue": "due_date",
    "dateToStart": "defer_date",
    "datePlanned": "planned_date",
}


def _build_repetition_rule(row: sqlite3.Row) -> dict[str, Any] | None:
    """Map SQLite columns to RepetitionRule dict. None if no rule."""
    rule_string = row["repetitionRuleString"]
    if not rule_string:
        return None
    schedule_type_raw = row["repetitionScheduleTypeString"]
    return {
        "rule_string": rule_string,
        "schedule_type": _SCHEDULE_TYPE_MAP.get(schedule_type_raw, schedule_type_raw),
        "anchor_date_key": _ANCHOR_DATE_MAP.get(row["repetitionAnchorDateKey"], "due_date"),
        "catch_up_automatically": bool(row["catchUpAutomatically"]),
    }


# -- Review interval --


def _parse_review_interval(raw: str | None) -> dict[str, Any]:
    """Parse '@1w' or '~2m' format into {steps, unit}."""
    if not raw:
        return {"steps": 7, "unit": "days"}
    match = re.match(r"[~@](\d+)([dwmy])", raw)
    if not match:
        return {"steps": 7, "unit": "days"}
    count = int(match.group(1))
    unit_char = match.group(2)
    unit_map = {"d": "days", "w": "weeks", "m": "months", "y": "years"}
    return {"steps": count, "unit": unit_map.get(unit_char, unit_char)}


# -- Parent reference --


def _build_parent_ref(
    row: sqlite3.Row,
    project_info_lookup: dict[str, dict[str, str]],
    task_name_lookup: dict[str, str],
) -> dict[str, str] | None:
    """Build a ParentRef dict from SQLite row data.

    Priority: parent task > containing project > None (inbox).
    """
    parent_task_id = row["parent"]
    if parent_task_id is not None:
        return {
            "type": "task",
            "id": parent_task_id,
            "name": task_name_lookup.get(parent_task_id, ""),
        }

    containing_project_pk = row["containingProjectInfo"]
    if containing_project_pk is not None:
        info = project_info_lookup.get(containing_project_pk)
        if info is not None:
            return {
                "type": "project",
                "id": info["id"],
                "name": info["name"],
            }

    return None


# -- Row mapping --


def _map_task_row(
    row: sqlite3.Row,
    tag_lookup: dict[str, list[dict[str, str]]],
    project_info_lookup: dict[str, dict[str, str]],
    task_name_lookup: dict[str, str],
) -> dict[str, Any]:
    """Map a Task SQLite row to a dict matching the Task Pydantic model."""
    task_id = row["persistentIdentifier"]
    return {
        "id": task_id,
        "name": row["name"],
        "url": f"omnifocus:///task/{task_id}",
        "added": _parse_timestamp(row["dateAdded"]),
        "modified": _parse_timestamp(row["dateModified"]),
        "note": row["plainTextNote"] or "",
        "flagged": bool(row["flagged"]),
        "effective_flagged": bool(row["effectiveFlagged"]),
        "due_date": _parse_local_datetime(row["dateDue"]),
        "defer_date": _parse_local_datetime(row["dateToStart"]),
        "effective_due_date": _parse_timestamp(row["effectiveDateDue"]),
        "effective_defer_date": _parse_timestamp(row["effectiveDateToStart"]),
        "completion_date": _parse_timestamp(row["dateCompleted"]),
        "effective_completion_date": _parse_timestamp(row["effectiveDateCompleted"]),
        "drop_date": _parse_timestamp(row["dateHidden"]),
        "effective_drop_date": _parse_timestamp(row["effectiveDateHidden"]),
        "planned_date": _parse_local_datetime(row["datePlanned"]),
        "effective_planned_date": _parse_timestamp(row["effectiveDatePlanned"]),
        "estimated_minutes": row["estimatedMinutes"],
        "has_children": (row["childrenCount"] or 0) > 0,
        "in_inbox": bool(row["inInbox"]),
        "parent": _build_parent_ref(row, project_info_lookup, task_name_lookup),
        "urgency": _map_urgency(
            overdue=row["overdue"] or 0,
            due_soon=row["dueSoon"] or 0,
        ),
        "availability": _map_task_availability(
            blocked=row["blocked"] or 0,
            date_completed=row["dateCompleted"],
            date_hidden=row["dateHidden"],
        ),
        "tags": tag_lookup.get(task_id, []),
        "repetition_rule": _build_repetition_rule(row),
    }


def _map_project_row(
    row: sqlite3.Row,
    tag_lookup: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    """Map a Task+ProjectInfo joined row to a Project Pydantic model dict."""
    task_id = row["persistentIdentifier"]
    return {
        "id": task_id,
        "name": row["name"],
        "url": f"omnifocus:///project/{task_id}",
        "added": _parse_timestamp(row["dateAdded"]),
        "modified": _parse_timestamp(row["dateModified"]),
        "note": row["plainTextNote"] or "",
        "flagged": bool(row["flagged"]),
        "effective_flagged": bool(row["effectiveFlagged"]),
        "due_date": _parse_local_datetime(row["dateDue"]),
        "defer_date": _parse_local_datetime(row["dateToStart"]),
        "effective_due_date": _parse_timestamp(row["effectiveDateDue"]),
        "effective_defer_date": _parse_timestamp(row["effectiveDateToStart"]),
        "completion_date": _parse_timestamp(row["dateCompleted"]),
        "drop_date": _parse_timestamp(row["dateHidden"]),
        "effective_drop_date": _parse_timestamp(row["effectiveDateHidden"]),
        "planned_date": _parse_local_datetime(row["datePlanned"]),
        "effective_planned_date": _parse_timestamp(row["effectiveDatePlanned"]),
        "estimated_minutes": row["estimatedMinutes"],
        "has_children": (row["childrenCount"] or 0) > 0,
        "urgency": _map_urgency(
            overdue=row["overdue"] or 0,
            due_soon=row["dueSoon"] or 0,
        ),
        "availability": _map_project_availability(
            effective_status=row["effectiveStatus"],
            date_completed=row["dateCompleted"],
            date_hidden=row["dateHidden"],
        ),
        "tags": tag_lookup.get(task_id, []),
        "repetition_rule": _build_repetition_rule(row),
        "last_review_date": _parse_timestamp(row["lastReviewDate"]),
        "next_review_date": _parse_timestamp(row["nextReviewDate"]),
        "review_interval": _parse_review_interval(row["reviewRepetitionString"]),
        "next_task": row["nextTask"],
        "folder": row["folder"],
    }


def _map_tag_row(row: sqlite3.Row) -> dict[str, Any]:
    """Map a Context SQLite row to a Tag Pydantic model dict."""
    tag_id = row["persistentIdentifier"]
    return {
        "id": tag_id,
        "name": row["name"],
        "url": f"omnifocus:///tag/{tag_id}",
        "added": _parse_timestamp(row["dateAdded"]),
        "modified": _parse_timestamp(row["dateModified"]),
        "availability": _map_tag_availability(
            allows_next_action=row["allowsNextAction"],
            date_hidden=row["dateHidden"],
        ),
        "children_are_mutually_exclusive": bool(row["childrenAreMutuallyExclusive"]),
        "parent": row["parent"],
    }


def _map_folder_row(row: sqlite3.Row) -> dict[str, Any]:
    """Map a Folder SQLite row to a Folder Pydantic model dict."""
    folder_id = row["persistentIdentifier"]
    return {
        "id": folder_id,
        "name": row["name"],
        "url": f"omnifocus:///folder/{folder_id}",
        "added": _parse_timestamp(row["dateAdded"]),
        "modified": _parse_timestamp(row["dateModified"]),
        "availability": _map_folder_availability(
            date_hidden=row["dateHidden"],
        ),
        "parent": row["parent"],
    }


def _map_perspective_row(row: sqlite3.Row) -> dict[str, Any]:
    """Map a Perspective SQLite row to a Perspective Pydantic model dict."""
    persp_id = row["persistentIdentifier"]
    value_data = row["valueData"]
    name = ""
    if value_data:
        plist = plistlib.loads(value_data)
        name = plist.get("name", "")
    return {
        "id": persp_id,
        "name": name,
    }


# -- Repository --


_FRESHNESS_TIMEOUT = 2.0
"""Seconds to wait for WAL mtime to change before returning possibly stale data."""


class HybridRepository:
    """Repository reading OmniFocus data from the SQLite cache file.

    Opens a fresh read-only connection for each get_all() call.
    Blocking SQLite I/O is wrapped in asyncio.to_thread.
    """

    def __init__(self, db_path: Path | None = None, bridge: Bridge | None = None) -> None:
        if db_path is not None:
            self._db_path = str(db_path)
        else:
            self._db_path = os.environ.get("OMNIFOCUS_SQLITE_PATH", _DEFAULT_DB_PATH)
        if bridge is None:
            msg = "HybridRepository requires a bridge"
            raise ValueError(msg)
        self._bridge: Bridge = bridge
        self._stale: bool = False
        self._last_wal_mtime_ns: int = 0

    def _mark_stale(self) -> None:
        """Mark data as stale so next get_all() waits for fresh data.

        Captures current WAL (or DB) mtime as baseline for change detection.
        """
        wal_path = self._db_path + "-wal"
        try:
            self._last_wal_mtime_ns = os.stat(wal_path).st_mtime_ns
        except FileNotFoundError:
            self._last_wal_mtime_ns = os.stat(self._db_path).st_mtime_ns
        self._stale = True

    async def add_task(
        self,
        spec: TaskCreateSpec,
        *,
        resolved_tag_ids: list[str] | None = None,
    ) -> TaskCreateResult:
        """Create a task via bridge and mark snapshot stale.

        Builds a camelCase payload from the spec, replaces tag names with
        resolved tag IDs, sends via bridge, and marks data as stale so the
        next get_all() will wait for fresh data from OmniFocus.
        """
        from omnifocus_operator.models.write import TaskCreateResult

        # Build payload: camelCase keys, exclude None fields
        payload = spec.model_dump(by_alias=True, exclude_none=True, mode="json")

        # Replace tag names with resolved tag IDs for bridge
        payload.pop("tags", None)
        if resolved_tag_ids is not None:
            payload["tagIds"] = resolved_tag_ids

        logger.debug(
            "HybridRepository.add_task: sending to bridge, payload keys=%s",
            list(payload.keys()),
        )
        result = await self._bridge.send_command("add_task", payload)
        self._mark_stale()
        logger.debug(
            "HybridRepository.add_task: bridge returned id=%s; marked stale",
            result["id"],
        )

        return TaskCreateResult(success=True, id=result["id"], name=result["name"])

    async def edit_task(self, payload: dict[str, Any]) -> dict[str, Any]:
        """Edit a task via bridge and mark snapshot stale."""
        logger.debug(
            "HybridRepository.edit_task: sending to bridge, payload keys=%s",
            list(payload.keys()),
        )
        self._mark_stale()
        result = await self._bridge.send_command("edit_task", payload)
        logger.debug(
            "HybridRepository.edit_task: bridge returned id=%s; marked stale",
            result.get("id"),
        )
        return result

    async def get_all(self) -> AllEntities:
        """Return all OmniFocus entities from the SQLite cache."""
        logger.debug("HybridRepository.get_all: stale=%s", self._stale)
        await self._ensure_fresh()
        result = await asyncio.to_thread(self._read_all)
        # Update mtime tracking after read
        self._last_wal_mtime_ns = await self._get_current_mtime_ns()
        entities = AllEntities.model_validate(result)
        logger.debug(
            "HybridRepository.get_all: tasks=%d, projects=%d, tags=%d",
            len(entities.tasks),
            len(entities.projects),
            len(entities.tags),
        )
        return entities

    async def _get_current_mtime_ns(self) -> int:
        """Get current WAL or DB file mtime in nanoseconds."""
        wal_path = self._db_path + "-wal"
        try:
            stat_result = await asyncio.to_thread(os.stat, wal_path)
            return stat_result.st_mtime_ns
        except FileNotFoundError:
            stat_result = await asyncio.to_thread(os.stat, self._db_path)
            return stat_result.st_mtime_ns

    async def _ensure_fresh(self) -> None:
        """Clear the stale flag, waiting for fresh SQLite data if needed."""
        if self._stale:
            await self._wait_for_fresh_data()
            self._stale = False

    async def _wait_for_fresh_data(self) -> None:
        """Poll WAL/DB mtime until it changes or timeout (2s).

        If the WAL file doesn't exist, falls back to the main DB file mtime.
        On timeout, returns anyway -- slightly stale data is better than error.
        """
        deadline = time.monotonic() + _FRESHNESS_TIMEOUT
        while time.monotonic() < deadline:
            current_mtime = await self._get_current_mtime_ns()
            if current_mtime != self._last_wal_mtime_ns:
                logger.debug(
                    "HybridRepository._wait_for_fresh_data: mtime changed, OmniFocus write detected"
                )
                return
            await asyncio.sleep(0.05)
        logger.debug(
            "HybridRepository._wait_for_fresh_data: timeout, proceeding with possibly stale data"
        )

    def _read_all(self) -> dict[str, Any]:
        """Synchronous read of all entities from SQLite.

        Opens a fresh read-only connection and closes it after reading.
        """
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # 1. Read tags first (needed for tag name lookup)
            tag_rows = conn.execute(_TAGS_SQL).fetchall()
            tag_name_lookup: dict[str, str] = {}
            for row in tag_rows:
                tag_name_lookup[row["persistentIdentifier"]] = row["name"]

            # 2. Build task->tags mapping from join table
            task_tag_rows = conn.execute(_TASK_TO_TAG_SQL).fetchall()
            task_tag_map: dict[str, list[dict[str, str]]] = {}
            for row in task_tag_rows:
                task_id = row["task"]
                tag_id = row["tag"]
                tag_name = tag_name_lookup.get(tag_id, "")
                if task_id not in task_tag_map:
                    task_tag_map[task_id] = []
                task_tag_map[task_id].append({"id": tag_id, "name": tag_name})

            # 3. Build project info lookup: ProjectInfo.pk -> {id, name}
            project_info_lookup: dict[str, dict[str, str]] = {}
            pi_rows = conn.execute(
                "SELECT pi.pk, pi.task, t.name FROM ProjectInfo pi "
                "JOIN Task t ON pi.task = t.persistentIdentifier"
            ).fetchall()
            for pi_row in pi_rows:
                project_info_lookup[pi_row["pk"]] = {
                    "id": pi_row["task"],
                    "name": pi_row["name"],
                }

            # 4. Build task name lookup: persistentIdentifier -> name
            task_name_rows = conn.execute("SELECT persistentIdentifier, name FROM Task").fetchall()
            task_name_lookup: dict[str, str] = {
                r["persistentIdentifier"]: r["name"] for r in task_name_rows
            }

            # 5. Read all entity types
            tasks = [
                _map_task_row(row, task_tag_map, project_info_lookup, task_name_lookup)
                for row in conn.execute(_TASKS_SQL).fetchall()
            ]
            projects = [
                _map_project_row(row, task_tag_map)
                for row in conn.execute(_PROJECTS_SQL).fetchall()
            ]
            tags = [_map_tag_row(row) for row in tag_rows]
            folders = [_map_folder_row(row) for row in conn.execute(_FOLDERS_SQL).fetchall()]
            perspectives = [
                _map_perspective_row(row) for row in conn.execute(_PERSPECTIVES_SQL).fetchall()
            ]

            return {
                "tasks": tasks,
                "projects": projects,
                "tags": tags,
                "folders": folders,
                "perspectives": perspectives,
            }
        finally:
            conn.close()

    # -- Single-entity reads --

    def _read_task(self, task_id: str) -> dict[str, Any] | None:
        """Read a single task by ID from SQLite. Returns None if not found."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                _TASKS_SQL + " AND t.persistentIdentifier = ?",
                (task_id,),
            ).fetchone()
            if row is None:
                return None

            # Build tag lookup for this task
            tag_name_lookup: dict[str, str] = {}
            for tr in conn.execute(_TAGS_SQL).fetchall():
                tag_name_lookup[tr["persistentIdentifier"]] = tr["name"]

            tag_rows = conn.execute(
                "SELECT tag FROM TaskToTag WHERE task = ?", (task_id,)
            ).fetchall()
            tag_list: list[dict[str, str]] = [
                {"id": tr["tag"], "name": tag_name_lookup.get(tr["tag"], "")} for tr in tag_rows
            ]
            task_tag_map: dict[str, list[dict[str, str]]] = {task_id: tag_list}

            # Build project_info lookup for parent resolution
            project_info_lookup: dict[str, dict[str, str]] = {}
            containing_pi = row["containingProjectInfo"]
            if containing_pi is not None:
                pi_row = conn.execute(
                    "SELECT pi.pk, pi.task, t.name FROM ProjectInfo pi "
                    "JOIN Task t ON pi.task = t.persistentIdentifier "
                    "WHERE pi.pk = ?",
                    (containing_pi,),
                ).fetchone()
                if pi_row is not None:
                    project_info_lookup[pi_row["pk"]] = {
                        "id": pi_row["task"],
                        "name": pi_row["name"],
                    }

            # Build task_name lookup for parent task resolution
            task_name_lookup: dict[str, str] = {}
            parent_task_id = row["parent"]
            if parent_task_id is not None:
                name_row = conn.execute(
                    "SELECT name FROM Task WHERE persistentIdentifier = ?",
                    (parent_task_id,),
                ).fetchone()
                if name_row is not None:
                    task_name_lookup[parent_task_id] = name_row["name"]

            return _map_task_row(row, task_tag_map, project_info_lookup, task_name_lookup)
        finally:
            conn.close()

    def _read_project(self, project_id: str) -> dict[str, Any] | None:
        """Read a single project by ID from SQLite. Returns None if not found."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                _PROJECTS_SQL + " WHERE t.persistentIdentifier = ?",
                (project_id,),
            ).fetchone()
            if row is None:
                return None

            # Build tag lookup for this project's task ID
            tag_name_lookup: dict[str, str] = {}
            for tr in conn.execute(_TAGS_SQL).fetchall():
                tag_name_lookup[tr["persistentIdentifier"]] = tr["name"]

            tag_rows = conn.execute(
                "SELECT tag FROM TaskToTag WHERE task = ?", (project_id,)
            ).fetchall()
            tag_list: list[dict[str, str]] = [
                {"id": tr["tag"], "name": tag_name_lookup.get(tr["tag"], "")} for tr in tag_rows
            ]
            task_tag_map: dict[str, list[dict[str, str]]] = {project_id: tag_list}

            return _map_project_row(row, task_tag_map)
        finally:
            conn.close()

    def _read_tag(self, tag_id: str) -> dict[str, Any] | None:
        """Read a single tag by ID from SQLite. Returns None if not found."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            row = conn.execute(
                "SELECT * FROM Context WHERE persistentIdentifier = ?",
                (tag_id,),
            ).fetchone()
            if row is None:
                return None
            return _map_tag_row(row)
        finally:
            conn.close()

    async def get_task(self, task_id: str) -> Task | None:
        """Return a single task by ID, or None if not found."""
        logger.debug("HybridRepository.get_task: stale=%s", self._stale)
        await self._ensure_fresh()
        result = await asyncio.to_thread(self._read_task, task_id)
        if result is None:
            return None
        return Task.model_validate(result)

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        logger.debug("HybridRepository.get_project: stale=%s", self._stale)
        await self._ensure_fresh()
        result = await asyncio.to_thread(self._read_project, project_id)
        if result is None:
            return None
        return Project.model_validate(result)

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
        logger.debug("HybridRepository.get_tag: stale=%s", self._stale)
        await self._ensure_fresh()
        result = await asyncio.to_thread(self._read_tag, tag_id)
        if result is None:
            return None
        return Tag.model_validate(result)
