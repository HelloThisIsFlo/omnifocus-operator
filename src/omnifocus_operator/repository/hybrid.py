"""HybridRepository -- SQLite-based OmniFocus data reader.

Reads all 5 entity types (Task, Project, Tag, Folder, Perspective) plus
the TaskToTag join table directly from the OmniFocus SQLite cache file.
Maps rows to Pydantic models with two-axis status (urgency + availability).

Connection semantics: read-only mode (?mode=ro), fresh connection per read.
Blocking I/O wrapped via asyncio.to_thread for the async get_all() interface.
"""

from __future__ import annotations

import asyncio
import functools
import os
import pathlib
import plistlib
import re
import sqlite3
import time
from collections.abc import Callable
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from zoneinfo import ZoneInfo

from omnifocus_operator.contracts.protocols import Repository
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoResult
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoResult
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult
from omnifocus_operator.repository.bridge_write_mixin import BridgeWriteMixin
from omnifocus_operator.repository.query_builder import (
    build_list_projects_sql,
    build_list_tasks_sql,
)
from omnifocus_operator.repository.rrule import derive_schedule, parse_end_condition, parse_rrule

if TYPE_CHECKING:
    from pathlib import Path

    from omnifocus_operator.contracts.protocols import Bridge
    from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoPayload
    from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoPayload
    from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
    from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery

import logging

from omnifocus_operator.models.folder import Folder
from omnifocus_operator.models.perspective import Perspective
from omnifocus_operator.models.project import Project
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.models.tag import Tag
from omnifocus_operator.models.task import Task

logger = logging.getLogger(__name__)

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
    """Map SQLite columns to structured RepetitionRule dict. None if no rule."""
    rule_string = row["repetitionRuleString"]
    if not rule_string:
        return None
    schedule_type_raw = row["repetitionScheduleTypeString"]
    catch_up = bool(row["catchUpAutomatically"])
    anchor_key = _ANCHOR_DATE_MAP.get(row["repetitionAnchorDateKey"], "due_date")
    schedule_type = _SCHEDULE_TYPE_MAP.get(schedule_type_raw, schedule_type_raw)

    frequency = parse_rrule(rule_string)
    end = parse_end_condition(rule_string)
    schedule = derive_schedule(schedule_type, catch_up)

    result: dict[str, Any] = {
        "frequency": frequency,
        "schedule": schedule,
        "based_on": anchor_key,
    }
    if end is not None:
        result["end"] = end
    return result


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


# -- Shared lookup builders --


def _build_tag_name_lookup(conn: sqlite3.Connection) -> dict[str, str]:
    """Execute _TAGS_SQL and return {tag_id: tag_name}."""
    tag_rows = conn.execute(_TAGS_SQL).fetchall()
    return {row["persistentIdentifier"]: row["name"] for row in tag_rows}


def _build_task_tag_map(
    conn: sqlite3.Connection,
    tag_name_lookup: dict[str, str],
) -> dict[str, list[dict[str, str]]]:
    """Execute _TASK_TO_TAG_SQL and return {task_id: [{id, name}]}."""
    task_tag_rows = conn.execute(_TASK_TO_TAG_SQL).fetchall()
    task_tag_map: dict[str, list[dict[str, str]]] = {}
    for row in task_tag_rows:
        task_id = row["task"]
        tag_id = row["tag"]
        tag_name = tag_name_lookup.get(tag_id, "")
        if task_id not in task_tag_map:
            task_tag_map[task_id] = []
        task_tag_map[task_id].append({"id": tag_id, "name": tag_name})
    return task_tag_map


def _build_project_info_lookup(conn: sqlite3.Connection) -> dict[str, dict[str, str]]:
    """Execute ProjectInfo JOIN query, return {pi_pk: {id, name}}."""
    pi_rows = conn.execute(
        "SELECT pi.pk, pi.task, t.name FROM ProjectInfo pi "
        "JOIN Task t ON pi.task = t.persistentIdentifier"
    ).fetchall()
    return {pi_row["pk"]: {"id": pi_row["task"], "name": pi_row["name"]} for pi_row in pi_rows}


def _build_task_name_lookup(conn: sqlite3.Connection) -> dict[str, str]:
    """Execute SELECT persistentIdentifier, name FROM Task, return {task_id: name}."""
    rows = conn.execute("SELECT persistentIdentifier, name FROM Task").fetchall()
    return {r["persistentIdentifier"]: r["name"] for r in rows}


# -- Repository --


_FRESHNESS_TIMEOUT = 2.0
"""Seconds to wait for WAL mtime to advance after a write before giving up."""


def _ensures_write_through[F: Callable[..., Any]](fn: F) -> F:
    """Decorator: capture WAL baseline, execute write, wait for SQLite confirmation.

    Expects the decorated method's ``self`` to have a ``_db_path: str`` attribute
    pointing at the OmniFocus SQLite database file.
    """

    async def _get_mtime_ns(db_path: str) -> int:
        """Get current WAL or DB file mtime in nanoseconds."""
        wal_path = db_path + "-wal"
        try:
            stat_result = await asyncio.to_thread(os.stat, wal_path)
            return stat_result.st_mtime_ns
        except FileNotFoundError:
            stat_result = await asyncio.to_thread(os.stat, db_path)
            return stat_result.st_mtime_ns

    async def _wait_for_fresh_data(db_path: str, baseline_mtime_ns: int) -> None:
        """Poll WAL/DB mtime until it advances past *baseline_mtime_ns* or timeout."""
        deadline = time.monotonic() + _FRESHNESS_TIMEOUT
        while time.monotonic() < deadline:
            current_mtime = await _get_mtime_ns(db_path)
            if current_mtime != baseline_mtime_ns:
                logger.debug("_ensures_write_through: mtime changed, OmniFocus write detected")
                return
            await asyncio.sleep(0.05)
        logger.debug("_ensures_write_through: timeout, proceeding with possibly stale data")

    @functools.wraps(fn)
    async def wrapper(self: Any, *args: Any, **kwargs: Any) -> Any:
        baseline = await _get_mtime_ns(self._db_path)
        result = await fn(self, *args, **kwargs)
        await _wait_for_fresh_data(self._db_path, baseline)
        return result

    return wrapper  # type: ignore[return-value]


class HybridRepository(BridgeWriteMixin, Repository):
    """Repository reading OmniFocus data from the SQLite cache file.

    Opens a fresh read-only connection for each get_all() call.
    Blocking SQLite I/O is wrapped in asyncio.to_thread.
    """

    def __init__(self, db_path: Path | None = None, bridge: Bridge | None = None) -> None:
        if db_path is not None:
            self._db_path = str(db_path)
        else:
            self._db_path = os.environ.get("OPERATOR_SQLITE_PATH", _DEFAULT_DB_PATH)
        if bridge is None:
            msg = "HybridRepository requires a bridge"
            raise ValueError(msg)
        self._bridge: Bridge = bridge

    @_ensures_write_through
    async def add_task(self, payload: AddTaskRepoPayload) -> AddTaskRepoResult:
        """Create a task via bridge and mark snapshot stale.

        Serializes the typed payload to a camelCase dict and sends via bridge.
        The next get_all() will wait for fresh data from OmniFocus.
        """
        logger.debug("HybridRepository.add_task: sending to bridge")
        result = await self._send_to_bridge("add_task", payload)
        logger.debug("HybridRepository.add_task: bridge returned id=%s", result["id"])

        return AddTaskRepoResult(id=result["id"], name=result["name"])

    @_ensures_write_through
    async def edit_task(self, payload: EditTaskRepoPayload) -> EditTaskRepoResult:
        """Edit a task via bridge and wait for SQLite confirmation."""
        logger.debug("HybridRepository.edit_task: sending to bridge")
        result = await self._send_to_bridge("edit_task", payload)
        logger.debug("HybridRepository.edit_task: bridge returned id=%s", result.get("id"))
        return EditTaskRepoResult(id=result["id"], name=result["name"])

    async def get_all(self) -> AllEntities:
        """Return all OmniFocus entities from the SQLite cache."""
        result = await asyncio.to_thread(self._read_all)
        entities = AllEntities.model_validate(result)
        logger.debug(
            "HybridRepository.get_all: tasks=%d, projects=%d, tags=%d",
            len(entities.tasks),
            len(entities.projects),
            len(entities.tags),
        )
        return entities

    def _read_all(self) -> dict[str, Any]:
        """Synchronous read of all entities from SQLite.

        Opens a fresh read-only connection and closes it after reading.
        """
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # 1. Build shared lookups
            tag_name_lookup = _build_tag_name_lookup(conn)
            task_tag_map = _build_task_tag_map(conn, tag_name_lookup)
            project_info_lookup = _build_project_info_lookup(conn)
            task_name_lookup = _build_task_name_lookup(conn)

            # 2. Read all entity types
            tasks = [
                _map_task_row(row, task_tag_map, project_info_lookup, task_name_lookup)
                for row in conn.execute(_TASKS_SQL).fetchall()
            ]
            projects = [
                _map_project_row(row, task_tag_map)
                for row in conn.execute(_PROJECTS_SQL).fetchall()
            ]
            tag_rows = conn.execute(_TAGS_SQL).fetchall()
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
        result = await asyncio.to_thread(self._read_task, task_id)
        if result is None:
            return None
        return Task.model_validate(result)

    async def get_project(self, project_id: str) -> Project | None:
        """Return a single project by ID, or None if not found."""
        result = await asyncio.to_thread(self._read_project, project_id)
        if result is None:
            return None
        return Project.model_validate(result)

    async def get_tag(self, tag_id: str) -> Tag | None:
        """Return a single tag by ID, or None if not found."""
        result = await asyncio.to_thread(self._read_tag, tag_id)
        if result is None:
            return None
        return Tag.model_validate(result)

    # -- List operations --

    def _list_tasks_sync(self, query: ListTasksRepoQuery) -> ListRepoResult[Task]:
        """Synchronous filtered task listing from SQLite."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # Build all 4 lookups (tag_name_lookup MUST come before task_tag_map)
            tag_name_lookup = _build_tag_name_lookup(conn)
            task_tag_map = _build_task_tag_map(conn, tag_name_lookup)
            project_info_lookup = _build_project_info_lookup(conn)
            task_name_lookup = _build_task_name_lookup(conn)

            # Build parameterized SQL
            data_q, count_q = build_list_tasks_sql(query)

            # Execute
            data_rows = conn.execute(data_q.sql, data_q.params).fetchall()
            count_row = conn.execute(count_q.sql, count_q.params).fetchone()

            # Map rows to Task models
            tasks = [
                Task.model_validate(
                    _map_task_row(row, task_tag_map, project_info_lookup, task_name_lookup)
                )
                for row in data_rows
            ]

            total = count_row[0] if count_row else 0
            offset = query.offset or 0
            has_more = (offset + len(tasks)) < total

            return ListRepoResult(items=tasks, total=total, has_more=has_more)
        finally:
            conn.close()

    async def list_tasks(self, query: ListTasksRepoQuery) -> ListRepoResult[Task]:
        """Return filtered, paginated tasks from the SQLite cache."""
        return await asyncio.to_thread(self._list_tasks_sync, query)

    def _list_projects_sync(self, query: ListProjectsRepoQuery) -> ListRepoResult[Project]:
        """Synchronous filtered project listing from SQLite."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            # Build lookups (projects use _map_project_row with 2 params: row, tag_lookup)
            tag_name_lookup = _build_tag_name_lookup(conn)
            task_tag_map = _build_task_tag_map(conn, tag_name_lookup)

            # Build parameterized SQL
            data_q, count_q = build_list_projects_sql(query)

            # Execute
            data_rows = conn.execute(data_q.sql, data_q.params).fetchall()
            count_row = conn.execute(count_q.sql, count_q.params).fetchone()

            # Map rows to Project models
            projects = [
                Project.model_validate(_map_project_row(row, task_tag_map)) for row in data_rows
            ]

            total = count_row[0] if count_row else 0
            offset = query.offset or 0
            has_more = (offset + len(projects)) < total

            return ListRepoResult(items=projects, total=total, has_more=has_more)
        finally:
            conn.close()

    async def list_projects(self, query: ListProjectsRepoQuery) -> ListRepoResult[Project]:
        """Return filtered, paginated projects from the SQLite cache."""
        return await asyncio.to_thread(self._list_projects_sync, query)

    # -- Simple list operations (fetch-all + Python filter) --

    def _list_tags_sync(self, query: ListTagsRepoQuery) -> ListRepoResult[Tag]:
        """Synchronous tag listing: fetch all, filter by availability in Python."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(_TAGS_SQL).fetchall()
            all_tags = [Tag.model_validate(_map_tag_row(row)) for row in rows]
            avail_set = set(query.availability)
            filtered = [t for t in all_tags if t.availability in avail_set]
            return ListRepoResult(items=filtered, total=len(filtered), has_more=False)
        finally:
            conn.close()

    async def list_tags(self, query: ListTagsRepoQuery) -> ListRepoResult[Tag]:
        """Return tags filtered by availability from the SQLite cache."""
        return await asyncio.to_thread(self._list_tags_sync, query)

    def _list_folders_sync(self, query: ListFoldersRepoQuery) -> ListRepoResult[Folder]:
        """Synchronous folder listing: fetch all, filter by availability in Python."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(_FOLDERS_SQL).fetchall()
            all_folders = [Folder.model_validate(_map_folder_row(row)) for row in rows]
            avail_set = set(query.availability)
            filtered = [f for f in all_folders if f.availability in avail_set]
            return ListRepoResult(items=filtered, total=len(filtered), has_more=False)
        finally:
            conn.close()

    async def list_folders(self, query: ListFoldersRepoQuery) -> ListRepoResult[Folder]:
        """Return folders filtered by availability from the SQLite cache."""
        return await asyncio.to_thread(self._list_folders_sync, query)

    def _list_perspectives_sync(self) -> ListRepoResult[Perspective]:
        """Synchronous perspective listing: fetch all, no filtering."""
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(_PERSPECTIVES_SQL).fetchall()
            perspectives = [Perspective.model_validate(_map_perspective_row(row)) for row in rows]
            return ListRepoResult(items=perspectives, total=len(perspectives), has_more=False)
        finally:
            conn.close()

    async def list_perspectives(self) -> ListRepoResult[Perspective]:
        """Return all perspectives from the SQLite cache."""
        return await asyncio.to_thread(self._list_perspectives_sync)
