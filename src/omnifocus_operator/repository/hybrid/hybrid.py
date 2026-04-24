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
import logging
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

from omnifocus_operator.config import SYSTEM_LOCATIONS, get_settings
from omnifocus_operator.contracts.protocols import Repository
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoResult
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoResult
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult
from omnifocus_operator.models.enums import ProjectType
from omnifocus_operator.repository.bridge_write_mixin import BridgeWriteMixin
from omnifocus_operator.repository.hybrid.query_builder import (
    TASK_ORDER_CTE,
    build_list_projects_sql,
    build_list_tasks_sql,
)
from omnifocus_operator.repository.pagination import paginate
from omnifocus_operator.repository.rrule import derive_schedule, parse_end_condition, parse_rrule

if TYPE_CHECKING:
    from pathlib import Path

    from omnifocus_operator.contracts.protocols import Bridge
    from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoPayload
    from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoPayload
    from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
    from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesRepoQuery
    from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
    from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery


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
       pi.effectiveStatus, pi.containsSingletonActions
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
        assert len(value) >= 10, f"OmniFocus timestamp unexpectedly short: {value!r}"
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


def _build_parent_and_project(
    row: sqlite3.Row,
    project_info_lookup: dict[str, dict[str, str]],
    task_name_lookup: dict[str, str],
) -> tuple[dict[str, Any], dict[str, str]]:
    """Build tagged ParentRef dict and ProjectRef dict from SQLite row data.

    Returns (parent_dict, project_dict). Neither is ever None.
    Inbox tasks get parent={"project": {"id": "$inbox", "name": "Inbox"}}
    and project={"id": "$inbox", "name": "Inbox"}.
    """
    inbox_ref = {"id": SYSTEM_LOCATIONS["inbox"].id, "name": SYSTEM_LOCATIONS["inbox"].name}

    parent_task_id = row["parent"]
    containing_pi = row["containingProjectInfo"]

    # Resolve project (containing project at any depth)
    if containing_pi is not None:
        info = project_info_lookup.get(containing_pi)
        project_ref = {"id": info["id"], "name": info["name"]} if info else inbox_ref
    else:
        project_ref = inbox_ref

    # Detect root task in project: parent points to the project's own task row
    is_root_in_project = False
    if parent_task_id is not None and containing_pi is not None:
        info = project_info_lookup.get(containing_pi)
        if info is not None and info["id"] == parent_task_id:
            is_root_in_project = True

    # Resolve parent (immediate container)
    if parent_task_id is not None and not is_root_in_project:
        parent_ref = {
            "task": {"id": parent_task_id, "name": task_name_lookup.get(parent_task_id, "")}
        }
    elif containing_pi is not None:
        info = project_info_lookup.get(containing_pi)
        if info is not None:
            parent_ref = {"project": {"id": info["id"], "name": info["name"]}}
        else:
            parent_ref = {"project": inbox_ref}
    else:
        parent_ref = {"project": inbox_ref}

    return parent_ref, project_ref


# -- Dotted order computation --


def _compute_dotted_orders(rows: list[sqlite3.Row]) -> dict[str, str]:
    """Compute dotted order strings from sorted task rows.

    Rows MUST be pre-sorted by sort_path (CTE output order).
    Returns {task_id: dotted_order} e.g. {"abc": "1", "def": "1.1", "ghi": "2"}.

    Each project/inbox namespace starts numbering at 1.
    Siblings under the same parent get sequential 1-based ordinals.

    IMPORTANT: Rows must already exclude project-root task rows (i.e., the SQL
    query must include `WHERE pi.task IS NULL`). If project-root rows are
    included, sibling counters will be corrupted and dotted paths will be
    silently wrong. This is a caller contract, not validated here.
    """
    # Track per-parent sibling counter
    parent_counters: dict[str | None, int] = {}
    # Track each task's ordinal within its parent
    task_ordinal: dict[str, int] = {}
    # Track each task's parent for path building
    task_parent: dict[str, str | None] = {}

    for row in rows:
        task_id = row["persistentIdentifier"]
        parent_id = row["parent"]
        task_parent[task_id] = parent_id

        if parent_id not in parent_counters:
            parent_counters[parent_id] = 0
        parent_counters[parent_id] += 1
        task_ordinal[task_id] = parent_counters[parent_id]

    # Build dotted paths by walking up the parent chain
    result: dict[str, str] = {}
    for task_id in task_ordinal:
        parts: list[str] = []
        current: str | None = task_id
        while current is not None and current in task_ordinal:
            parts.append(str(task_ordinal[current]))
            current = task_parent.get(current)
        parts.reverse()
        result[task_id] = ".".join(parts)

    return result


def _build_full_dotted_orders(conn: sqlite3.Connection) -> dict[str, str]:
    """Compute dotted orders for ALL tasks using the full unfiltered CTE.

    This ensures siblings retain their original ordinals even when WHERE
    filters remove some tasks from the result set (e.g. flagged=True
    yields sparse order values like "1", "3" when the 2nd sibling is
    unflagged).
    """
    full_sql = (
        TASK_ORDER_CTE + "SELECT t.*, o.sort_path\n"
        "FROM Task t\n"
        "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
        "LEFT JOIN task_order o ON t.persistentIdentifier = o.id\n"
        "WHERE pi.task IS NULL\n"
        "ORDER BY o.sort_path, t.persistentIdentifier"
    )
    all_rows = conn.execute(full_sql).fetchall()
    return _compute_dotted_orders(all_rows)


# -- Row mapping --


def _map_task_row(
    row: sqlite3.Row,
    tag_lookup: dict[str, list[dict[str, str]]],
    project_info_lookup: dict[str, dict[str, str]],
    task_name_lookup: dict[str, str],
    attachment_presence: set[str],
    *,
    order: str | None = None,
) -> dict[str, Any]:
    """Map a Task SQLite row to a dict matching the Task Pydantic model.

    ``attachment_presence`` is the batched set of task IDs that have at least
    one attachment (CACHE-04). For single-entity reads, callers pass either an
    empty set or a scoped ``{task_id}``-style set — no per-row EXISTS probe on
    the batch path.
    """
    task_id = row["persistentIdentifier"]
    parent_ref, project_ref = _build_parent_and_project(row, project_info_lookup, task_name_lookup)
    return {
        "id": task_id,
        "name": row["name"],
        "order": order,
        "url": f"omnifocus:///task/{task_id}",
        "added": _parse_timestamp(row["dateAdded"]),
        "modified": _parse_timestamp(row["dateModified"]),
        "note": row["plainTextNote"] or "",
        "flagged": bool(row["flagged"]),
        "inherited_flagged": bool(row["effectiveFlagged"]),
        "due_date": _parse_local_datetime(row["dateDue"]),
        "defer_date": _parse_local_datetime(row["dateToStart"]),
        "inherited_due_date": _parse_timestamp(row["effectiveDateDue"]),
        "inherited_defer_date": _parse_timestamp(row["effectiveDateToStart"]),
        "completion_date": _parse_timestamp(row["dateCompleted"]),
        "inherited_completion_date": _parse_timestamp(row["effectiveDateCompleted"]),
        "drop_date": _parse_timestamp(row["dateHidden"]),
        "inherited_drop_date": _parse_timestamp(row["effectiveDateHidden"]),
        "planned_date": _parse_local_datetime(row["datePlanned"]),
        "inherited_planned_date": _parse_timestamp(row["effectiveDatePlanned"]),
        "estimated_minutes": row["estimatedMinutes"],
        "has_children": (row["childrenCount"] or 0) > 0,
        # Phase 56-02: CACHE-01/02/04 reads from Task/Attachment.
        "has_note": bool(row["plainTextNote"]),
        "has_repetition": bool(row["repetitionRuleString"]),
        "has_attachments": task_id in attachment_presence,
        "completes_with_children": bool(row["completeWhenChildrenComplete"]),
        "type": "sequential" if row["sequential"] else "parallel",
        "parent": parent_ref,
        "project": project_ref,
        "urgency": _map_urgency(
            overdue=row["overdue"] or 0,
            due_soon=row["dueSoon"] or 0,
        ),
        "availability": _map_task_availability(
            blocked=row["blocked"] or 0,
            date_completed=row["effectiveDateCompleted"],
            date_hidden=row["effectiveDateHidden"],
        ),
        "tags": tag_lookup.get(task_id, []),
        "repetition_rule": _build_repetition_rule(row),
    }


def _map_project_row(
    row: sqlite3.Row,
    tag_lookup: dict[str, list[dict[str, str]]],
    folder_name_lookup: dict[str, str],
    task_name_lookup: dict[str, str],
    attachment_presence: set[str],
) -> dict[str, Any]:
    """Map a Task+ProjectInfo joined row to a Project Pydantic model dict.

    ``attachment_presence`` mirrors the ``_map_task_row`` parameter: batched
    presence set for ``has_attachments``. Projects are Task rows too, so the
    same set covers them.

    Project ``type`` obeys HIER-05: ``containsSingletonActions`` takes
    precedence over ``sequential``.
    """
    task_id = row["persistentIdentifier"]
    project_type = ProjectType.from_flags(
        sequential=bool(row["sequential"]),
        contains_singleton_actions=bool(row["containsSingletonActions"]),
    )
    return {
        "id": task_id,
        "name": row["name"],
        "url": f"omnifocus:///project/{task_id}",
        "added": _parse_timestamp(row["dateAdded"]),
        "modified": _parse_timestamp(row["dateModified"]),
        "note": row["plainTextNote"] or "",
        "flagged": bool(row["flagged"]),
        "due_date": _parse_local_datetime(row["dateDue"]),
        "defer_date": _parse_local_datetime(row["dateToStart"]),
        "completion_date": _parse_timestamp(row["dateCompleted"]),
        "drop_date": _parse_timestamp(row["dateHidden"]),
        "planned_date": _parse_local_datetime(row["datePlanned"]),
        "estimated_minutes": row["estimatedMinutes"],
        "has_children": (row["childrenCount"] or 0) > 0,
        # Phase 56-02: CACHE-01/02/03/04 reads on projects.
        "has_note": bool(row["plainTextNote"]),
        "has_repetition": bool(row["repetitionRuleString"]),
        "has_attachments": task_id in attachment_presence,
        "completes_with_children": bool(row["completeWhenChildrenComplete"]),
        "type": project_type,
        "urgency": _map_urgency(
            overdue=row["overdue"] or 0,
            due_soon=row["dueSoon"] or 0,
        ),
        "availability": _map_project_availability(
            effective_status=row["effectiveStatus"],
            date_completed=row["effectiveDateCompleted"],
            date_hidden=row["effectiveDateHidden"],
        ),
        "tags": tag_lookup.get(task_id, []),
        "repetition_rule": _build_repetition_rule(row),
        "last_review_date": _parse_timestamp(row["lastReviewDate"]),
        "next_review_date": _parse_timestamp(row["nextReviewDate"]),
        "review_interval": _parse_review_interval(row["reviewRepetitionString"]),
        "next_task": (
            {"id": row["nextTask"], "name": task_name_lookup.get(row["nextTask"], "")}
            if row["nextTask"] is not None and row["nextTask"] != task_id
            else None
        ),
        "folder": (
            {"id": row["folder"], "name": folder_name_lookup.get(row["folder"], "")}
            if row["folder"] is not None
            else None
        ),
    }


def _map_tag_row(row: sqlite3.Row, tag_name_lookup: dict[str, str]) -> dict[str, Any]:
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
        "parent": (
            {"id": row["parent"], "name": tag_name_lookup.get(row["parent"], "")}
            if row["parent"] is not None
            else None
        ),
    }


def _map_folder_row(row: sqlite3.Row, folder_name_lookup: dict[str, str]) -> dict[str, Any]:
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
        "parent": (
            {"id": row["parent"], "name": folder_name_lookup.get(row["parent"], "")}
            if row["parent"] is not None
            else None
        ),
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


def _build_folder_name_lookup(conn: sqlite3.Connection) -> dict[str, str]:
    """Execute _FOLDERS_SQL and return {folder_id: folder_name}."""
    rows = conn.execute(_FOLDERS_SQL).fetchall()
    return {row["persistentIdentifier"]: row["name"] for row in rows}


def _build_attachment_presence_set(conn: sqlite3.Connection) -> set[str]:
    """Load the set of task/project IDs that have at least one attachment.

    Single batched query (CACHE-04): one ``SELECT task FROM Attachment`` feeds
    a Python ``set[str]`` for O(1) per-row ``has_attachments`` emission during
    snapshot assembly. No per-row ``EXISTS`` probes on the batch path.

    Attachment rows may have a non-null ``task`` column pointing at a task's
    ``persistentIdentifier`` (projects are also Task rows in OF's schema, so
    this set covers both tasks and projects uniformly).
    """
    rows = conn.execute("SELECT task FROM Attachment").fetchall()
    return {row["task"] for row in rows if row["task"] is not None}


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
            self._db_path = get_settings().sqlite_path or _DEFAULT_DB_PATH
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
            folder_name_lookup = _build_folder_name_lookup(conn)
            # CACHE-04: single batched query feeds the per-row presence check
            # for both tasks and projects (projects are Task rows too).
            attachment_presence = _build_attachment_presence_set(conn)

            # 2. Read all entity types (tasks with CTE ordering)
            ordered_tasks_sql = (
                TASK_ORDER_CTE + "SELECT t.*, o.sort_path\n"
                "FROM Task t\n"
                "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
                "LEFT JOIN task_order o ON t.persistentIdentifier = o.id\n"
                "WHERE pi.task IS NULL\n"
                "ORDER BY o.sort_path, t.persistentIdentifier"
            )
            task_rows = conn.execute(ordered_tasks_sql).fetchall()
            dotted_orders = _compute_dotted_orders(task_rows)
            tasks = [
                _map_task_row(
                    row,
                    task_tag_map,
                    project_info_lookup,
                    task_name_lookup,
                    attachment_presence,
                    order=dotted_orders.get(row["persistentIdentifier"]),
                )
                for row in task_rows
            ]
            projects = [
                _map_project_row(
                    row,
                    task_tag_map,
                    folder_name_lookup,
                    task_name_lookup,
                    attachment_presence,
                )
                for row in conn.execute(_PROJECTS_SQL).fetchall()
            ]
            tag_rows = conn.execute(_TAGS_SQL).fetchall()
            tags = [_map_tag_row(row, tag_name_lookup) for row in tag_rows]
            folders = [
                _map_folder_row(row, folder_name_lookup)
                for row in conn.execute(_FOLDERS_SQL).fetchall()
            ]
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

            # Compute dotted order for this task via scoped CTE
            order = self._compute_task_order(conn, row)
            # Single-entity attachment lookup: scoped EXISTS probe (O(log n) on
            # the indexed Attachment_task FK). Only the batch path uses the
            # batched presence-set helper (CACHE-04).
            has_attachment_row = conn.execute(
                "SELECT 1 FROM Attachment WHERE task = ? LIMIT 1", (task_id,)
            ).fetchone()
            attachment_presence: set[str] = {task_id} if has_attachment_row else set()
            return _map_task_row(
                row,
                task_tag_map,
                project_info_lookup,
                task_name_lookup,
                attachment_presence,
                order=order,
            )
        finally:
            conn.close()

    def _compute_task_order(self, conn: sqlite3.Connection, row: sqlite3.Row) -> str | None:
        """Compute the dotted order string for a single task.

        Runs the CTE scoped to the task's project or inbox namespace,
        then uses _compute_dotted_orders to find this task's position.
        """
        containing_pi = row["containingProjectInfo"]
        task_id = row["persistentIdentifier"]

        if containing_pi is not None:
            # Project-based task: run CTE for all tasks in this project
            scoped_sql = (
                TASK_ORDER_CTE + "SELECT t.*, o.sort_path\n"
                "FROM Task t\n"
                "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
                "LEFT JOIN task_order o ON t.persistentIdentifier = o.id\n"
                "WHERE pi.task IS NULL\n"
                "  AND t.containingProjectInfo = ?\n"
                "ORDER BY o.sort_path, t.persistentIdentifier"
            )
            sibling_rows = conn.execute(scoped_sql, (containing_pi,)).fetchall()
            if not sibling_rows:
                logger.warning(
                    "_compute_task_order: no rows for containingProjectInfo=%s (stale reference?)",
                    containing_pi,
                )
                return None
        else:
            # Inbox task: run CTE for all inbox tasks (no containingProjectInfo)
            scoped_sql = (
                TASK_ORDER_CTE + "SELECT t.*, o.sort_path\n"
                "FROM Task t\n"
                "LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task\n"
                "LEFT JOIN task_order o ON t.persistentIdentifier = o.id\n"
                "WHERE pi.task IS NULL\n"
                "  AND t.containingProjectInfo IS NULL\n"
                "ORDER BY o.sort_path, t.persistentIdentifier"
            )
            sibling_rows = conn.execute(scoped_sql).fetchall()

        dotted_orders = _compute_dotted_orders(sibling_rows)
        return dotted_orders.get(task_id)

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

            # Build folder name lookup (targeted: just this project's folder)
            folder_name_lookup: dict[str, str] = {}
            folder_id = row["folder"]
            if folder_id is not None:
                folder_row = conn.execute(
                    "SELECT name FROM Folder WHERE persistentIdentifier = ?", (folder_id,)
                ).fetchone()
                if folder_row is not None:
                    folder_name_lookup[folder_id] = folder_row["name"]

            # Build task name lookup (targeted: just this project's next_task)
            task_name_lookup: dict[str, str] = {}
            next_task_id = row["nextTask"]
            if next_task_id is not None:
                nt_row = conn.execute(
                    "SELECT name FROM Task WHERE persistentIdentifier = ?", (next_task_id,)
                ).fetchone()
                if nt_row is not None:
                    task_name_lookup[next_task_id] = nt_row["name"]

            # Single-entity attachment lookup: scoped EXISTS probe.
            has_attachment_row = conn.execute(
                "SELECT 1 FROM Attachment WHERE task = ? LIMIT 1", (project_id,)
            ).fetchone()
            attachment_presence: set[str] = {project_id} if has_attachment_row else set()
            return _map_project_row(
                row, task_tag_map, folder_name_lookup, task_name_lookup, attachment_presence
            )
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

            # Build targeted tag name lookup for parent resolution
            tag_name_lookup: dict[str, str] = {}
            parent_id = row["parent"]
            if parent_id is not None:
                parent_row = conn.execute(
                    "SELECT name FROM Context WHERE persistentIdentifier = ?", (parent_id,)
                ).fetchone()
                if parent_row is not None:
                    tag_name_lookup[parent_id] = parent_row["name"]

            return _map_tag_row(row, tag_name_lookup)
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
            attachment_presence = _build_attachment_presence_set(conn)

            # Build parameterized SQL
            data_q, count_q = build_list_tasks_sql(query)

            # Execute
            data_rows = conn.execute(data_q.sql, data_q.params).fetchall()
            count_row = conn.execute(count_q.sql, count_q.params).fetchone()

            # Compute dotted orders from FULL unfiltered CTE (not just filtered rows)
            # so siblings retain their original ordinals even when filters remove some
            dotted_orders = _build_full_dotted_orders(conn)

            # Map rows to Task models
            tasks = [
                Task.model_validate(
                    _map_task_row(
                        row,
                        task_tag_map,
                        project_info_lookup,
                        task_name_lookup,
                        attachment_presence,
                        order=dotted_orders.get(row["persistentIdentifier"]),
                    )
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
            # Build lookups
            tag_name_lookup = _build_tag_name_lookup(conn)
            task_tag_map = _build_task_tag_map(conn, tag_name_lookup)
            folder_name_lookup = _build_folder_name_lookup(conn)
            task_name_lookup = _build_task_name_lookup(conn)
            attachment_presence = _build_attachment_presence_set(conn)

            # Build parameterized SQL
            data_q, count_q = build_list_projects_sql(query)

            # Execute
            data_rows = conn.execute(data_q.sql, data_q.params).fetchall()
            count_row = conn.execute(count_q.sql, count_q.params).fetchone()

            # Map rows to Project models
            projects = [
                Project.model_validate(
                    _map_project_row(
                        row,
                        task_tag_map,
                        folder_name_lookup,
                        task_name_lookup,
                        attachment_presence,
                    )
                )
                for row in data_rows
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
            tag_name_lookup = _build_tag_name_lookup(conn)
            rows = conn.execute(_TAGS_SQL).fetchall()
            all_tags = [Tag.model_validate(_map_tag_row(row, tag_name_lookup)) for row in rows]
            avail_set = set(query.availability)
            filtered = [t for t in all_tags if t.availability in avail_set]
            if query.search is not None:
                lower_search = query.search.lower()
                filtered = [t for t in filtered if lower_search in t.name.lower()]
            return paginate(filtered, query.limit, query.offset)
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
            folder_name_lookup = _build_folder_name_lookup(conn)
            rows = conn.execute(_FOLDERS_SQL).fetchall()
            all_folders = [
                Folder.model_validate(_map_folder_row(row, folder_name_lookup)) for row in rows
            ]
            avail_set = set(query.availability)
            filtered = [f for f in all_folders if f.availability in avail_set]
            if query.search is not None:
                lower_search = query.search.lower()
                filtered = [f for f in filtered if lower_search in f.name.lower()]
            return paginate(filtered, query.limit, query.offset)
        finally:
            conn.close()

    async def list_folders(self, query: ListFoldersRepoQuery) -> ListRepoResult[Folder]:
        """Return folders filtered by availability from the SQLite cache."""
        return await asyncio.to_thread(self._list_folders_sync, query)

    def _list_perspectives_sync(
        self, query: ListPerspectivesRepoQuery
    ) -> ListRepoResult[Perspective]:
        """Synchronous perspective listing: fetch all, filter by search in Python.

        Known gap: only returns custom perspectives. Built-in perspectives
        (Inbox, Projects, Tags, Forecast, Flagged, Review) live in the OmniJS
        runtime, not the SQLite cache. This will be resolved in v1.6 via a
        BridgePerspectiveMixin that merges bridge-sourced built-ins with
        SQLite custom perspectives.
        """
        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            rows = conn.execute(_PERSPECTIVES_SQL).fetchall()
            perspectives = [Perspective.model_validate(_map_perspective_row(row)) for row in rows]
            if query.search is not None:
                lower_search = query.search.lower()
                perspectives = [p for p in perspectives if lower_search in p.name.lower()]
            return paginate(perspectives, query.limit, query.offset)
        finally:
            conn.close()

    async def list_perspectives(
        self, query: ListPerspectivesRepoQuery
    ) -> ListRepoResult[Perspective]:
        """Return perspectives from the SQLite cache, optionally filtered by search."""
        return await asyncio.to_thread(self._list_perspectives_sync, query)

    # -- Edge child lookup (for move translation) --

    def _read_edge_child_id(self, parent_id: str, edge: str) -> str | None:
        """Read the first or last child task ID for a container from SQLite."""
        inbox_id = SYSTEM_LOCATIONS["inbox"].id
        order = "ASC" if edge == "first" else "DESC"

        conn = sqlite3.connect(f"file:{self._db_path}?mode=ro", uri=True)
        conn.row_factory = sqlite3.Row
        try:
            if parent_id == inbox_id:
                # Inbox: tasks with no parent and no ProjectInfo row
                row = conn.execute(
                    "SELECT persistentIdentifier FROM Task"
                    " WHERE parent IS NULL"
                    "   AND containingProjectInfo IS NULL"
                    "   AND NOT EXISTS"
                    " (SELECT 1 FROM ProjectInfo pi WHERE pi.task = persistentIdentifier)"
                    f" ORDER BY rank {order} LIMIT 1",
                    (),
                ).fetchone()
            else:
                row = conn.execute(
                    "SELECT persistentIdentifier FROM Task"
                    " WHERE parent = ?"
                    f" ORDER BY rank {order} LIMIT 1",
                    (parent_id,),
                ).fetchone()
            if row is None:
                return None
            return str(row["persistentIdentifier"])
        finally:
            conn.close()

    async def get_edge_child_id(self, parent_id: str, edge: str) -> str | None:
        """Return the first or last child task ID for a container."""
        return await asyncio.to_thread(self._read_edge_child_id, parent_id, edge)
