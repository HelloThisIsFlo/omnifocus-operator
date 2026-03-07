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
import plistlib
import re
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from pathlib import Path

from omnifocus_operator.models.snapshot import AllEntities

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

_TASK_TO_TAG_SQL = "SELECT task, context FROM TaskToTag"


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


# -- Note extraction --


def _extract_note_text(xml_data: bytes | None) -> str:
    """Extract plain text from OmniFocus note XML.

    Notes are stored as XML: <text><p><run><lit>content</lit></run></p></text>
    Return empty string for None or empty notes.
    """
    if not xml_data:
        return ""
    text = xml_data.decode("utf-8", errors="replace")
    text = re.sub(r"<[^>]+>", "", text)
    return text.strip()


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
    "due-after-completion": "from_completion",
    "start-after-completion": "from_completion",
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


# -- Row mapping --


def _map_task_row(
    row: sqlite3.Row,
    tag_lookup: dict[str, list[dict[str, str]]],
) -> dict[str, Any]:
    """Map a Task SQLite row to a dict matching the Task Pydantic model."""
    task_id = row["persistentIdentifier"]
    return {
        "id": task_id,
        "name": row["name"],
        "url": f"omnifocus:///task/{task_id}",
        "added": _parse_timestamp(row["dateAdded"]),
        "modified": _parse_timestamp(row["dateModified"]),
        "note": _extract_note_text(row["noteXMLData"]),
        "flagged": bool(row["flagged"]),
        "effective_flagged": bool(row["effectiveFlagged"]),
        "due_date": _parse_timestamp(row["dateDue"]),
        "defer_date": _parse_timestamp(row["dateToStart"]),
        "effective_due_date": _parse_timestamp(row["effectiveDateDue"]),
        "effective_defer_date": _parse_timestamp(row["effectiveDateToStart"]),
        "completion_date": _parse_timestamp(row["dateCompleted"]),
        "effective_completion_date": _parse_timestamp(row["effectiveDateCompleted"]),
        "drop_date": _parse_timestamp(row["dateHidden"]),
        "effective_drop_date": _parse_timestamp(row["effectiveDateHidden"]),
        "planned_date": _parse_timestamp(row["datePlanned"]),
        "effective_planned_date": _parse_timestamp(row["effectiveDatePlanned"]),
        "estimated_minutes": row["estimatedMinutes"],
        "has_children": (row["childrenCount"] or 0) > 0,
        "in_inbox": bool(row["inInbox"]),
        "project": row["containingProjectInfo"],
        "parent": row["parent"],
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
        "note": _extract_note_text(row["noteXMLData"]),
        "flagged": bool(row["flagged"]),
        "effective_flagged": bool(row["effectiveFlagged"]),
        "due_date": _parse_timestamp(row["dateDue"]),
        "defer_date": _parse_timestamp(row["dateToStart"]),
        "effective_due_date": _parse_timestamp(row["effectiveDateDue"]),
        "effective_defer_date": _parse_timestamp(row["effectiveDateToStart"]),
        "completion_date": _parse_timestamp(row["dateCompleted"]),
        "drop_date": _parse_timestamp(row["dateHidden"]),
        "effective_drop_date": _parse_timestamp(row["effectiveDateHidden"]),
        "planned_date": _parse_timestamp(row["datePlanned"]),
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


class HybridRepository:
    """Repository reading OmniFocus data from the SQLite cache file.

    Opens a fresh read-only connection for each get_all() call.
    Blocking SQLite I/O is wrapped in asyncio.to_thread.
    """

    def __init__(self, db_path: Path | None = None) -> None:
        if db_path is not None:
            self._db_path = str(db_path)
        else:
            self._db_path = os.environ.get("OMNIFOCUS_SQLITE_PATH", _DEFAULT_DB_PATH)

    async def get_all(self) -> AllEntities:
        """Return all OmniFocus entities from the SQLite cache."""
        result = await asyncio.to_thread(self._read_all)
        return AllEntities.model_validate(result)

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
                tag_id = row["context"]
                tag_name = tag_name_lookup.get(tag_id, "")
                if task_id not in task_tag_map:
                    task_tag_map[task_id] = []
                task_tag_map[task_id].append({"id": tag_id, "name": tag_name})

            # 3. Read all entity types
            tasks = [
                _map_task_row(row, task_tag_map) for row in conn.execute(_TASKS_SQL).fetchall()
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
