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
from datetime import UTC, datetime
from typing import TYPE_CHECKING, Any

import pytest

from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery
from omnifocus_operator.models.enums import (
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
                "availability": "available",
                "flagged": True,
                "folder_id": "folder-1",
                "next_review_date": _REVIEW_SOON,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
            },
            {
                "id": "proj-2",
                "name": "Plan Vacation",
                "availability": "available",
                "flagged": False,
                "folder_id": None,
                "next_review_date": _REVIEW_FAR,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
            },
            {
                "id": "proj-3",
                "name": "Old Project",
                "availability": "blocked",
                "flagged": False,
                "folder_id": "folder-1",
                "next_review_date": _REVIEW_PAST,
                "last_review_date": _REVIEW_PAST,
                "added": _ADDED,
                "modified": _MODIFIED,
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
            },
        ],
        "perspectives": [
            {"id": None, "name": "Inbox"},
            {"id": "persp-1", "name": "Forecast"},
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
            )
        )

    # Translate projects
    bridge_projects = []
    for p in data["projects"]:
        bridge_projects.append(
            make_project_dict(
                id=p["id"],
                name=p["name"],
                flagged=p["flagged"],
                effectiveFlagged=p["flagged"],
                folder=p["folder_id"],
                status="Active" if p["availability"] in ("available", "blocked") else "Dropped",
                taskStatus=_BRIDGE_AVAILABILITY_MAP[p["availability"]],
                nextReviewDate=_dt_to_iso(p["next_review_date"]),
                lastReviewDate=_dt_to_iso(p["last_review_date"]),
                added=_dt_to_iso(p["added"]),
                modified=_dt_to_iso(p["modified"]),
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
    "completed": {"blocked": 0, "dateCompleted": _to_cf_epoch(_MODIFIED), "dateHidden": None},
    "dropped": {"blocked": 0, "dateCompleted": None, "dateHidden": _to_cf_epoch(_MODIFIED)},
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
                effectiveDateDue TEXT,
                effectiveDateToStart TEXT,
                dateCompleted REAL,
                effectiveDateCompleted REAL,
                dateHidden REAL,
                effectiveDateHidden REAL,
                datePlanned REAL,
                effectiveDatePlanned REAL,
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
                catchUpAutomatically INTEGER DEFAULT 0
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
            conn.execute(
                """INSERT INTO Task (
                    persistentIdentifier, name, dateAdded, dateModified,
                    flagged, effectiveFlagged, estimatedMinutes,
                    childrenCount, inInbox, containingProjectInfo, parent,
                    overdue, dueSoon, blocked, dateCompleted, dateHidden
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
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
                    avail_cols["dateCompleted"],
                    avail_cols["dateHidden"],
                ],
            )

        # Insert projects (Task row + ProjectInfo row)
        for p in data["projects"]:
            avail_cols = _SQLITE_TASK_AVAILABILITY[p["availability"]]
            task_id = p["id"]
            conn.execute(
                """INSERT INTO Task (
                    persistentIdentifier, name, dateAdded, dateModified,
                    flagged, effectiveFlagged, childrenCount, inInbox,
                    overdue, dueSoon, blocked, dateCompleted, dateHidden
                ) VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)""",
                [
                    task_id,
                    p["name"],
                    _to_cf_epoch(p["added"]),
                    _to_cf_epoch(p["modified"]),
                    int(p["flagged"]),
                    int(p["flagged"]),
                    0,  # childrenCount
                    0,  # inInbox
                    0,  # overdue
                    0,  # dueSoon
                    avail_cols["blocked"],
                    avail_cols["dateCompleted"],
                    avail_cols["dateHidden"],
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
    """Assert two ListRepoResult instances are equivalent (items sorted by ID)."""
    items_a = sorted(result_a.items, key=lambda x: x.id or "")
    items_b = sorted(result_b.items, key=lambda x: x.id or "")
    assert items_a == items_b
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
        # Default availability = [available, blocked] -> task-1, task-2, task-3, task-4
        assert len(items) == 4
        assert [t.id for t in items] == ["task-1", "task-2", "task-3", "task-4"]
        assert result.total == 4

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
            assert t.parent is not None
            assert t.parent.id == "proj-1"

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
        assert items[0].in_inbox is True

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
        assert result.total == 4
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
        # available + blocked -> proj-1, proj-2, proj-3
        assert len(items) == 3
        assert [p.id for p in items] == ["proj-1", "proj-2", "proj-3"]
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_list_projects_by_folder(self, cross_repo: Repository) -> None:
        """Folder filter returns only projects in that folder."""
        result = await cross_repo.list_projects(ListProjectsRepoQuery(folder_ids=["folder-1"]))
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 2
        assert [p.id for p in items] == ["proj-1", "proj-3"]
        for p in items:
            assert p.folder == "folder-1"

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
        # proj-2 has review on 2026-06-01 (after threshold)
        assert len(items) == 2
        assert [p.id for p in items] == ["proj-1", "proj-3"]


# ===========================================================================
# Tag cross-path equivalence tests
# ===========================================================================


class TestListTagsCrossPath:
    @pytest.mark.asyncio
    async def test_list_tags_default(self, cross_repo: Repository) -> None:
        """Default query returns available + blocked tags."""
        result = await cross_repo.list_tags(ListTagsRepoQuery())
        items = sorted(result.items, key=lambda x: x.id)
        # Default = [available, blocked] -> tag-1, tag-2, tag-3
        assert len(items) == 3
        assert [t.id for t in items] == ["tag-1", "tag-2", "tag-3"]
        assert result.total == 3

    @pytest.mark.asyncio
    async def test_list_tags_active_only(self, cross_repo: Repository) -> None:
        """Active-only filter returns only available tags."""
        result = await cross_repo.list_tags(
            ListTagsRepoQuery(availability=[TagAvailability.AVAILABLE])
        )
        items = sorted(result.items, key=lambda x: x.id)
        assert len(items) == 2
        assert [t.id for t in items] == ["tag-1", "tag-2"]


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
        result = await cross_repo.list_perspectives()
        items = sorted(result.items, key=lambda x: x.name)
        assert len(items) == 2
        assert result.total == 2

        # Builtin perspective (id=None)
        forecast = next(p for p in items if p.name == "Forecast")
        assert forecast.id == "persp-1"
        assert forecast.builtin is False

        inbox = next(p for p in items if p.name == "Inbox")
        assert inbox.id is None
        assert inbox.builtin is True
