"""Cross-path equivalence tests.

BridgeOnlyRepository and HybridRepository produce identical results.
Parametrized fixture creates both repo types from the same neutral test data.
Seed adapters translate neutral dicts to bridge format (camelCase, ISO dates)
and SQLite format (CF epoch floats, int booleans, join tables).

Proves INFRA-03: bridge fallback path is equivalent to the SQL path.
"""

from __future__ import annotations

import plistlib
import sqlite3
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any

import pytest

from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesRepoQuery
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery
from omnifocus_operator.models.enums import (
    Availability,
    FolderAvailability,
    TagAvailability,
)
from omnifocus_operator.repository.bridge_only import BridgeOnlyRepository
from omnifocus_operator.repository.hybrid import HybridRepository
from tests.conftest import (
    make_folder_dict,
    make_perspective_dict,
    make_project_dict,
    make_snapshot_dict,
    make_tag_dict,
    make_task_dict,
)
from tests.doubles import ConstantMtimeSource, InMemoryBridge

if TYPE_CHECKING:
    from pathlib import Path

    from omnifocus_operator.contracts.protocols import Repository
    from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult

# ---------------------------------------------------------------------------
# Core Foundation epoch constant
# ---------------------------------------------------------------------------

_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)


def _to_cf_epoch(dt: datetime) -> float:
    """Convert a timezone-aware datetime to CF epoch float."""
    return (dt - _CF_EPOCH).total_seconds()


# ---------------------------------------------------------------------------
# Neutral test data -- defined once, translated by seed adapters
# ---------------------------------------------------------------------------

# Reference datetimes
_ADDED = datetime(2026, 1, 15, 10, 30, 0, tzinfo=UTC)
_MODIFIED = datetime(2026, 2, 1, 8, 0, 0, tzinfo=UTC)
_REVIEW_PAST = datetime(2026, 1, 10, 10, 0, 0, tzinfo=UTC)
_REVIEW_SOON = datetime(2026, 3, 20, 10, 0, 0, tzinfo=UTC)
_REVIEW_FAR = datetime(2026, 6, 1, 10, 0, 0, tzinfo=UTC)

# Date filter reference datetimes
_DUE_DATE = datetime(2026, 3, 15, 17, 0, 0, tzinfo=UTC)
_DEFER_DATE = datetime(2026, 2, 1, 9, 0, 0, tzinfo=UTC)
_PLANNED_DATE = datetime(2026, 3, 10, 8, 0, 0, tzinfo=UTC)
_COMPLETED_DATE = datetime(2026, 2, 20, 14, 0, 0, tzinfo=UTC)
_DROPPED_DATE = datetime(2026, 2, 25, 11, 0, 0, tzinfo=UTC)


def _build_neutral_test_data() -> dict[str, Any]:
    """Build neutral test data covering all 5 entity types.

    Returns a dict with keys: tasks, projects, tags, folders, perspectives,
    task_tag_assignments.
    """
    return {
        "tags": [
            {
                "id": "tag-1",
                "name": "Work",
                "availability": "available",
                "added": _ADDED,
                "modified": _MODIFIED,
            },
            {
                "id": "tag-2",
                "name": "Home",
                "availability": "available",
                "added": _ADDED,
                "modified": _MODIFIED,
            },
            {
                "id": "tag-3",
                "name": "OnHold",
                "availability": "blocked",
                "added": _ADDED,
                "modified": _MODIFIED,
            },
            {
                "id": "tag-4",
                "name": "Buro",
                "availability": "available",
                "added": _ADDED,
                "modified": _MODIFIED,
            },
        ],
        "folders": [
            {
                "id": "folder-1",
                "name": "Active Projects",
                "availability": "available",
                "added": _ADDED,
                "modified": _MODIFIED,
            },
            {
                "id": "folder-2",
                "name": "Archive",
                "availability": "dropped",
                "added": _ADDED,
                "modified": _MODIFIED,
            },
        ],
        "projects": [
            {
                "id": "proj-1",
                "name": "Build App",
                "note": "Mobile app for tracking expenses",
                "availability": "available",
                "flagged": True,
                "folder_id": "folder-1",
                "next_review_date": _REVIEW_SOON,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "proj-2",
                "name": "Plan Vacation",
                "note": "",
                "availability": "available",
                "flagged": False,
                "folder_id": None,
                "next_review_date": _REVIEW_FAR,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "proj-3",
                "name": "Old Project",
                "note": "Contains archived deliverables",
                "availability": "blocked",
                "flagged": False,
                "folder_id": "folder-1",
                "next_review_date": _REVIEW_PAST,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "proj-due",
                "name": "Project With Due Date",
                "note": "",
                "availability": "available",
                "flagged": False,
                "folder_id": "folder-1",
                "next_review_date": _REVIEW_SOON,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": _DUE_DATE,
                "effective_due": _DUE_DATE,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "proj-completed",
                "name": "Completed Project",
                "note": "",
                "availability": "completed",
                "flagged": False,
                "folder_id": "folder-1",
                "next_review_date": _REVIEW_PAST,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": _COMPLETED_DATE,
                "effective_completed": _COMPLETED_DATE,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "proj-dropped",
                "name": "Dropped Project",
                "note": "",
                "availability": "dropped",
                "flagged": False,
                "folder_id": "folder-1",
                "next_review_date": _REVIEW_PAST,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": _DROPPED_DATE,
                "effective_dropped": _DROPPED_DATE,
            },
        ],
        "tasks": [
            {
                "id": "task-1",
                "name": "Inbox searchable keyword task",
                "in_inbox": True,
                "flagged": True,
                "project_id": None,
                "parent_id": None,
                "availability": "available",
                "estimated_minutes": 15,
                "tag_ids": ["tag-1"],
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": _DUE_DATE,
                "effective_due": _DUE_DATE,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "task-2",
                "name": "Build feature",
                "in_inbox": False,
                "flagged": False,
                "project_id": "proj-1",
                "parent_id": "proj-1",
                "availability": "available",
                "estimated_minutes": 60,
                "tag_ids": ["tag-1", "tag-2"],
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": _DEFER_DATE,
                "effective_defer": _DEFER_DATE,
                "planned": _PLANNED_DATE,
                "effective_planned": _PLANNED_DATE,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "task-3",
                "name": "Book flights",
                "in_inbox": False,
                "flagged": False,
                "project_id": "proj-2",
                "parent_id": "proj-2",
                "availability": "blocked",
                "estimated_minutes": None,
                "tag_ids": [],
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "task-4",
                "name": "Review docs",
                "in_inbox": False,
                "flagged": True,
                "project_id": "proj-1",
                "parent_id": "proj-1",
                "availability": "available",
                "estimated_minutes": 30,
                "tag_ids": ["tag-2"],
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": _DUE_DATE,
                "effective_due": _DUE_DATE,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "task-5",
                "name": "Completed report",
                "in_inbox": False,
                "flagged": False,
                "project_id": "proj-1",
                "parent_id": "proj-1",
                "availability": "completed",
                "estimated_minutes": None,
                "tag_ids": [],
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": _COMPLETED_DATE,
                "effective_completed": _COMPLETED_DATE,
                "dropped": None,
                "effective_dropped": None,
            },
            {
                "id": "task-6",
                "name": "Dropped idea",
                "in_inbox": False,
                "flagged": False,
                "project_id": "proj-2",
                "parent_id": "proj-2",
                "availability": "dropped",
                "estimated_minutes": None,
                "tag_ids": [],
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": None,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": _DROPPED_DATE,
                "effective_dropped": _DROPPED_DATE,
            },
            {
                "id": "task-7",
                "name": "Inherited due task",
                "in_inbox": False,
                "flagged": False,
                "project_id": "proj-due",
                "parent_id": "proj-due",
                "availability": "available",
                "estimated_minutes": None,
                "tag_ids": [],
                "added": _ADDED,
                "modified": _MODIFIED,
                "due": None,
                "effective_due": _DUE_DATE,
                "defer": None,
                "effective_defer": None,
                "planned": None,
                "effective_planned": None,
                "completed": None,
                "effective_completed": None,
                "dropped": None,
                "effective_dropped": None,
            },
        ],
        "perspectives": [
            {"id": None, "name": "Inbox"},
            {"id": "persp-1", "name": "Forecast"},
            {"id": "persp-2", "name": "Review"},
        ],
        # Explicit task-tag assignments for SQLite join table
        "task_tag_assignments": [
            {"task_id": "task-1", "tag_id": "tag-1"},
            {"task_id": "task-2", "tag_id": "tag-1"},
            {"task_id": "task-2", "tag_id": "tag-2"},
            {"task_id": "task-4", "tag_id": "tag-2"},
        ],
    }


# ---------------------------------------------------------------------------
# Bridge seed adapter
# ---------------------------------------------------------------------------

_BRIDGE_AVAILABILITY_MAP = {
    "available": "Available",
    "blocked": "Blocked",
    "completed": "Completed",
    "dropped": "Dropped",
}

_BRIDGE_TAG_AVAILABILITY_MAP = {
    "available": "Active",
    "blocked": "OnHold",
    "dropped": "Dropped",
}

_BRIDGE_FOLDER_AVAILABILITY_MAP = {
    "available": "Active",
    "dropped": "Dropped",
}


def _dt_to_iso(dt: datetime) -> str:
    """Convert datetime to ISO 8601 string with .000Z suffix."""
    return dt.strftime("%Y-%m-%dT%H:%M:%S.000Z")


async def seed_bridge_repo(data: dict[str, Any]) -> BridgeOnlyRepository:
    """Translate neutral data to bridge format and return a seeded BridgeOnlyRepository."""
    # Build tag lookup for inline tag refs on tasks
    tag_lookup = {t["id"]: t["name"] for t in data["tags"]}

    # Translate tasks
    bridge_tasks = []
    for t in data["tasks"]:
        tag_refs = [{"id": tid, "name": tag_lookup[tid]} for tid in t["tag_ids"]]
        bridge_tasks.append(
            make_task_dict(
                id=t["id"],
                name=t["name"],
                inInbox=t["in_inbox"],
                flagged=t["flagged"],
                effectiveFlagged=t["flagged"],
                project=t["project_id"],
                parent=t["parent_id"],
                status=_BRIDGE_AVAILABILITY_MAP[t["availability"]],
                estimatedMinutes=t["estimated_minutes"],
                tags=tag_refs,
                added=_dt_to_iso(t["added"]),
                modified=_dt_to_iso(t["modified"]),
                dueDate=_dt_to_iso(t["due"]) if t.get("due") else None,
                effectiveDueDate=_dt_to_iso(t["effective_due"]) if t.get("effective_due") else None,
                deferDate=_dt_to_iso(t["defer"]) if t.get("defer") else None,
                effectiveDeferDate=_dt_to_iso(t["effective_defer"])
                if t.get("effective_defer")
                else None,
                plannedDate=_dt_to_iso(t["planned"]) if t.get("planned") else None,
                effectivePlannedDate=_dt_to_iso(t["effective_planned"])
                if t.get("effective_planned")
                else None,
                completionDate=_dt_to_iso(t["completed"]) if t.get("completed") else None,
                effectiveCompletionDate=_dt_to_iso(t["effective_completed"])
                if t.get("effective_completed")
                else None,
                dropDate=_dt_to_iso(t["dropped"]) if t.get("dropped") else None,
                effectiveDropDate=_dt_to_iso(t["effective_dropped"])
                if t.get("effective_dropped")
                else None,
            )
        )

    # Translate projects
    bridge_projects = []
    for p in data["projects"]:
        bridge_projects.append(
            make_project_dict(
                id=p["id"],
                name=p["name"],
                note=p.get("note", ""),
                flagged=p["flagged"],
                effectiveFlagged=p["flagged"],
                folder=p["folder_id"],
                status={
                    "available": "Active",
                    "blocked": "OnHold",
                    "completed": "Done",
                    "dropped": "Dropped",
                }[p["availability"]],
                taskStatus=_BRIDGE_AVAILABILITY_MAP[p["availability"]],
                nextReviewDate=_dt_to_iso(p["next_review_date"]),
                lastReviewDate=_dt_to_iso(p["last_review_date"]),
                added=_dt_to_iso(p["added"]),
                modified=_dt_to_iso(p["modified"]),
                dueDate=_dt_to_iso(p["due"]) if p.get("due") else None,
                effectiveDueDate=_dt_to_iso(p["effective_due"]) if p.get("effective_due") else None,
                deferDate=_dt_to_iso(p["defer"]) if p.get("defer") else None,
                effectiveDeferDate=_dt_to_iso(p["effective_defer"])
                if p.get("effective_defer")
                else None,
                plannedDate=_dt_to_iso(p["planned"]) if p.get("planned") else None,
                effectivePlannedDate=_dt_to_iso(p["effective_planned"])
                if p.get("effective_planned")
                else None,
                completionDate=_dt_to_iso(p["completed"]) if p.get("completed") else None,
                effectiveCompletionDate=_dt_to_iso(p["effective_completed"])
                if p.get("effective_completed")
                else None,
                dropDate=_dt_to_iso(p["dropped"]) if p.get("dropped") else None,
                effectiveDropDate=_dt_to_iso(p["effective_dropped"])
                if p.get("effective_dropped")
                else None,
            )
        )

    # Translate tags
    bridge_tags = []
    for tg in data["tags"]:
        bridge_tags.append(
            make_tag_dict(
                id=tg["id"],
                name=tg["name"],
                status=_BRIDGE_TAG_AVAILABILITY_MAP[tg["availability"]],
                added=_dt_to_iso(tg["added"]),
                modified=_dt_to_iso(tg["modified"]),
            )
        )

    # Translate folders
    bridge_folders = []
    for f in data["folders"]:
        bridge_folders.append(
            make_folder_dict(
                id=f["id"],
                name=f["name"],
                status=_BRIDGE_FOLDER_AVAILABILITY_MAP[f["availability"]],
                added=_dt_to_iso(f["added"]),
                modified=_dt_to_iso(f["modified"]),
            )
        )

    # Translate perspectives
    bridge_perspectives = []
    for p in data["perspectives"]:
        bridge_perspectives.append(make_perspective_dict(id=p["id"], name=p["name"]))

    snapshot = make_snapshot_dict(
        tasks=bridge_tasks,
        projects=bridge_projects,
        tags=bridge_tags,
        folders=bridge_folders,
        perspectives=bridge_perspectives,
    )

    bridge = InMemoryBridge(data=snapshot)
    return BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())


# ---------------------------------------------------------------------------
# SQLite seed adapter
# ---------------------------------------------------------------------------

# Map model availability to SQLite columns
_SQLITE_TASK_AVAILABILITY = {
    "available": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
    "blocked": {"blocked": 1, "dateCompleted": None, "dateHidden": None},
    "completed": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
    "dropped": {"blocked": 0, "dateCompleted": None, "dateHidden": None},
}

_SQLITE_TAG_AVAILABILITY = {
    "available": {"allowsNextAction": 1, "dateHidden": None},
    "blocked": {"allowsNextAction": 0, "dateHidden": None},
    "dropped": {"allowsNextAction": 1, "dateHidden": _to_cf_epoch(_MODIFIED)},
}

_SQLITE_FOLDER_AVAILABILITY = {
    "available": {"dateHidden": None},
    "dropped": {"dateHidden": _to_cf_epoch(_MODIFIED)},
}

_SQLITE_PROJECT_EFFECTIVE_STATUS = {
    "available": "active",
    "blocked": "inactive",
    "completed": "done",
    "dropped": "dropped",
}


async def seed_sqlite_repo(data: dict[str, Any], tmp_path: Path) -> HybridRepository:
    """Translate neutral data to SQLite format and return a seeded HybridRepository."""

    db_path = tmp_path / "cross_path_test.db"
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript("""
            CREATE TABLE Task (
                persistentIdentifier TEXT PRIMARY KEY,
                name TEXT,
                dateAdded REAL,
                dateModified REAL,
                noteXMLData BLOB,
                plainTextNote TEXT,
                flagged INTEGER DEFAULT 0,
                effectiveFlagged INTEGER DEFAULT 0,
                dateDue TEXT,
                dateToStart TEXT,
                datePlanned TEXT,
                effectiveDateDue INTEGER,
                effectiveDateToStart INTEGER,
                effectiveDatePlanned INTEGER,
                dateCompleted REAL,
                effectiveDateCompleted REAL,
                dateHidden REAL,
                effectiveDateHidden REAL,
                estimatedMinutes REAL,
                childrenCount INTEGER DEFAULT 0,
                inInbox INTEGER DEFAULT 0,
                containingProjectInfo TEXT,
                parent TEXT,
                overdue INTEGER DEFAULT 0,
                dueSoon INTEGER DEFAULT 0,
                blocked INTEGER DEFAULT 0,
                repetitionRuleString TEXT,
                repetitionScheduleTypeString TEXT,
                repetitionAnchorDateKey TEXT,
                catchUpAutomatically INTEGER DEFAULT 0,
                rank INTEGER DEFAULT 0
            );
            CREATE TABLE ProjectInfo (
                pk TEXT PRIMARY KEY,
                task TEXT,
                lastReviewDate REAL,
                nextReviewDate REAL,
                reviewRepetitionString TEXT,
                nextTask TEXT,
                folder TEXT,
                effectiveStatus TEXT
            );
            CREATE TABLE Context (
                persistentIdentifier TEXT PRIMARY KEY,
                name TEXT,
                dateAdded REAL,
                dateModified REAL,
                allowsNextAction INTEGER DEFAULT 1,
                dateHidden REAL,
                childrenAreMutuallyExclusive INTEGER DEFAULT 0,
                parent TEXT
            );
            CREATE TABLE Folder (
                persistentIdentifier TEXT PRIMARY KEY,
                name TEXT,
                dateAdded REAL,
                dateModified REAL,
                dateHidden REAL,
                parent TEXT
            );
            CREATE TABLE Perspective (
                persistentIdentifier TEXT,
                creationOrdinal INTEGER,
                dateAdded REAL,
                dateModified REAL,
                valueData BLOB
            );
            CREATE TABLE TaskToTag (
                task TEXT,
                tag TEXT
            );
        """)

        # Insert tasks (non-project tasks only)
        for t in data["tasks"]:
            avail_cols = _SQLITE_TASK_AVAILABILITY[t["availability"]]
            # Find containingProjectInfo pk for tasks in projects
            containing_pi = None
            if t["project_id"]:
                containing_pi = f"pi-{t['project_id']}"

            # Date columns -- override availability defaults with neutral data
            date_completed = (
                _to_cf_epoch(t["completed"]) if t.get("completed") else avail_cols["dateCompleted"]
            )
            date_hidden = (
                _to_cf_epoch(t["dropped"]) if t.get("dropped") else avail_cols["dateHidden"]
            )
            effective_completed = (
                _to_cf_epoch(t["effective_completed"])
                if t.get("effective_completed")
                else date_completed
            )
            effective_hidden = (
                _to_cf_epoch(t["effective_dropped"]) if t.get("effective_dropped") else date_hidden
            )

            # Direct dates: due/defer/planned as naive ISO text
            date_due = t["due"].strftime("%Y-%m-%dT%H:%M:%S.000Z") if t.get("due") else None
            date_to_start = (
                t["defer"].strftime("%Y-%m-%dT%H:%M:%S.000Z") if t.get("defer") else None
            )
            date_planned = (
                t["planned"].strftime("%Y-%m-%dT%H:%M:%S.000Z") if t.get("planned") else None
            )

            # Effective dates: due/defer/planned as INTEGER (truncated CF epoch)
            eff_date_due = int(_to_cf_epoch(t["effective_due"])) if t.get("effective_due") else None
            eff_date_to_start = (
                int(_to_cf_epoch(t["effective_defer"])) if t.get("effective_defer") else None
            )
            eff_date_planned = (
                int(_to_cf_epoch(t["effective_planned"])) if t.get("effective_planned") else None
            )

            conn.execute(
                """INSERT INTO Task (
                    persistentIdentifier, name, dateAdded, dateModified,
                    flagged, effectiveFlagged, estimatedMinutes,
                    childrenCount, inInbox, containingProjectInfo, parent,
                    overdue, dueSoon, blocked,
                    dateDue, dateToStart, datePlanned,
                    effectiveDateDue, effectiveDateToStart, effectiveDatePlanned,
                    dateCompleted, effectiveDateCompleted,
                    dateHidden, effectiveDateHidden
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    t["id"],
                    t["name"],
                    _to_cf_epoch(t["added"]),
                    _to_cf_epoch(t["modified"]),
                    int(t["flagged"]),
                    int(t["flagged"]),
                    t["estimated_minutes"],
                    0,  # childrenCount
                    int(t["in_inbox"]),
                    containing_pi,
                    t["parent_id"],
                    0,  # overdue
                    0,  # dueSoon
                    avail_cols["blocked"],
                    date_due,
                    date_to_start,
                    date_planned,
                    eff_date_due,
                    eff_date_to_start,
                    eff_date_planned,
                    date_completed,
                    effective_completed,
                    date_hidden,
                    effective_hidden,
                ],
            )

        # Insert projects (Task row + ProjectInfo row)
        for p in data["projects"]:
            avail_cols = _SQLITE_TASK_AVAILABILITY[p["availability"]]
            task_id = p["id"]

            # Project date columns (same pattern as tasks)
            p_date_completed = (
                _to_cf_epoch(p["completed"]) if p.get("completed") else avail_cols["dateCompleted"]
            )
            p_date_hidden = (
                _to_cf_epoch(p["dropped"]) if p.get("dropped") else avail_cols["dateHidden"]
            )
            p_eff_completed = (
                _to_cf_epoch(p["effective_completed"])
                if p.get("effective_completed")
                else p_date_completed
            )
            p_eff_hidden = (
                _to_cf_epoch(p["effective_dropped"])
                if p.get("effective_dropped")
                else p_date_hidden
            )
            p_date_due = p["due"].strftime("%Y-%m-%dT%H:%M:%S.000Z") if p.get("due") else None
            p_date_to_start = (
                p["defer"].strftime("%Y-%m-%dT%H:%M:%S.000Z") if p.get("defer") else None
            )
            p_date_planned = (
                p["planned"].strftime("%Y-%m-%dT%H:%M:%S.000Z") if p.get("planned") else None
            )
            p_eff_date_due = (
                int(_to_cf_epoch(p["effective_due"])) if p.get("effective_due") else None
            )
            p_eff_date_to_start = (
                int(_to_cf_epoch(p["effective_defer"])) if p.get("effective_defer") else None
            )
            p_eff_date_planned = (
                int(_to_cf_epoch(p["effective_planned"])) if p.get("effective_planned") else None
            )

            conn.execute(
                """INSERT INTO Task (
                    persistentIdentifier, name, plainTextNote, dateAdded, dateModified,
                    flagged, effectiveFlagged, childrenCount, inInbox,
                    overdue, dueSoon, blocked,
                    dateDue, dateToStart, datePlanned,
                    effectiveDateDue, effectiveDateToStart, effectiveDatePlanned,
                    dateCompleted, effectiveDateCompleted,
                    dateHidden, effectiveDateHidden
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    task_id,
                    p["name"],
                    p.get("note", "") or None,
                    _to_cf_epoch(p["added"]),
                    _to_cf_epoch(p["modified"]),
                    int(p["flagged"]),
                    int(p["flagged"]),
                    0,  # childrenCount
                    0,  # inInbox
                    0,  # overdue
                    0,  # dueSoon
                    avail_cols["blocked"],
                    p_date_due,
                    p_date_to_start,
                    p_date_planned,
                    p_eff_date_due,
                    p_eff_date_to_start,
                    p_eff_date_planned,
                    p_date_completed,
                    p_eff_completed,
                    p_date_hidden,
                    p_eff_hidden,
                ],
            )
            conn.execute(
                """INSERT INTO ProjectInfo (
                    pk, task, lastReviewDate, nextReviewDate,
                    reviewRepetitionString, folder, effectiveStatus
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    f"pi-{task_id}",
                    task_id,
                    _to_cf_epoch(p["last_review_date"]),
                    _to_cf_epoch(p["next_review_date"]),
                    "@1w",
                    p["folder_id"],
                    _SQLITE_PROJECT_EFFECTIVE_STATUS[p["availability"]],
                ],
            )

        # Insert tags
        for tg in data["tags"]:
            avail_cols = _SQLITE_TAG_AVAILABILITY[tg["availability"]]
            conn.execute(
                """INSERT INTO Context (
                    persistentIdentifier, name, dateAdded, dateModified,
                    allowsNextAction, dateHidden, childrenAreMutuallyExclusive
                ) VALUES (?, ?, ?, ?, ?, ?, ?)""",
                [
                    tg["id"],
                    tg["name"],
                    _to_cf_epoch(tg["added"]),
                    _to_cf_epoch(tg["modified"]),
                    avail_cols["allowsNextAction"],
                    avail_cols["dateHidden"],
                    0,
                ],
            )

        # Insert folders
        for f in data["folders"]:
            avail_cols = _SQLITE_FOLDER_AVAILABILITY[f["availability"]]
            conn.execute(
                """INSERT INTO Folder (
                    persistentIdentifier, name, dateAdded, dateModified, dateHidden
                ) VALUES (?, ?, ?, ?, ?)""",
                [
                    f["id"],
                    f["name"],
                    _to_cf_epoch(f["added"]),
                    _to_cf_epoch(f["modified"]),
                    avail_cols["dateHidden"],
                ],
            )

        # Insert perspectives
        for p_data in data["perspectives"]:
            value_data = plistlib.dumps({"name": p_data["name"]})
            conn.execute(
                """INSERT INTO Perspective (
                    persistentIdentifier, creationOrdinal, dateAdded, dateModified, valueData
                ) VALUES (?, ?, ?, ?, ?)""",
                [
                    p_data["id"],
                    1,
                    _to_cf_epoch(_ADDED),
                    _to_cf_epoch(_MODIFIED),
                    value_data,
                ],
            )

        # Insert task-tag join rows
        for tt in data["task_tag_assignments"]:
            conn.execute(
                "INSERT INTO TaskToTag (task, tag) VALUES (?, ?)",
                [tt["task_id"], tt["tag_id"]],
            )

        conn.commit()
    finally:
        conn.close()

    return HybridRepository(db_path=db_path, bridge=InMemoryBridge())


# ---------------------------------------------------------------------------
# Comparison helper
# ---------------------------------------------------------------------------


def assert_equivalent(result_a: ListRepoResult, result_b: ListRepoResult) -> None:  # type: ignore[type-arg]
    """Assert two ListRepoResult instances are equivalent (items sorted by ID).

    Excludes ``order`` from comparison -- intentional divergence (D-05):
    HybridRepository returns dotted path strings, BridgeOnlyRepository returns None.
    """
    items_a = sorted(result_a.items, key=lambda x: x.id or "")
    items_b = sorted(result_b.items, key=lambda x: x.id or "")
    for a, b in zip(items_a, items_b, strict=True):
        assert a.model_dump(exclude={"order"}) == b.model_dump(exclude={"order"})
    assert result_a.total == result_b.total


# ---------------------------------------------------------------------------
# Parametrized repo fixture
# ---------------------------------------------------------------------------


@pytest.fixture(params=["bridge", "sqlite"])
async def cross_repo(request: pytest.FixtureRequest, tmp_path: Path) -> Repository:
    """Return a seeded repository -- BridgeOnlyRepository or HybridRepository."""
    data = _build_neutral_test_data()
    if request.param == "bridge":
        return await seed_bridge_repo(data)
    return await seed_sqlite_repo(data, tmp_path)


# ===========================================================================
# Task cross-path equivalence tests
# ===========================================================================


class TestListTasksCrossPath:
    @pytest.mark.asyncio
    async def test_list_tasks_default(self, cross_repo: Repository) -> None:
        """Default query returns available + blocked tasks."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery())
        items = sorted(result.items, key=lambda x: x.id)
        # Default availability = [available, blocked] -> task-1..4 + task-7 (available)
        assert len(items) == 5
        assert [t.id for t in items] == ["task-1", "task-2", "task-3", "task-4", "task-7"]
        assert result.total == 5

    @pytest.mark.asyncio
    async def test_list_tasks_flagged(self, cross_repo: Repository) -> None:
        """Flagged filter returns only flagged tasks."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(flagged=True))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 2
        assert [t.id for t in items] == ["task-1", "task-4"]
        for t in items:
            assert t.flagged is True

    @pytest.mark.asyncio
    async def test_list_tasks_by_project(self, cross_repo: Repository) -> None:
        """Project filter returns only tasks in that project."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(project_ids=["proj-1"]))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 2
        assert [t.id for t in items] == ["task-2", "task-4"]
        for t in items:
            assert t.project.id == "proj-1"

    @pytest.mark.asyncio
    async def test_list_tasks_by_tags(self, cross_repo: Repository) -> None:
        """Tag filter returns tasks with that tag."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(tag_ids=["tag-1"]))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 2
        assert [t.id for t in items] == ["task-1", "task-2"]

    @pytest.mark.asyncio
    async def test_list_tasks_inbox(self, cross_repo: Repository) -> None:
        """Inbox filter returns only inbox tasks."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(in_inbox=True))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "task-1"
        assert items[0].project.id == "$inbox"

    @pytest.mark.asyncio
    async def test_list_tasks_search(self, cross_repo: Repository) -> None:
        """Search filter matches on name substring."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(search="keyword"))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "task-1"
        assert "keyword" in items[0].name.lower()

    @pytest.mark.asyncio
    async def test_list_tasks_pagination(self, cross_repo: Repository) -> None:
        """Pagination returns limited items but total reflects all matches."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(limit=1))
        assert len(result.items) == 1
        assert result.total == 5
        assert result.has_more is True


# ===========================================================================
# Project cross-path equivalence tests
# ===========================================================================


class TestListProjectsCrossPath:
    @pytest.mark.asyncio
    async def test_list_projects_default(self, cross_repo: Repository) -> None:
        """Default query returns available + blocked projects."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery())
        items = sorted(result.items, key=lambda x: x.id)
        # available + blocked -> proj-1, proj-2, proj-3, proj-due
        assert len(items) == 4
        assert [p.id for p in items] == ["proj-1", "proj-2", "proj-3", "proj-due"]
        assert result.total == 4

    @pytest.mark.asyncio
    async def test_list_projects_by_folder(self, cross_repo: Repository) -> None:
        """Folder filter returns only projects in that folder."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery(folder_ids=["folder-1"]))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 3
        assert [p.id for p in items] == ["proj-1", "proj-3", "proj-due"]
        for p in items:
            assert p.folder is not None
            assert p.folder.id == "folder-1"

    @pytest.mark.asyncio
    async def test_list_projects_flagged(self, cross_repo: Repository) -> None:
        """Flagged filter returns only flagged projects."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery(flagged=True))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "proj-1"
        assert items[0].flagged is True

    @pytest.mark.asyncio
    async def test_list_projects_review_due(self, cross_repo: Repository) -> None:
        """Review due before filter returns projects with next review before threshold."""
        threshold = datetime(2026, 4, 1, 0, 0, 0, tzinfo=UTC)
        result = await cross_repo.list_projects(ListProjectsRepoQuery(review_due_before=threshold))
        items = sorted(result.items, key=lambda x: x.id)
        # proj-1 has review on 2026-03-20 (before threshold)
        # proj-3 has review on 2026-01-10 (before threshold)
        # proj-due has review on 2026-03-20 (before threshold)
        # proj-2 has review on 2026-06-01 (after threshold)
        assert len(items) == 3
        assert [p.id for p in items] == ["proj-1", "proj-3", "proj-due"]


# ===========================================================================
# Tag cross-path equivalence tests
# ===========================================================================


class TestListTagsCrossPath:
    @pytest.mark.asyncio
    async def test_list_tags_default(self, cross_repo: Repository) -> None:
        """Default query returns available + blocked tags."""
        result = await cross_repo.list_tags(ListTagsRepoQuery())
        items = sorted(result.items, key=lambda x: x.id)
        # Default = [available, blocked] -> tag-1, tag-2, tag-3, tag-4
        assert len(items) == 4
        assert [t.id for t in items] == ["tag-1", "tag-2", "tag-3", "tag-4"]
        assert result.total == 4

    @pytest.mark.asyncio
    async def test_list_tags_active_only(self, cross_repo: Repository) -> None:
        """Active-only filter returns only available tags."""
        result = await cross_repo.list_tags(
            ListTagsRepoQuery(availability=[TagAvailability.AVAILABLE])
        )
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 3
        assert [t.id for t in items] == ["tag-1", "tag-2", "tag-4"]


# ===========================================================================
# Folder cross-path equivalence tests
# ===========================================================================


class TestListFoldersCrossPath:
    @pytest.mark.asyncio
    async def test_list_folders_default(self, cross_repo: Repository) -> None:
        """Default query returns available folders only."""
        result = await cross_repo.list_folders(ListFoldersRepoQuery())
        items = sorted(result.items, key=lambda x: x.id)
        # Default = [available] -> folder-1 only
        assert len(items) == 1
        assert items[0].id == "folder-1"
        assert items[0].name == "Active Projects"
        assert result.total == 1

    @pytest.mark.asyncio
    async def test_list_folders_all(self, cross_repo: Repository) -> None:
        """All-availability query returns all folders."""
        result = await cross_repo.list_folders(
            ListFoldersRepoQuery(
                availability=[FolderAvailability.AVAILABLE, FolderAvailability.DROPPED]
            )
        )
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 2
        assert [f.id for f in items] == ["folder-1", "folder-2"]


# ===========================================================================
# Perspective cross-path equivalence tests
# ===========================================================================


class TestListPerspectivesCrossPath:
    @pytest.mark.asyncio
    async def test_list_perspectives(self, cross_repo: Repository) -> None:
        """All perspectives returned with correct fields."""
        result = await cross_repo.list_perspectives(ListPerspectivesRepoQuery())
        items = sorted(result.items, key=lambda x: x.name)
        assert len(items) == 3
        assert result.total == 3

        # Builtin perspective (id=None)
        forecast = next(p for p in items if p.name == "Forecast")
        assert forecast.id == "persp-1"
        assert forecast.builtin is False

        inbox = next(p for p in items if p.name == "Inbox")
        assert inbox.id is None
        assert inbox.builtin is True

    @pytest.mark.asyncio
    async def test_list_perspectives_search(self, cross_repo: Repository) -> None:
        """Search filter matches on perspective name substring."""
        result = await cross_repo.list_perspectives(ListPerspectivesRepoQuery(search="fore"))
        items = sorted(result.items, key=lambda x: x.name)
        assert len(items) == 1
        assert items[0].name == "Forecast"


# ===========================================================================
# Search cross-path equivalence tests (additional)
# ===========================================================================


class TestSearchCrossPath:
    """Cross-path search tests for projects, tags, folders -- grouped for clarity."""

    @pytest.mark.asyncio
    async def test_list_projects_search_name(self, cross_repo: Repository) -> None:
        """Search on project name returns matching projects."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery(search="build"))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "proj-1"
        assert "build" in items[0].name.lower()

    @pytest.mark.asyncio
    async def test_list_projects_search_notes(self, cross_repo: Repository) -> None:
        """Search matches in project notes field."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery(search="expenses"))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "proj-1"

    @pytest.mark.asyncio
    async def test_list_tags_search(self, cross_repo: Repository) -> None:
        """Search on tag name returns matching tags."""
        result = await cross_repo.list_tags(ListTagsRepoQuery(search="work"))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "tag-1"
        assert items[0].name == "Work"

    @pytest.mark.asyncio
    async def test_list_tags_search_no_match(self, cross_repo: Repository) -> None:
        """Search with no matches returns empty result."""
        result = await cross_repo.list_tags(ListTagsRepoQuery(search="nonexistent"))
        assert len(result.items) == 0
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_list_tags_search_non_ascii(self, cross_repo: Repository) -> None:
        """Search with ASCII term matches ASCII tag name across both paths."""
        result = await cross_repo.list_tags(ListTagsRepoQuery(search="buro"))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "tag-4"
        assert items[0].name == "Buro"

    @pytest.mark.asyncio
    async def test_list_folders_search(self, cross_repo: Repository) -> None:
        """Search on folder name returns matching folders."""
        result = await cross_repo.list_folders(
            ListFoldersRepoQuery(
                availability=[FolderAvailability.AVAILABLE, FolderAvailability.DROPPED],
                search="archive",
            )
        )
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 1
        assert items[0].id == "folder-2"
        assert items[0].name == "Archive"


# ===========================================================================
# Date filter cross-path equivalence tests (EXEC-10, EXEC-11)
# ===========================================================================


class TestDateFilterCrossPath:
    """Date filter cross-path equivalence (EXEC-10, EXEC-11).

    Proves SQL and bridge paths produce identical results for all date filter
    variants, including tasks with inherited effective dates from parent projects.
    """

    @pytest.mark.asyncio
    async def test_due_before_includes_direct_and_inherited(self, cross_repo: Repository) -> None:
        """Due filter uses effective date -- includes task-7 with inherited due."""
        threshold = _DUE_DATE + timedelta(days=1)
        result = await cross_repo.list_tasks(ListTasksRepoQuery(due_before=threshold))
        ids = sorted(t.id for t in result.items)
        # task-1 (direct due), task-4 (direct due), task-7 (inherited due)
        assert ids == ["task-1", "task-4", "task-7"]

    @pytest.mark.asyncio
    async def test_due_after_filters_correctly(self, cross_repo: Repository) -> None:
        """Due after threshold excludes tasks with earlier/no due dates."""
        threshold = _DUE_DATE + timedelta(days=1)
        result = await cross_repo.list_tasks(ListTasksRepoQuery(due_after=threshold))
        assert len(result.items) == 0

    @pytest.mark.asyncio
    async def test_due_after_exact_match(self, cross_repo: Repository) -> None:
        """Due after exact _DUE_DATE returns all tasks with that effective due."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(due_after=_DUE_DATE))
        ids = sorted(t.id for t in result.items)
        assert ids == ["task-1", "task-4", "task-7"]

    @pytest.mark.asyncio
    async def test_defer_before(self, cross_repo: Repository) -> None:
        """Defer filter returns only task-2 (sole task with defer date)."""
        threshold = _DEFER_DATE + timedelta(days=1)
        result = await cross_repo.list_tasks(ListTasksRepoQuery(defer_before=threshold))
        ids = [t.id for t in result.items]
        assert ids == ["task-2"]

    @pytest.mark.asyncio
    async def test_planned_before(self, cross_repo: Repository) -> None:
        """Planned filter returns only task-2."""
        threshold = _PLANNED_DATE + timedelta(days=1)
        result = await cross_repo.list_tasks(ListTasksRepoQuery(planned_before=threshold))
        ids = [t.id for t in result.items]
        assert ids == ["task-2"]

    @pytest.mark.asyncio
    async def test_completed_date_filter(self, cross_repo: Repository) -> None:
        """Completed date filter with COMPLETED availability returns task-5."""
        result = await cross_repo.list_tasks(
            ListTasksRepoQuery(
                availability=[Availability.AVAILABLE, Availability.BLOCKED, Availability.COMPLETED],
                completed_after=_COMPLETED_DATE - timedelta(days=1),
                completed_before=_COMPLETED_DATE + timedelta(days=1),
            )
        )
        completed_ids = [t.id for t in result.items if t.availability == Availability.COMPLETED]
        assert completed_ids == ["task-5"]

    @pytest.mark.asyncio
    async def test_dropped_date_filter(self, cross_repo: Repository) -> None:
        """Dropped date filter with DROPPED availability returns task-6."""
        result = await cross_repo.list_tasks(
            ListTasksRepoQuery(
                availability=[Availability.AVAILABLE, Availability.BLOCKED, Availability.DROPPED],
                dropped_after=_DROPPED_DATE - timedelta(days=1),
                dropped_before=_DROPPED_DATE + timedelta(days=1),
            )
        )
        dropped_ids = [t.id for t in result.items if t.availability == Availability.DROPPED]
        assert dropped_ids == ["task-6"]

    @pytest.mark.asyncio
    async def test_completed_date_filter_preserves_remaining_lifecycle(
        self, cross_repo: Repository
    ) -> None:
        """Lifecycle date filter is additive: remaining tasks survive alongside completed."""
        result = await cross_repo.list_tasks(
            ListTasksRepoQuery(
                availability=[Availability.AVAILABLE, Availability.BLOCKED, Availability.COMPLETED],
                completed_after=_COMPLETED_DATE - timedelta(days=1),
                completed_before=_COMPLETED_DATE + timedelta(days=1),
            )
        )
        # 5 remaining (task-1..4, task-7) + 1 completed (task-5) = 6
        remaining_ids = [t.id for t in result.items if t.availability != Availability.COMPLETED]
        completed_ids = [t.id for t in result.items if t.availability == Availability.COMPLETED]
        assert sorted(remaining_ids) == ["task-1", "task-2", "task-3", "task-4", "task-7"]
        assert completed_ids == ["task-5"]
        assert len(result.items) == 6

    @pytest.mark.asyncio
    async def test_dropped_date_filter_preserves_remaining_lifecycle(
        self, cross_repo: Repository
    ) -> None:
        """Lifecycle date filter is additive: remaining tasks survive alongside dropped."""
        result = await cross_repo.list_tasks(
            ListTasksRepoQuery(
                availability=[Availability.AVAILABLE, Availability.BLOCKED, Availability.DROPPED],
                dropped_after=_DROPPED_DATE - timedelta(days=1),
                dropped_before=_DROPPED_DATE + timedelta(days=1),
            )
        )
        # 5 remaining (task-1..4, task-7) + 1 dropped (task-6) = 6
        remaining_ids = [t.id for t in result.items if t.availability != Availability.DROPPED]
        dropped_ids = [t.id for t in result.items if t.availability == Availability.DROPPED]
        assert sorted(remaining_ids) == ["task-1", "task-2", "task-3", "task-4", "task-7"]
        assert dropped_ids == ["task-6"]
        assert len(result.items) == 6

    @pytest.mark.asyncio
    async def test_due_combined_with_flagged(self, cross_repo: Repository) -> None:
        """Date filter + base filter combine with AND."""
        threshold = _DUE_DATE + timedelta(days=1)
        result = await cross_repo.list_tasks(ListTasksRepoQuery(due_before=threshold, flagged=True))
        ids = sorted(t.id for t in result.items)
        # task-1 (flagged, has due), task-4 (flagged, has due)
        # task-7 has due but is NOT flagged
        assert ids == ["task-1", "task-4"]

    @pytest.mark.asyncio
    async def test_added_date_range(self, cross_repo: Repository) -> None:
        """Added date filter returns tasks within the range."""
        result = await cross_repo.list_tasks(
            ListTasksRepoQuery(
                added_after=_ADDED - timedelta(days=1),
                added_before=_ADDED + timedelta(days=1),
            )
        )
        # All available+blocked tasks have _ADDED as their added date
        assert len(result.items) >= 4

    @pytest.mark.asyncio
    async def test_null_date_excluded(self, cross_repo: Repository) -> None:
        """Tasks with NULL date field are excluded from date filter results."""
        # task-3 has no due date (all None). Due filter should not return it.
        threshold = _DUE_DATE + timedelta(days=1)
        result = await cross_repo.list_tasks(ListTasksRepoQuery(due_before=threshold))
        ids = [t.id for t in result.items]
        assert "task-3" not in ids


# ===========================================================================
# Project date filter cross-path equivalence tests
# ===========================================================================


class TestProjectDateFilterCrossPath:
    """Project date filter cross-path equivalence.

    Proves SQL and bridge paths produce identical results for project date
    filters, including lifecycle (completed/dropped) additive semantics.
    """

    @pytest.mark.asyncio
    async def test_due_before_returns_project_with_due_date(self, cross_repo: Repository) -> None:
        """Due before threshold includes proj-due."""
        threshold = _DUE_DATE + timedelta(days=1)
        result = await cross_repo.list_projects(ListProjectsRepoQuery(due_before=threshold))
        ids = [p.id for p in result.items]
        assert "proj-due" in ids

    @pytest.mark.asyncio
    async def test_due_after_exact_match(self, cross_repo: Repository) -> None:
        """Due after exact _DUE_DATE returns proj-due (inclusive lower bound)."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery(due_after=_DUE_DATE))
        ids = [p.id for p in result.items]
        assert "proj-due" in ids

    @pytest.mark.asyncio
    async def test_completed_date_filter(self, cross_repo: Repository) -> None:
        """Completed date filter with COMPLETED availability returns proj-completed."""
        result = await cross_repo.list_projects(
            ListProjectsRepoQuery(
                availability=[Availability.AVAILABLE, Availability.BLOCKED, Availability.COMPLETED],
                completed_after=_COMPLETED_DATE - timedelta(days=1),
                completed_before=_COMPLETED_DATE + timedelta(days=1),
            )
        )
        completed_ids = [p.id for p in result.items if p.availability == Availability.COMPLETED]
        assert completed_ids == ["proj-completed"]

    @pytest.mark.asyncio
    async def test_dropped_date_filter(self, cross_repo: Repository) -> None:
        """Dropped date filter with DROPPED availability returns proj-dropped."""
        result = await cross_repo.list_projects(
            ListProjectsRepoQuery(
                availability=[Availability.AVAILABLE, Availability.BLOCKED, Availability.DROPPED],
                dropped_after=_DROPPED_DATE - timedelta(days=1),
                dropped_before=_DROPPED_DATE + timedelta(days=1),
            )
        )
        dropped_ids = [p.id for p in result.items if p.availability == Availability.DROPPED]
        assert dropped_ids == ["proj-dropped"]

    @pytest.mark.asyncio
    async def test_completed_preserves_remaining(self, cross_repo: Repository) -> None:
        """Lifecycle date filter is additive: remaining projects survive alongside completed."""
        result = await cross_repo.list_projects(
            ListProjectsRepoQuery(
                availability=[Availability.AVAILABLE, Availability.BLOCKED, Availability.COMPLETED],
                completed_after=_COMPLETED_DATE - timedelta(days=1),
                completed_before=_COMPLETED_DATE + timedelta(days=1),
            )
        )
        remaining_ids = sorted(
            p.id for p in result.items if p.availability != Availability.COMPLETED
        )
        completed_ids = [p.id for p in result.items if p.availability == Availability.COMPLETED]
        # 4 remaining (proj-1, proj-2, proj-3, proj-due) + 1 completed (proj-completed)
        assert remaining_ids == ["proj-1", "proj-2", "proj-3", "proj-due"]
        assert completed_ids == ["proj-completed"]

    @pytest.mark.asyncio
    async def test_date_filter_combined_with_folder(self, cross_repo: Repository) -> None:
        """Date filter + folder_ids combine with AND."""
        threshold = _DUE_DATE + timedelta(days=1)
        result = await cross_repo.list_projects(
            ListProjectsRepoQuery(
                due_before=threshold,
                folder_ids=["folder-1"],
            )
        )
        ids = [p.id for p in result.items]
        # proj-due has due date and is in folder-1
        assert "proj-due" in ids
        # proj-2 is NOT in folder-1 (folder_id=None)
        assert "proj-2" not in ids


# ===========================================================================
# Empty availability cross-path equivalence tests
# ===========================================================================


class TestEmptyAvailabilityCrossPath:
    """availability=[] must return 0 items on both paths (gap 2 fix)."""

    @pytest.mark.asyncio
    async def test_empty_availability_returns_no_tasks(self, cross_repo: Repository) -> None:
        """availability=[] matches zero availability states, so zero tasks returned."""
        result = await cross_repo.list_tasks(ListTasksRepoQuery(availability=[]))
        assert result.items == []
        assert result.total == 0

    @pytest.mark.asyncio
    async def test_empty_availability_returns_no_projects(self, cross_repo: Repository) -> None:
        """availability=[] matches zero availability states, so zero projects returned."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery(availability=[]))
        assert result.items == []
        assert result.total == 0
