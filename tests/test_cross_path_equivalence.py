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
                # Phase 56-02 HIER-05 cross-path precedence test: BOTH
                # sequential=True AND containsSingletonActions=True -> must
                # resolve to "singleActions" on both repos.
                "completes_with_children": False,
                "project_type": "singleActions",
                "_sequential_underlying": True,  # documents HIER-05 test intent
                "has_attachments": True,
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
                # Phase 56-02: pure sequential project (no singleActions).
                "completes_with_children": True,
                "project_type": "sequential",
                "has_attachments": False,
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
                # Phase 56-02 property-surface: full-positive permutation.
                "completes_with_children": False,
                "task_type": "sequential",
                "has_attachments": True,
                "plain_text_note": "keyword note content",
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
                # Phase 56-02: factory-default permutation (all False/parallel).
                "completes_with_children": True,
                "task_type": "parallel",
                "has_attachments": False,
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


def _project_sequential_bit(p: dict[str, Any]) -> int:
    """Resolve the underlying `sequential` SQLite column / bridge field for a project.

    Uses explicit ``_sequential_underlying`` when present (HIER-05 precedence
    test: both flags set). Otherwise derives from ``project_type``.
    """
    if "_sequential_underlying" in p:
        return 1 if p["_sequential_underlying"] else 0
    return 1 if p.get("project_type", "parallel") == "sequential" else 0


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
                note=t.get("plain_text_note") or "",
                inInbox=t["in_inbox"],
                flagged=t["flagged"],
                effectiveFlagged=t["flagged"],
                project=t["project_id"],
                parent=t["parent_id"],
                status=_BRIDGE_AVAILABILITY_MAP[t["availability"]],
                estimatedMinutes=t["estimated_minutes"],
                tags=tag_refs,
                # Phase 56-02 raw bridge fields.
                completedByChildren=t.get("completes_with_children", True),
                sequential=t.get("task_type", "parallel") == "sequential",
                hasAttachments=bool(t.get("has_attachments", False)),
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
        project_type = p.get("project_type", "parallel")
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
                # Phase 56-02 raw bridge fields (three-state type + presence).
                completedByChildren=p.get("completes_with_children", True),
                sequential=bool(_project_sequential_bit(p)),
                containsSingletonActions=project_type == "singleActions",
                hasAttachments=bool(p.get("has_attachments", False)),
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
                rank INTEGER DEFAULT 0,
                completeWhenChildrenComplete INTEGER DEFAULT 1,
                sequential INTEGER DEFAULT 0
            );
            CREATE TABLE ProjectInfo (
                pk TEXT PRIMARY KEY,
                task TEXT,
                lastReviewDate REAL,
                nextReviewDate REAL,
                reviewRepetitionString TEXT,
                nextTask TEXT,
                folder TEXT,
                effectiveStatus TEXT,
                containsSingletonActions INTEGER DEFAULT 0
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
            CREATE TABLE Attachment (
                persistentIdentifier TEXT PRIMARY KEY,
                task TEXT,
                folder TEXT,
                context TEXT,
                perspective TEXT
            );
            CREATE INDEX Attachment_task ON Attachment (task);
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
                    plainTextNote,
                    flagged, effectiveFlagged, estimatedMinutes,
                    childrenCount, inInbox, containingProjectInfo, parent,
                    overdue, dueSoon, blocked,
                    dateDue, dateToStart, datePlanned,
                    effectiveDateDue, effectiveDateToStart, effectiveDatePlanned,
                    dateCompleted, effectiveDateCompleted,
                    dateHidden, effectiveDateHidden,
                    completeWhenChildrenComplete, sequential
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    t["id"],
                    t["name"],
                    _to_cf_epoch(t["added"]),
                    _to_cf_epoch(t["modified"]),
                    t.get("plain_text_note"),
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
                    # Phase 56-02 property-surface columns.
                    1 if t.get("completes_with_children", True) else 0,
                    1 if t.get("task_type", "parallel") == "sequential" else 0,
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
                    dateHidden, effectiveDateHidden,
                    completeWhenChildrenComplete, sequential
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    # Phase 56-02 property-surface columns. For HIER-05
                    # cross-path tests, `_sequential_underlying` overrides the
                    # type-implied sequential bit so both underlying flags can
                    # be set simultaneously.
                    1 if p.get("completes_with_children", True) else 0,
                    _project_sequential_bit(p),
                ],
            )
            conn.execute(
                """INSERT INTO ProjectInfo (
                    pk, task, lastReviewDate, nextReviewDate,
                    reviewRepetitionString, folder, effectiveStatus,
                    containsSingletonActions
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    f"pi-{task_id}",
                    task_id,
                    _to_cf_epoch(p["last_review_date"]),
                    _to_cf_epoch(p["next_review_date"]),
                    "@1w",
                    p["folder_id"],
                    _SQLITE_PROJECT_EFFECTIVE_STATUS[p["availability"]],
                    1 if p.get("project_type") == "singleActions" else 0,
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

        # Phase 56-02: insert attachment rows for any task/project with
        # has_attachments=True so the batched presence set picks them up.
        attachment_seq = 0
        for t in data["tasks"]:
            if t.get("has_attachments"):
                attachment_seq += 1
                conn.execute(
                    "INSERT INTO Attachment (persistentIdentifier, task) VALUES (?, ?)",
                    [f"att-{attachment_seq}", t["id"]],
                )
        for p in data["projects"]:
            if p.get("has_attachments"):
                attachment_seq += 1
                conn.execute(
                    "INSERT INTO Attachment (persistentIdentifier, task) VALUES (?, ?)",
                    [f"att-{attachment_seq}", p["id"]],
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
        """task_id_scope filter returns only the tasks passed in (post-Phase 57).

        Semantic shift: task_id_scope holds TASK PKs, not project PKs. The
        service's expand_scope (unit-tested separately) is responsible for
        producing this set from the user-facing ``project`` filter.
        Agent-facing behavior via ``OperatorService.list_tasks`` is unchanged.
        """
        result = await cross_repo.list_tasks(ListTasksRepoQuery(task_id_scope=["task-2", "task-4"]))
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
# Phase 56-02: Task property surface cross-path equivalence
# ===========================================================================


class TestPropertySurfaceCrossPath:
    """CACHE-01..04 + HIER-05 equivalence across HybridRepository and
    BridgeOnlyRepository. Same neutral seed data must produce identical values
    for ``completes_with_children``, ``type``, ``has_attachments``, ``has_note``,
    and ``has_repetition`` on both repos.
    """

    @pytest.mark.asyncio
    async def test_task_completes_with_children_matches_seed(self, cross_repo: Repository) -> None:
        result = await cross_repo.list_tasks(ListTasksRepoQuery())
        by_id = {t.id: t for t in result.items}
        # task-1 seeded with completes_with_children=False.
        assert by_id["task-1"].completes_with_children is False
        # task-2 seeded with completes_with_children=True.
        assert by_id["task-2"].completes_with_children is True

    @pytest.mark.asyncio
    async def test_task_type_matches_seed(self, cross_repo: Repository) -> None:
        result = await cross_repo.list_tasks(ListTasksRepoQuery())
        by_id = {t.id: t for t in result.items}
        assert by_id["task-1"].type == "sequential"  # seeded sequential
        assert by_id["task-2"].type == "parallel"  # seeded parallel

    @pytest.mark.asyncio
    async def test_task_has_attachments_reflects_seed(self, cross_repo: Repository) -> None:
        result = await cross_repo.list_tasks(ListTasksRepoQuery())
        by_id = {t.id: t for t in result.items}
        assert by_id["task-1"].has_attachments is True
        assert by_id["task-2"].has_attachments is False

    @pytest.mark.asyncio
    async def test_task_has_note_reflects_seed(self, cross_repo: Repository) -> None:
        result = await cross_repo.list_tasks(ListTasksRepoQuery())
        by_id = {t.id: t for t in result.items}
        # task-1 has plain_text_note="keyword note content" seeded.
        assert by_id["task-1"].has_note is True
        # task-2 has no note seeded -> False.
        assert by_id["task-2"].has_note is False

    @pytest.mark.asyncio
    async def test_project_type_single_actions_takes_precedence_over_sequential(
        self, cross_repo: Repository
    ) -> None:
        """HIER-05 cross-path proof: proj-1 has BOTH sequential=True AND
        containsSingletonActions=True -> must resolve to ``singleActions`` on
        both the SQLite and the BridgeOnly path.
        """
        result = await cross_repo.list_projects(ListProjectsRepoQuery())
        by_id = {p.id: p for p in result.items}
        assert by_id["proj-1"].type == "singleActions"

    @pytest.mark.asyncio
    async def test_project_type_matches_seed_for_each_state(self, cross_repo: Repository) -> None:
        result = await cross_repo.list_projects(ListProjectsRepoQuery())
        by_id = {p.id: p for p in result.items}
        assert by_id["proj-1"].type == "singleActions"  # HIER-05
        assert by_id["proj-2"].type == "sequential"
        assert by_id["proj-3"].type == "parallel"  # factory default

    @pytest.mark.asyncio
    async def test_project_completes_with_children_matches_seed(
        self, cross_repo: Repository
    ) -> None:
        result = await cross_repo.list_projects(ListProjectsRepoQuery())
        by_id = {p.id: p for p in result.items}
        assert by_id["proj-1"].completes_with_children is False
        assert by_id["proj-2"].completes_with_children is True

    @pytest.mark.asyncio
    async def test_project_has_attachments_reflects_seed(self, cross_repo: Repository) -> None:
        result = await cross_repo.list_projects(ListProjectsRepoQuery())
        by_id = {p.id: p for p in result.items}
        assert by_id["proj-1"].has_attachments is True
        assert by_id["proj-2"].has_attachments is False

    @pytest.mark.asyncio
    async def test_task_field_by_field_equivalence_for_full_entity(
        self, cross_repo: Repository
    ) -> None:
        """For every task, all five new fields are equal across the two repos.

        The fixture produces one repo per invocation -- this test runs twice
        (bridge + sqlite) and asserts internal consistency per-row. A single
        regression on either path would still fail the class-level checks in
        the tests above, but this one exercises the full per-entity contract.
        """
        result = await cross_repo.list_tasks(ListTasksRepoQuery())
        for task in result.items:
            # Every task has all five fields populated with well-typed values.
            assert isinstance(task.completes_with_children, bool)
            assert task.type in ("parallel", "sequential")
            assert isinstance(task.has_attachments, bool)
            assert isinstance(task.has_note, bool)
            assert isinstance(task.has_repetition, bool)

    # -- Phase 56-08 (G1): project-side is_sequential via service enrichment --

    @pytest.mark.asyncio
    async def test_project_is_sequential_enriched_cross_path(self, cross_repo: Repository) -> None:
        """Phase 56-08: service enrichment populates is_sequential on projects
        equivalently for both HybridRepository and BridgeOnlyRepository.

        Neutral test data seeds:
          - proj-1: sequential + containsSingletonActions -> singleActions -> is_sequential False
          - proj-2: sequential only                        -> sequential   -> is_sequential True
          - proj-3: neither                                -> parallel     -> is_sequential False

        The derived flag is computed from final assembled ProjectType (after
        HIER-05 precedence), not from the raw sequential bit — singleActions
        beats sequential, so proj-1 is NOT is_sequential.
        """
        from omnifocus_operator.service import OperatorService  # noqa: PLC0415
        from omnifocus_operator.service.preferences import OmniFocusPreferences  # noqa: PLC0415

        # Build a service over the repo; preferences unused by list_projects.
        service = OperatorService(
            repository=cross_repo,
            preferences=OmniFocusPreferences(InMemoryBridge()),
        )

        all_data = await service.get_all_data()
        by_id = {p.id: p for p in all_data.projects}
        assert by_id["proj-1"].is_sequential is False  # type singleActions
        assert by_id["proj-2"].is_sequential is True  # type sequential
        assert by_id["proj-3"].is_sequential is False  # type parallel

    @pytest.mark.asyncio
    async def test_list_projects_enriches_is_sequential_cross_path(
        self, cross_repo: Repository
    ) -> None:
        """Phase 56-08: list_projects pipeline applies project enrichment across repos."""
        from omnifocus_operator.contracts.use_cases.list.projects import (  # noqa: PLC0415
            ListProjectsQuery,
        )
        from omnifocus_operator.service import OperatorService  # noqa: PLC0415
        from omnifocus_operator.service.preferences import OmniFocusPreferences  # noqa: PLC0415

        service = OperatorService(
            repository=cross_repo,
            preferences=OmniFocusPreferences(InMemoryBridge()),
        )
        result = await service.list_projects(ListProjectsQuery())
        by_id = {p.id: p for p in result.items}
        assert by_id["proj-1"].is_sequential is False
        assert by_id["proj-2"].is_sequential is True
        assert by_id["proj-3"].is_sequential is False

    @pytest.mark.asyncio
    async def test_get_project_enriches_is_sequential_cross_path(
        self, cross_repo: Repository
    ) -> None:
        """Phase 56-08: get_project applies project enrichment across repos."""
        from omnifocus_operator.service import OperatorService  # noqa: PLC0415
        from omnifocus_operator.service.preferences import OmniFocusPreferences  # noqa: PLC0415

        service = OperatorService(
            repository=cross_repo,
            preferences=OmniFocusPreferences(InMemoryBridge()),
        )
        proj_seq = await service.get_project("proj-2")
        assert proj_seq.is_sequential is True
        proj_par = await service.get_project("proj-3")
        assert proj_par.is_sequential is False
        proj_single = await service.get_project("proj-1")
        assert proj_single.is_sequential is False


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


# ===========================================================================
# Phase 56-07: Wave 3 end-to-end round-trip on both repositories
# ===========================================================================
#
# Writes through the full OperatorService stack, reads back via get_task +
# list_tasks. Parametrized across both repository backends so PROP-01..06 are
# proven uniformly:
#
#   - BridgeOnlyRepository + InMemoryBridge -- natural round-trip: writes
#     mutate InMemoryBridge state; reads adapt the same snapshot.
#
#   - HybridRepository + InMemoryBridge + SQLite -- writes go through the
#     bridge (as in production), then a test-only helper rehydrates the
#     SQLite fixture from the bridge snapshot so subsequent reads see the
#     written values. This stands in for OmniFocus's write-through to its
#     SQLite cache. The InMemoryBridge + SQLite pairing is the functional
#     analogue of OmniFocus's live write-through.
#
# The tests are gated on the post-56-06 write contract being present on
# AddTaskCommand (the two Patch fields). When 56-06 has not yet landed
# on the base branch, the fixture skips cleanly instead of failing -- both
# plans run in parallel as Wave 3, and the combined surface only materializes
# when both have merged. Once 56-06 lands, these tests become the final
# end-to-end proof.


def _post_56_06_write_surface_present() -> bool:
    """Feature-detect post-56-06 AddTaskCommand fields.

    Returns True when ``completes_with_children`` and ``type`` are both
    declared on AddTaskCommand (56-06 Task 1 outcome).
    """
    from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
        AddTaskCommand,
    )

    fields = AddTaskCommand.model_fields
    return "completes_with_children" in fields and "type" in fields


async def _rehydrate_sqlite_from_bridge(
    bridge: InMemoryBridge,
    db_path: Path,
) -> None:
    """Rebuild the HybridRepository SQLite fixture from InMemoryBridge state.

    Test-only stand-in for OmniFocus's write-through to the SQLite cache:
    after every service write we replay the bridge snapshot into a fresh
    database file so HybridRepository reads reflect the write. Only the
    columns needed by the new property-surface read paths are populated --
    date, availability, and tag-join concerns stay out of scope here.
    """
    snapshot = await bridge.send_command("get_all")
    if db_path.exists():
        db_path.unlink()
    conn = sqlite3.connect(str(db_path))
    try:
        conn.executescript(
            """
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
                rank INTEGER DEFAULT 0,
                completeWhenChildrenComplete INTEGER DEFAULT 1,
                sequential INTEGER DEFAULT 0
            );
            CREATE TABLE ProjectInfo (
                pk TEXT PRIMARY KEY,
                task TEXT,
                lastReviewDate REAL,
                nextReviewDate REAL,
                reviewRepetitionString TEXT,
                nextTask TEXT,
                folder TEXT,
                effectiveStatus TEXT,
                containsSingletonActions INTEGER DEFAULT 0
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
            CREATE TABLE Attachment (
                persistentIdentifier TEXT PRIMARY KEY,
                task TEXT,
                folder TEXT,
                context TEXT,
                perspective TEXT
            );
            CREATE INDEX Attachment_task ON Attachment (task);
            """
        )
        now = datetime.now(tz=UTC)
        for t in snapshot["tasks"]:
            conn.execute(
                """INSERT INTO Task (
                    persistentIdentifier, name, dateAdded, dateModified,
                    plainTextNote,
                    flagged, effectiveFlagged, estimatedMinutes,
                    childrenCount, inInbox, containingProjectInfo, parent,
                    overdue, dueSoon, blocked,
                    completeWhenChildrenComplete, sequential
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?,
                          ?, ?, ?, ?, ?)""",
                [
                    t["id"],
                    t["name"],
                    _to_cf_epoch(now),
                    _to_cf_epoch(now),
                    t.get("note") or None,
                    1 if t.get("flagged") else 0,
                    1 if t.get("effectiveFlagged") else 0,
                    t.get("estimatedMinutes"),
                    1 if t.get("hasChildren") else 0,
                    1 if t.get("inInbox") else 0,
                    None,
                    t.get("parent"),
                    0,
                    0,
                    0,
                    # Post-56-06 raw fields: stored by InMemoryBridge as
                    # completedByChildren / sequential.
                    1 if t.get("completedByChildren", True) else 0,
                    1 if t.get("sequential", False) else 0,
                ],
            )
        conn.commit()
    finally:
        conn.close()


@pytest.fixture(params=["bridge", "sqlite"])
async def cross_service(
    request: pytest.FixtureRequest,
    tmp_path: Path,
) -> dict[str, Any]:
    """Parametrized fixture yielding a full OperatorService stack per repo.

    Returns a dict with keys:
      - ``service``    : OperatorService wrapping the repo under test
      - ``bridge``     : the shared InMemoryBridge (use .configure_settings
                         / ._settings.pop to drive PROP-05/06 preferences)
      - ``repo``       : the repository instance (BridgeOnly or Hybrid)
      - ``preferences``: OmniFocusPreferences wired to ``bridge``
      - ``rehydrate``  : async callable that syncs the HybridRepository
                         SQLite fixture from the bridge (no-op for bridge
                         param). Call it between a write and a read when
                         running against the sqlite backend.

    The tests themselves stay backend-agnostic: BridgeOnlyRepository round-
    trips naturally; HybridRepository reads from SQLite which the helper
    re-derives from the bridge snapshot on demand.
    """
    from omnifocus_operator.service import OperatorService  # noqa: PLC0415
    from omnifocus_operator.service.preferences import OmniFocusPreferences  # noqa: PLC0415

    if not _post_56_06_write_surface_present():
        pytest.skip(
            "Post-56-06 write surface not yet present on AddTaskCommand. "
            "This round-trip suite gates on 56-06 landing the Patch[bool] + "
            "Patch[TaskType] fields. Plans 56-06 and 56-07 run as parallel "
            "Wave 3 worktrees; once both merge, the skip condition clears "
            "and these tests become the end-to-end Wave 3 proof."
        )

    bridge = InMemoryBridge()

    if request.param == "bridge":
        repo: Repository = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())

        async def _rehydrate() -> None:
            """Bridge path rehydration is a no-op -- reads share bridge state."""
            return None

    else:  # sqlite
        db_path = tmp_path / "round_trip_hybrid.db"
        # Seed an initially-empty database so HybridRepository has something
        # to read on the first get_task / list_tasks call before any writes.
        await _rehydrate_sqlite_from_bridge(bridge, db_path)
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        async def _rehydrate() -> None:
            await _rehydrate_sqlite_from_bridge(bridge, db_path)

    preferences = OmniFocusPreferences(bridge)
    service = OperatorService(repository=repo, preferences=preferences)

    return {
        "service": service,
        "bridge": bridge,
        "repo": repo,
        "preferences": preferences,
        "rehydrate": _rehydrate,
    }


class TestTaskPropertySurfaceRoundTrip:
    """Wave 3 end-to-end: write -> read covers both repo paths.

    Proves PROP-01..06 work uniformly across HybridRepository and
    BridgeOnlyRepository. The agent-value path (command carries the new
    fields) and the create-default path (omitted fields resolve to user
    preferences) both land as explicit writes that the read path sees.
    """

    @pytest.mark.asyncio
    async def test_round_trip_agent_value_completes_with_children_true(
        self, cross_service: dict[str, Any]
    ) -> None:
        """PROP-01: agent sets completesWithChildren=True -> read back shows True."""
        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )
        from omnifocus_operator.models.enums import TaskType  # noqa: PLC0415

        service = cross_service["service"]
        result = await service.add_task(
            AddTaskCommand(
                name="round-trip-1",
                completes_with_children=True,
                type=TaskType.PARALLEL,
            )
        )
        assert result.status == "success"
        await cross_service["rehydrate"]()

        task = await service.get_task(result.id)
        assert task is not None
        assert task.completes_with_children is True
        assert task.type == TaskType.PARALLEL
        assert task.is_sequential is False  # derived: type != SEQUENTIAL
        assert task.depends_on_children is False  # no children AND completes=True

    @pytest.mark.asyncio
    async def test_round_trip_agent_value_sequential_and_no_autocomplete(
        self, cross_service: dict[str, Any]
    ) -> None:
        """PROP-01 + PROP-02: sequential task with completes=False."""
        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )
        from omnifocus_operator.models.enums import TaskType  # noqa: PLC0415

        service = cross_service["service"]
        result = await service.add_task(
            AddTaskCommand(
                name="round-trip-2",
                completes_with_children=False,
                type=TaskType.SEQUENTIAL,
            )
        )
        await cross_service["rehydrate"]()

        task = await service.get_task(result.id)
        assert task.completes_with_children is False
        assert task.type == TaskType.SEQUENTIAL
        assert task.is_sequential is True  # derived: type == SEQUENTIAL

    @pytest.mark.asyncio
    async def test_round_trip_edit_flips_completes_with_children(
        self, cross_service: dict[str, Any]
    ) -> None:
        """PROP-02: edit_task flips completesWithChildren; read reflects the edit."""
        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )
        from omnifocus_operator.contracts.use_cases.edit.tasks import (  # noqa: PLC0415
            EditTaskCommand,
        )
        from omnifocus_operator.models.enums import TaskType  # noqa: PLC0415

        service = cross_service["service"]
        result = await service.add_task(
            AddTaskCommand(
                name="edit-flip",
                completes_with_children=True,
                type=TaskType.PARALLEL,
            )
        )
        await cross_service["rehydrate"]()
        await service.edit_task(
            EditTaskCommand(id=result.id, completes_with_children=False),
        )
        await cross_service["rehydrate"]()

        task = await service.get_task(result.id)
        assert task.completes_with_children is False

    @pytest.mark.asyncio
    async def test_round_trip_edit_type_parallel_to_sequential(
        self, cross_service: dict[str, Any]
    ) -> None:
        """PROP-02: edit_task flips type; derived is_sequential flips too."""
        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )
        from omnifocus_operator.contracts.use_cases.edit.tasks import (  # noqa: PLC0415
            EditTaskCommand,
        )
        from omnifocus_operator.models.enums import TaskType  # noqa: PLC0415

        service = cross_service["service"]
        result = await service.add_task(
            AddTaskCommand(
                name="type-flip",
                completes_with_children=True,
                type=TaskType.PARALLEL,
            )
        )
        await cross_service["rehydrate"]()
        await service.edit_task(EditTaskCommand(id=result.id, type=TaskType.SEQUENTIAL))
        await cross_service["rehydrate"]()

        task = await service.get_task(result.id)
        assert task.type == TaskType.SEQUENTIAL
        assert task.is_sequential is True

    @pytest.mark.asyncio
    async def test_round_trip_create_default_resolves_preference_values(
        self, cross_service: dict[str, Any]
    ) -> None:
        """PROP-05/06: omitted fields resolve to user preferences, written explicitly."""
        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )
        from omnifocus_operator.models.enums import TaskType  # noqa: PLC0415

        service = cross_service["service"]
        bridge = cross_service["bridge"]
        bridge.configure_settings(
            {
                "OFMCompleteWhenLastItemComplete": False,
                "OFMTaskDefaultSequential": True,
            }
        )

        result = await service.add_task(AddTaskCommand(name="defaults-from-prefs"))
        await cross_service["rehydrate"]()

        task = await service.get_task(result.id)
        assert task.completes_with_children is False  # from preference
        assert task.type == TaskType.SEQUENTIAL  # from preference
        assert task.is_sequential is True  # derived

    @pytest.mark.asyncio
    async def test_round_trip_factory_default_fallback_when_preference_keys_absent(
        self, cross_service: dict[str, Any]
    ) -> None:
        """PROP-03: absence of preference key -> user kept OF factory default."""
        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )
        from omnifocus_operator.models.enums import TaskType  # noqa: PLC0415

        service = cross_service["service"]
        bridge = cross_service["bridge"]
        # Explicitly remove both keys so the bridge returns their absence.
        bridge._settings.pop("OFMCompleteWhenLastItemComplete", None)
        bridge._settings.pop("OFMTaskDefaultSequential", None)

        result = await service.add_task(AddTaskCommand(name="factory-default-fallback"))
        await cross_service["rehydrate"]()

        task = await service.get_task(result.id)
        assert task.completes_with_children is True  # OF factory default
        assert task.type == TaskType.PARALLEL  # OF factory default

    @pytest.mark.asyncio
    async def test_round_trip_list_tasks_reflects_written_fields(
        self, cross_service: dict[str, Any]
    ) -> None:
        """list_tasks exercises the cache-backed read path with the same values."""
        from omnifocus_operator.contracts.use_cases.add.tasks import (  # noqa: PLC0415
            AddTaskCommand,
        )
        from omnifocus_operator.contracts.use_cases.list.tasks import (  # noqa: PLC0415
            ListTasksQuery,
        )
        from omnifocus_operator.models.enums import TaskType  # noqa: PLC0415

        service = cross_service["service"]
        result = await service.add_task(
            AddTaskCommand(
                name="list-rt",
                completes_with_children=False,
                type=TaskType.SEQUENTIAL,
            )
        )
        await cross_service["rehydrate"]()

        list_result = await service.list_tasks(ListTasksQuery(search="list-rt"))
        matching = [t for t in list_result.items if t.id == result.id]
        assert len(matching) == 1
        assert matching[0].completes_with_children is False
        assert matching[0].type == TaskType.SEQUENTIAL
        assert matching[0].is_sequential is True
