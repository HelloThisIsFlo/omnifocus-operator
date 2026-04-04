"""Tests for HybridRepository -- SQLite-based OmniFocus data reader.

Uses in-memory SQLite databases written to temp files as test fixtures.
Covers all 5 entity types, two-axis status mapping, dual timestamp formats,
XML note extraction, plist perspective parsing, and connection semantics.
"""

from __future__ import annotations

import asyncio
import plistlib
import sqlite3
import time
from datetime import UTC, datetime, timedelta
from typing import TYPE_CHECKING, Any
from unittest.mock import patch
from zoneinfo import ZoneInfo

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from omnifocus_operator.contracts.protocols import Repository
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskRepoPayload, AddTaskRepoResult
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskRepoPayload
from omnifocus_operator.contracts.use_cases.list.common import ListRepoResult
from omnifocus_operator.contracts.use_cases.list.folders import ListFoldersRepoQuery
from omnifocus_operator.contracts.use_cases.list.perspectives import ListPerspectivesRepoQuery
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tags import ListTagsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery
from omnifocus_operator.models.enums import Availability, FolderAvailability, TagAvailability
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.repository.hybrid.hybrid import _FRESHNESS_TIMEOUT, HybridRepository
from tests.doubles import InMemoryBridge, StubBridge

# Core Foundation epoch: Jan 1, 2001 00:00:00 UTC
_CF_EPOCH = datetime(2001, 1, 1, tzinfo=UTC)

# A sample CF epoch float for 2026-02-20 15:15:16.902 UTC
_SAMPLE_CF_FLOAT = (
    _CF_EPOCH + timedelta(days=9182, hours=15, minutes=15, seconds=16, milliseconds=902) - _CF_EPOCH
).total_seconds()


def _cf_epoch(dt: datetime) -> float:
    """Convert a timezone-aware datetime to CF epoch float."""
    return (dt - _CF_EPOCH).total_seconds()


def _make_note_xml(text: str) -> bytes:
    """Create OmniFocus-style note XML from plain text."""
    xml = '<?xml version="1.0" encoding="UTF-8"?>'
    xml += f"<text><p><run><lit>{text}</lit></run></p></text>"
    return xml.encode()


def _make_perspective_plist(name: str) -> bytes:
    """Create a binary plist blob with a name key."""
    return plistlib.dumps({"name": name})


def create_test_db(
    tmp_path: Path,
    *,
    tasks: list[dict[str, Any]] | None = None,
    projects: list[dict[str, Any]] | None = None,
    tags: list[dict[str, Any]] | None = None,
    folders: list[dict[str, Any]] | None = None,
    perspectives: list[dict[str, Any]] | None = None,
    task_tags: list[dict[str, Any]] | None = None,
) -> Path:
    """Create a SQLite database with the OmniFocus schema and seed data.

    Returns the path to the database file.
    """
    db_path = tmp_path / "test.db"
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

        for task in tasks or []:
            cols = list(task.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            conn.execute(
                f"INSERT INTO Task ({col_names}) VALUES ({placeholders})",
                [task[c] for c in cols],
            )

        for proj in projects or []:
            # Projects need both a Task row and a ProjectInfo row.
            # The 'project_info' key contains ProjectInfo fields.
            proj_info = proj.pop("project_info", {})
            task_cols = list(proj.keys())
            placeholders = ", ".join(["?"] * len(task_cols))
            col_names = ", ".join(task_cols)
            conn.execute(
                f"INSERT INTO Task ({col_names}) VALUES ({placeholders})",
                [proj[c] for c in task_cols],
            )
            if proj_info:
                pi_cols = list(proj_info.keys())
                placeholders = ", ".join(["?"] * len(pi_cols))
                col_names = ", ".join(pi_cols)
                conn.execute(
                    f"INSERT INTO ProjectInfo ({col_names}) VALUES ({placeholders})",
                    [proj_info[c] for c in pi_cols],
                )

        for tag in tags or []:
            cols = list(tag.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            conn.execute(
                f"INSERT INTO Context ({col_names}) VALUES ({placeholders})",
                [tag[c] for c in cols],
            )

        for folder in folders or []:
            cols = list(folder.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            conn.execute(
                f"INSERT INTO Folder ({col_names}) VALUES ({placeholders})",
                [folder[c] for c in cols],
            )

        for persp in perspectives or []:
            cols = list(persp.keys())
            placeholders = ", ".join(["?"] * len(cols))
            col_names = ", ".join(cols)
            conn.execute(
                f"INSERT INTO Perspective ({col_names}) VALUES ({placeholders})",
                [persp[c] for c in cols],
            )

        for tt in task_tags or []:
            conn.execute(
                "INSERT INTO TaskToTag (task, tag) VALUES (?, ?)",
                [tt["task"], tt["tag"]],
            )

        conn.commit()
    finally:
        conn.close()

    return db_path


# --- Shared test data helpers ---

_NOW_CF = _cf_epoch(datetime(2026, 3, 7, 12, 0, 0, tzinfo=UTC))
_EARLIER_CF = _cf_epoch(datetime(2026, 3, 1, 8, 0, 0, tzinfo=UTC))


def _minimal_task(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a minimal valid task row dict with sensible defaults."""
    base: dict[str, Any] = {
        "persistentIdentifier": "task-001",
        "name": "Test Task",
        "dateAdded": _EARLIER_CF,
        "dateModified": _NOW_CF,
        "flagged": 0,
        "effectiveFlagged": 0,
        "childrenCount": 0,
        "inInbox": 0,
        "overdue": 0,
        "dueSoon": 0,
        "blocked": 0,
    }
    if overrides:
        base.update(overrides)
    return base


def _minimal_tag(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "persistentIdentifier": "tag-001",
        "name": "Test Tag",
        "dateAdded": _EARLIER_CF,
        "dateModified": _NOW_CF,
        "allowsNextAction": 1,
    }
    if overrides:
        base.update(overrides)
    return base


def _minimal_folder(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    base: dict[str, Any] = {
        "persistentIdentifier": "folder-001",
        "name": "Test Folder",
        "dateAdded": _EARLIER_CF,
        "dateModified": _NOW_CF,
    }
    if overrides:
        base.update(overrides)
    return base


def _minimal_project(overrides: dict[str, Any] | None = None) -> dict[str, Any]:
    """Return a minimal project (Task row + ProjectInfo row)."""
    task_id = (overrides or {}).get("persistentIdentifier", "proj-001")
    base: dict[str, Any] = {
        "persistentIdentifier": task_id,
        "name": "Test Project",
        "dateAdded": _EARLIER_CF,
        "dateModified": _NOW_CF,
        "flagged": 0,
        "effectiveFlagged": 0,
        "childrenCount": 0,
        "inInbox": 0,
        "overdue": 0,
        "dueSoon": 0,
        "blocked": 0,
        "project_info": {
            "pk": f"pi-{task_id}",
            "task": task_id,
            "lastReviewDate": _EARLIER_CF,
            "nextReviewDate": _NOW_CF,
            "reviewRepetitionString": "@1w",
            "effectiveStatus": "active",
        },
    }
    if overrides:
        pi_overrides = overrides.pop("project_info", None)
        base.update(overrides)
        if pi_overrides:
            base["project_info"].update(pi_overrides)
    return base


# ============================================================================
# FIXTURES
# ============================================================================


@pytest.fixture
def hybrid_db(request: pytest.FixtureRequest, tmp_path: Path) -> Path:
    """SQLite DB seeded from @pytest.mark.hybrid_db(...) marker.

    Without marker: creates an empty database (no seed data).
    With marker: passes kwargs to create_test_db().
    """
    marker = request.node.get_closest_marker("hybrid_db")
    if marker is not None:
        return create_test_db(tmp_path, **marker.kwargs)
    return create_test_db(tmp_path)


@pytest.fixture
def hybrid_repo(hybrid_db: Path) -> HybridRepository:
    """HybridRepository backed by marker-seeded DB + empty InMemoryBridge.

    Chain: @pytest.mark.hybrid_db(...) -> hybrid_db -> hybrid_repo

    The InMemoryBridge is always empty -- it's only used for write operations
    that read-focused tests don't exercise.
    """
    return HybridRepository(db_path=hybrid_db, bridge=InMemoryBridge())


# ============================================================================
# TESTS
# ============================================================================


class TestProtocol:
    def test_satisfies_repository_protocol(self, hybrid_repo: HybridRepository) -> None:
        assert isinstance(hybrid_repo, Repository)


class TestReadAllEntities:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task()],
        projects=[_minimal_project()],
        tags=[_minimal_tag()],
        folders=[_minimal_folder()],
        perspectives=[
            {
                "persistentIdentifier": "persp-001",
                "valueData": _make_perspective_plist("Forecast"),
            }
        ],
    )
    async def test_read_all_entities(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert isinstance(result, AllEntities)
        assert len(result.tasks) == 1
        assert len(result.projects) == 1
        assert len(result.tags) == 1
        assert len(result.folders) == 1
        assert len(result.perspectives) == 1


class TestConnectionSemantics:
    def test_read_only_connection(self, hybrid_repo: HybridRepository) -> None:
        """Verify that the connection string contains ?mode=ro."""
        # Inspect the connection URI by calling _read_all and checking the path usage
        # We'll monkeypatch sqlite3.connect to capture the URI
        calls: list[str] = []
        original_connect = sqlite3.connect

        def capturing_connect(uri_str: str, **kwargs: Any) -> Any:
            calls.append(uri_str)
            return original_connect(uri_str, **kwargs)

        with patch("sqlite3.connect", side_effect=capturing_connect):
            hybrid_repo._read_all()

        assert len(calls) == 1
        assert "?mode=ro" in calls[0]

    @pytest.mark.asyncio
    async def test_fresh_connection_per_read(self, hybrid_repo: HybridRepository) -> None:
        """Two consecutive get_all() calls create two separate connections."""
        call_count = 0
        original_connect = sqlite3.connect

        def counting_connect(uri_str: str, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return original_connect(uri_str, **kwargs)

        with patch("sqlite3.connect", side_effect=counting_connect):
            await hybrid_repo.get_all()
            await hybrid_repo.get_all()

        assert call_count == 2


class TestTaskBasicFields:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "abc123",
                    "name": "Buy milk",
                    "plainTextNote": "Remember oat milk",
                    "flagged": 1,
                    "effectiveFlagged": 1,
                    "inInbox": 1,
                    "childrenCount": 3,
                }
            )
        ],
    )
    async def test_task_basic_fields(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.id == "abc123"
        assert task.name == "Buy milk"
        assert task.url == "omnifocus:///task/abc123"
        assert task.note == "Remember oat milk"
        assert task.flagged is True
        assert task.effective_flagged is True
        assert task.in_inbox is True
        assert task.has_children is True
        assert task.added is not None
        assert task.modified is not None


class TestTaskTimestamps:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "dateDue": "2026-02-20T15:15:16.000",
                    "dateToStart": "2026-02-20T15:15:16.000",
                }
            )
        ],
    )
    async def test_task_dates_local_time_string(self, hybrid_repo: HybridRepository) -> None:
        """dateDue/dateToStart as local-time ISO strings parse correctly."""
        # Use UTC timezone so local time == UTC for predictable assertions
        with patch(
            "omnifocus_operator.repository.hybrid.hybrid._LOCAL_TZ",
            ZoneInfo("UTC"),
        ):
            result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.year == 2026
        assert task.due_date.month == 2
        assert task.due_date.day == 20
        assert task.defer_date is not None
        assert task.defer_date.year == 2026

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "effectiveDateDue": _cf_epoch(datetime(2026, 2, 16, 22, 0, 0, tzinfo=UTC)),
                    "effectiveDateToStart": _cf_epoch(datetime(2026, 2, 16, 22, 0, 0, tzinfo=UTC)),
                }
            )
        ],
    )
    async def test_effective_dates_cf_epoch(self, hybrid_repo: HybridRepository) -> None:
        """effectiveDateDue/effectiveDateToStart as CF epoch floats parse correctly."""
        result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.effective_due_date is not None
        assert task.effective_due_date.year == 2026
        assert task.effective_due_date.month == 2
        assert task.effective_due_date.day == 16
        assert task.effective_defer_date is not None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_task_null_dates(self, hybrid_repo: HybridRepository) -> None:
        """NULL date columns produce None fields."""
        result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.due_date is None
        assert task.defer_date is None
        assert task.completion_date is None
        assert task.drop_date is None
        assert task.planned_date is None


class TestTaskStatus:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task({"overdue": 1, "dueSoon": 0})])
    async def test_task_urgency_overdue(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].urgency == "overdue"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task({"overdue": 0, "dueSoon": 1})])
    async def test_task_urgency_due_soon(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].urgency == "due_soon"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task({"overdue": 0, "dueSoon": 0})])
    async def test_task_urgency_none(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].urgency == "none"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task({"overdue": 1, "dueSoon": 1})])
    async def test_task_urgency_overdue_priority(self, hybrid_repo: HybridRepository) -> None:
        """Overdue takes priority over due_soon."""
        result = await hybrid_repo.get_all()
        assert result.tasks[0].urgency == "overdue"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task({"dateHidden": _NOW_CF})])
    async def test_task_availability_dropped(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].availability == "dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task({"dateCompleted": _NOW_CF})])
    async def test_task_availability_completed(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].availability == "completed"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task({"blocked": 1})])
    async def test_task_availability_blocked(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].availability == "blocked"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_task_availability_available(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].availability == "available"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"effectiveDateCompleted": _NOW_CF})]
    )
    async def test_task_availability_completed_by_effective(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Task with effectiveDateCompleted (no own dateCompleted) maps to completed."""
        result = await hybrid_repo.get_all()
        assert result.tasks[0].availability == "completed"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"effectiveDateHidden": _NOW_CF})]
    )
    async def test_task_availability_dropped_by_effective(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Task with effectiveDateHidden (no own dateHidden) maps to dropped."""
        result = await hybrid_repo.get_all()
        assert result.tasks[0].availability == "dropped"


class TestTaskTags:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"persistentIdentifier": "t1"})],
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-a", "name": "Errand"}),
            _minimal_tag({"persistentIdentifier": "tag-b", "name": "Home"}),
        ],
        task_tags=[
            {"task": "t1", "tag": "tag-a"},
            {"task": "t1", "tag": "tag-b"},
        ],
    )
    async def test_task_tags_via_join(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        task = result.tasks[0]
        assert len(task.tags) == 2
        tag_names = {t.name for t in task.tags}
        assert tag_names == {"Errand", "Home"}
        tag_ids = {t.id for t in task.tags}
        assert tag_ids == {"tag-a", "tag-b"}


class TestTaskRepetition:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "repetitionRuleString": "FREQ=WEEKLY;INTERVAL=1",
                    "repetitionScheduleTypeString": "fixed",
                    "repetitionAnchorDateKey": "dateDue",
                    "catchUpAutomatically": 1,
                }
            )
        ],
    )
    async def test_task_repetition_rule(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        task = result.tasks[0]
        assert task.repetition_rule is not None
        assert task.repetition_rule.frequency.type == "weekly"
        assert task.repetition_rule.schedule == "regularly_with_catch_up"
        assert task.repetition_rule.based_on == "due_date"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_task_no_repetition_rule(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].repetition_rule is None


class TestTaskNotes:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "plainTextNote": "Buy oat milk and eggs",
                }
            )
        ],
    )
    async def test_task_note_plain_text(self, hybrid_repo: HybridRepository) -> None:
        """Notes are read from plainTextNote column (not noteXMLData)."""
        result = await hybrid_repo.get_all()
        assert result.tasks[0].note == "Buy oat milk and eggs"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_task_note_null(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks[0].note == ""


class TestTaskRelationships:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_inbox_task_parent_null(self, hybrid_repo: HybridRepository) -> None:
        """Task with no project and no parent has parent=None."""
        result = await hybrid_repo.get_all()
        task = result.tasks[0]
        assert task.parent is None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "containingProjectInfo": "pi-proj-001",
                }
            )
        ],
        projects=[_minimal_project()],
    )
    async def test_task_in_project_parent_ref(self, hybrid_repo: HybridRepository) -> None:
        """Task in a project gets parent={type:'project', id, name}."""
        result = await hybrid_repo.get_all()
        task = result.tasks[0]
        assert task.parent is not None
        assert task.parent.type == "project"
        assert task.parent.id == "proj-001"
        assert task.parent.name == "Test Project"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "subtask-001",
                    "name": "Subtask",
                    "parent": "parent-task-001",
                    "containingProjectInfo": "pi-proj-001",
                }
            ),
            _minimal_task(
                {
                    "persistentIdentifier": "parent-task-001",
                    "name": "Parent Task",
                    "containingProjectInfo": "pi-proj-001",
                }
            ),
        ],
        projects=[_minimal_project()],
    )
    async def test_subtask_parent_ref(self, hybrid_repo: HybridRepository) -> None:
        """Subtask gets parent={type:'task', id, name} using parent task."""
        result = await hybrid_repo.get_all()
        subtask = next(t for t in result.tasks if t.id == "subtask-001")
        assert subtask.parent is not None
        assert subtask.parent.type == "task"
        assert subtask.parent.id == "parent-task-001"
        assert subtask.parent.name == "Parent Task"


class TestProjectFields:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "proj-abc",
                    "name": "My Project",
                    "project_info": {
                        "pk": "pi-proj-abc",
                        "task": "proj-abc",
                        "lastReviewDate": _EARLIER_CF,
                        "nextReviewDate": _NOW_CF,
                        "reviewRepetitionString": "@1w",
                        "nextTask": "next-t1",
                        "folder": "folder-001",
                        "effectiveStatus": "active",
                    },
                }
            )
        ],
    )
    async def test_project_fields(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        proj = result.projects[0]
        assert proj.id == "proj-abc"
        assert proj.name == "My Project"
        assert proj.url == "omnifocus:///project/proj-abc"
        assert proj.last_review_date is not None
        assert proj.next_review_date is not None
        assert proj.review_interval.steps == 1
        assert proj.review_interval.unit == "weeks"
        assert proj.next_task == "next-t1"
        assert proj.folder == "folder-001"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "project_info": {"effectiveStatus": "dropped"},
                }
            )
        ],
    )
    async def test_project_availability_dropped_by_status(
        self, hybrid_repo: HybridRepository
    ) -> None:
        result = await hybrid_repo.get_all()
        assert result.projects[0].availability == "dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(projects=[_minimal_project({"dateHidden": _NOW_CF})])
    async def test_project_availability_dropped_by_date_hidden(
        self, hybrid_repo: HybridRepository
    ) -> None:
        result = await hybrid_repo.get_all()
        assert result.projects[0].availability == "dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(projects=[_minimal_project({"dateCompleted": _NOW_CF})])
    async def test_project_availability_completed(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.projects[0].availability == "completed"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "project_info": {"effectiveStatus": "inactive"},
                }
            )
        ],
    )
    async def test_project_availability_blocked(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.projects[0].availability == "blocked"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(projects=[_minimal_project()])
    async def test_project_availability_available(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.projects[0].availability == "available"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[_minimal_project({"effectiveDateCompleted": _NOW_CF})]
    )
    async def test_project_availability_completed_by_effective(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Project with effectiveDateCompleted (no own dateCompleted) maps to completed."""
        result = await hybrid_repo.get_all()
        assert result.projects[0].availability == "completed"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[_minimal_project({"effectiveDateHidden": _NOW_CF})]
    )
    async def test_project_availability_dropped_by_effective(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Project with effectiveDateHidden (no own dateHidden) maps to dropped."""
        result = await hybrid_repo.get_all()
        assert result.projects[0].availability == "dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "project_info": {"reviewRepetitionString": "@1w"},
                }
            )
        ],
    )
    async def test_project_review_interval_weekly(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.projects[0].review_interval.steps == 1
        assert result.projects[0].review_interval.unit == "weeks"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "project_info": {"reviewRepetitionString": "~2m"},
                }
            )
        ],
    )
    async def test_project_review_interval_monthly(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.projects[0].review_interval.steps == 2
        assert result.projects[0].review_interval.unit == "months"


class TestTagFields:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tags=[
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-xyz",
                    "name": "Errands",
                    "childrenAreMutuallyExclusive": 1,
                    "parent": "tag-parent",
                }
            )
        ],
    )
    async def test_tag_fields(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        tag = result.tags[0]
        assert tag.id == "tag-xyz"
        assert tag.name == "Errands"
        assert tag.url == "omnifocus:///tag/tag-xyz"
        assert tag.children_are_mutually_exclusive is True
        assert tag.parent == "tag-parent"
        assert tag.added is not None
        assert tag.modified is not None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tags=[_minimal_tag({"allowsNextAction": 0})])
    async def test_tag_availability_blocked(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tags[0].availability == "blocked"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tags=[_minimal_tag({"dateHidden": _NOW_CF})])
    async def test_tag_availability_dropped(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tags[0].availability == "dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tags=[_minimal_tag()])
    async def test_tag_availability_available(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tags[0].availability == "available"


class TestFolderFields:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        folders=[
            _minimal_folder(
                {
                    "persistentIdentifier": "fold-1",
                    "name": "Work",
                    "parent": "fold-parent",
                }
            )
        ],
    )
    async def test_folder_fields(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        folder = result.folders[0]
        assert folder.id == "fold-1"
        assert folder.name == "Work"
        assert folder.url == "omnifocus:///folder/fold-1"
        assert folder.parent == "fold-parent"
        assert folder.added is not None
        assert folder.modified is not None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(folders=[_minimal_folder({"dateHidden": _NOW_CF})])
    async def test_folder_availability_dropped(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.folders[0].availability == "dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(folders=[_minimal_folder()])
    async def test_folder_availability_available(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.folders[0].availability == "available"


class TestPerspective:
    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        perspectives=[
            {
                "persistentIdentifier": "persp-custom",
                "valueData": _make_perspective_plist("My Custom View"),
            }
        ],
    )
    async def test_perspective_from_plist(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        persp = result.perspectives[0]
        assert persp.id == "persp-custom"
        assert persp.name == "My Custom View"
        assert persp.builtin is False

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        perspectives=[
            {
                "persistentIdentifier": None,
                "valueData": _make_perspective_plist("Inbox"),
            }
        ],
    )
    async def test_perspective_builtin_detection(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        persp = result.perspectives[0]
        assert persp.id is None
        assert persp.builtin is True


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_database(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_all()
        assert result.tasks == []
        assert result.projects == []
        assert result.tags == []
        assert result.folders == []
        assert result.perspectives == []

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task()],
        tags=[_minimal_tag()],
    )
    async def test_reads_without_omnifocus(self, hybrid_repo: HybridRepository) -> None:
        """Reading from a file-based SQLite works without OmniFocus process."""
        # The point: no OmniFocus dependency, just a SQLite file.
        result = await hybrid_repo.get_all()
        assert len(result.tasks) == 1
        assert len(result.tags) == 1


class TestFreshness:
    """Tests for write-through WAL freshness -- writes block until SQLite confirms."""

    @pytest.mark.asyncio
    async def test_freshness_wal_polling(self, tmp_path: Path) -> None:
        """Write method polls WAL mtime; completes when mtime changes."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        bridge = StubBridge(data={"id": "task-001", "name": "Edited"})
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        # Schedule a WAL mtime change after a short delay
        async def modify_wal() -> None:
            await asyncio.sleep(0.15)
            wal_path.write_bytes(b"changed")

        task = asyncio.create_task(modify_wal())
        # edit_task should poll and detect the change
        result = await repo.edit_task(EditTaskRepoPayload(id="task-001", name="Edited"))
        await task
        assert result.id == "task-001"

    @pytest.mark.asyncio
    async def test_freshness_db_fallback(self, tmp_path: Path) -> None:
        """When WAL file does not exist, freshness uses main .db file mtime."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        # Ensure no WAL file
        wal_path = db_path.parent / (db_path.name + "-wal")
        if wal_path.exists():
            wal_path.unlink()

        bridge = StubBridge(data={"id": "task-001", "name": "Edited"})
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        # Modify DB file mtime after short delay
        async def modify_db() -> None:
            await asyncio.sleep(0.15)
            db_path.write_bytes(db_path.read_bytes() + b"\x00")

        task = asyncio.create_task(modify_db())
        result = await repo.edit_task(EditTaskRepoPayload(id="task-001", name="Edited"))
        await task
        assert result.id == "task-001"

    @pytest.mark.asyncio
    async def test_freshness_timeout(self, tmp_path: Path) -> None:
        """Write without WAL change times out after ~2s and returns anyway."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        bridge = StubBridge(data={"id": "task-001", "name": "Edited"})
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        # Don't modify WAL -- should timeout and return result anyway
        start = time.monotonic()
        result = await repo.edit_task(EditTaskRepoPayload(id="task-001", name="Edited"))
        elapsed = time.monotonic() - start

        assert elapsed >= _FRESHNESS_TIMEOUT * 0.75
        assert elapsed < _FRESHNESS_TIMEOUT * 1.5
        assert result.id == "task-001"

    @pytest.mark.asyncio
    async def test_freshness_no_timeout_when_wal_changes_during_bridge_call(
        self, tmp_path: Path
    ) -> None:
        """edit_task() captures baseline BEFORE bridge call, so WAL changes are detected.

        The decorator captures mtime before send_command(), so if OmniFocus
        flushes the WAL during the bridge call, _wait_for_fresh_data() sees
        the change immediately and returns fast.
        """
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = str(db_path) + "-wal"
        bridge = StubBridge(data={"id": "task-001", "name": "Edited"}, wal_path=wal_path)
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        start = time.monotonic()
        await repo.edit_task(EditTaskRepoPayload(id="task-001", name="Edited"))
        elapsed = time.monotonic() - start

        assert elapsed < _FRESHNESS_TIMEOUT * 0.25, (
            f"Expected fast return (WAL changed during bridge call), but took {elapsed:.1f}s "
            f"(likely hit the {_FRESHNESS_TIMEOUT}s timeout due to race condition)"
        )

    @pytest.mark.asyncio
    async def test_freshness_poll_interval(self, tmp_path: Path) -> None:
        """Polling during write occurs at ~50ms intervals."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        bridge = StubBridge(data={"id": "task-001", "name": "Edited"})
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        sleep_calls: list[float] = []
        original_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            sleep_calls.append(duration)
            await original_sleep(duration)

        # Modify WAL after a few polls
        async def modify_wal() -> None:
            await original_sleep(0.2)
            wal_path.write_bytes(b"changed")

        task = asyncio.create_task(modify_wal())
        with patch(
            "omnifocus_operator.repository.hybrid.hybrid.asyncio.sleep", side_effect=tracking_sleep
        ):
            await repo.edit_task(EditTaskRepoPayload(id="task-001", name="Edited"))
        await task

        # All sleep calls should be 0.05 (50ms)
        assert len(sleep_calls) > 0
        for call in sleep_calls:
            assert call == pytest.approx(0.05)

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_reads_never_poll(self, hybrid_repo: HybridRepository) -> None:
        """Read methods never trigger freshness polling."""
        sleep_calls: list[float] = []
        original_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            sleep_calls.append(duration)
            await original_sleep(duration)

        with patch(
            "omnifocus_operator.repository.hybrid.hybrid.asyncio.sleep", side_effect=tracking_sleep
        ):
            await hybrid_repo.get_all()
            await hybrid_repo.get_task("task-001")

        assert len(sleep_calls) == 0

    @pytest.mark.asyncio
    async def test_write_through_add_task(self, tmp_path: Path) -> None:
        """add_task blocks until WAL confirms write."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        bridge = StubBridge(data={"id": "new-1", "name": "Test"})
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        async def modify_wal() -> None:
            await asyncio.sleep(0.15)
            wal_path.write_bytes(b"changed")

        task = asyncio.create_task(modify_wal())
        result = await repo.add_task(AddTaskRepoPayload(name="Test"))
        await task
        assert result.id == "new-1"

    @pytest.mark.asyncio
    @pytest.mark.parametrize(
        ("method", "arg"),
        [
            pytest.param("add_task", AddTaskRepoPayload(name="Test"), id="add_task"),
            pytest.param(
                "edit_task", EditTaskRepoPayload(id="task-001", name="Edited"), id="edit_task"
            ),
        ],
    )
    async def test_both_write_methods_poll_wal(
        self,
        tmp_path: Path,
        method: str,
        arg: Any,
    ) -> None:
        """Both add_task and edit_task trigger WAL polling."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        bridge = StubBridge(data={"id": "task-001", "name": "Test"})
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        sleep_called = False
        original_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            nonlocal sleep_called
            sleep_called = True
            # Modify WAL to unblock the poll immediately
            wal_path.write_bytes(b"changed")
            await original_sleep(duration)

        with patch(
            "omnifocus_operator.repository.hybrid.hybrid.asyncio.sleep", side_effect=tracking_sleep
        ):
            await getattr(repo, method)(arg)

        assert sleep_called, f"{method} did not trigger WAL polling"


class TestAddTask:
    """Tests for HybridRepository.add_task -- write-through-bridge."""

    @pytest.mark.asyncio
    async def test_add_task_calls_bridge(self, tmp_path: Path) -> None:
        """add_task sends add_task command to bridge with correct payload."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = str(db_path) + "-wal"
        bridge = StubBridge(data={"id": "new-task-1", "name": "Buy milk"}, wal_path=wal_path)
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        payload = AddTaskRepoPayload(name="Buy milk")
        await repo.add_task(payload)

        assert bridge.call_count == 1
        call = bridge.calls[0]
        assert call.operation == "add_task"
        assert call.params["name"] == "Buy milk"

    @pytest.mark.asyncio
    async def test_add_task_returns_result(self, tmp_path: Path) -> None:
        """add_task returns AddTaskRepoResult with bridge response data."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = str(db_path) + "-wal"
        bridge = StubBridge(data={"id": "new-task-1", "name": "Buy milk"}, wal_path=wal_path)
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        payload = AddTaskRepoPayload(name="Buy milk")
        result = await repo.add_task(payload)

        assert isinstance(result, AddTaskRepoResult)
        assert result.id == "new-task-1"
        assert result.name == "Buy milk"

    @pytest.mark.asyncio
    async def test_add_task_only_sends_populated_fields(self, tmp_path: Path) -> None:
        """add_task only sends populated fields in payload."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = str(db_path) + "-wal"
        bridge = StubBridge(data={"id": "t1", "name": "Test"}, wal_path=wal_path)
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        payload = AddTaskRepoPayload(name="Test")
        await repo.add_task(payload)

        params = bridge.calls[0].params
        assert "name" in params
        # None fields should not be in payload
        assert "dueDate" not in params
        assert "deferDate" not in params
        assert "parent" not in params

    @pytest.mark.asyncio
    async def test_add_task_with_tag_ids(self, tmp_path: Path) -> None:
        """add_task includes tagIds in payload when tag_ids provided."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = str(db_path) + "-wal"
        bridge = StubBridge(data={"id": "t1", "name": "Test"}, wal_path=wal_path)
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        payload = AddTaskRepoPayload(name="Test", tag_ids=["tag-001", "tag-002"])
        await repo.add_task(payload)

        params = bridge.calls[0].params
        assert params["tagIds"] == ["tag-001", "tag-002"]

    @pytest.mark.asyncio
    async def test_add_task_uses_camel_case_keys(self, tmp_path: Path) -> None:
        """add_task payload uses camelCase keys for bridge protocol."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = str(db_path) + "-wal"
        bridge = StubBridge(data={"id": "t1", "name": "Test"}, wal_path=wal_path)
        repo = HybridRepository(db_path=db_path, bridge=bridge)

        payload = AddTaskRepoPayload(
            name="Test",
            due_date="2026-03-15T10:00:00+00:00",
            estimated_minutes=30.0,
        )
        await repo.add_task(payload)

        params = bridge.calls[0].params
        assert "dueDate" in params
        assert "estimatedMinutes" in params
        # Should NOT have snake_case keys
        assert "due_date" not in params
        assert "estimated_minutes" not in params

    def test_protocol_has_add_task(self) -> None:
        """Repository protocol defines add_task method."""
        assert hasattr(Repository, "add_task")

    def test_temporary_simulate_write_removed(self, tmp_path: Path) -> None:
        """TEMPORARY_simulate_write is removed from HybridRepository."""
        assert not hasattr(HybridRepository, "TEMPORARY_simulate_write")


# ============================================================================
# GET-BY-ID TESTS
# ============================================================================


class TestGetTask:
    """Tests for HybridRepository.get_task() -- single task lookup by ID."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "task-abc",
                    "name": "Buy milk",
                    "plainTextNote": "Oat milk",
                    "flagged": 1,
                    "effectiveFlagged": 1,
                    "inInbox": 0,
                    "childrenCount": 2,
                    "overdue": 1,
                }
            )
        ],
        projects=[_minimal_project()],
    )
    async def test_found_returns_task_with_all_fields(self, hybrid_repo: HybridRepository) -> None:
        """Found task returns a complete Task model with all fields populated."""
        task = await hybrid_repo.get_task("task-abc")

        assert task is not None
        assert task.id == "task-abc"
        assert task.name == "Buy milk"
        assert task.note == "Oat milk"
        assert task.flagged is True
        assert task.effective_flagged is True
        assert task.has_children is True
        assert task.urgency == "overdue"
        assert task.availability == "available"
        assert task.added is not None
        assert task.modified is not None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_not_found_returns_none(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_task("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "task-in-proj",
                    "containingProjectInfo": "pi-proj-001",
                }
            )
        ],
        projects=[_minimal_project()],
    )
    async def test_task_with_project_parent_ref(self, hybrid_repo: HybridRepository) -> None:
        """Task in a project gets ParentRef with type='project'."""
        task = await hybrid_repo.get_task("task-in-proj")

        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "project"
        assert task.parent.id == "proj-001"
        assert task.parent.name == "Test Project"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "subtask-1",
                    "name": "Subtask",
                    "parent": "parent-task-1",
                    "containingProjectInfo": "pi-proj-001",
                }
            ),
            _minimal_task(
                {
                    "persistentIdentifier": "parent-task-1",
                    "name": "Parent Task",
                    "containingProjectInfo": "pi-proj-001",
                }
            ),
        ],
        projects=[_minimal_project()],
    )
    async def test_task_with_task_parent_ref(self, hybrid_repo: HybridRepository) -> None:
        """Subtask gets ParentRef with type='task'."""
        task = await hybrid_repo.get_task("subtask-1")

        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "task"
        assert task.parent.id == "parent-task-1"
        assert task.parent.name == "Parent Task"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"persistentIdentifier": "inbox-task", "inInbox": 1})],
    )
    async def test_inbox_task_parent_none(self, hybrid_repo: HybridRepository) -> None:
        """Inbox task (no project, no parent) has parent=None."""
        task = await hybrid_repo.get_task("inbox-task")

        assert task is not None
        assert task.parent is None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"persistentIdentifier": "tagged-task"})],
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-a", "name": "Errand"}),
            _minimal_tag({"persistentIdentifier": "tag-b", "name": "Home"}),
        ],
        task_tags=[
            {"task": "tagged-task", "tag": "tag-a"},
            {"task": "tagged-task", "tag": "tag-b"},
        ],
    )
    async def test_task_with_tags(self, hybrid_repo: HybridRepository) -> None:
        """Task tags are included in get_task result."""
        task = await hybrid_repo.get_task("tagged-task")

        assert task is not None
        assert len(task.tags) == 2
        tag_names = {t.name for t in task.tags}
        assert tag_names == {"Errand", "Home"}

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[_minimal_project({"persistentIdentifier": "proj-as-task"})],
    )
    async def test_does_not_return_project_as_task(self, hybrid_repo: HybridRepository) -> None:
        """A project's task row is excluded from get_task (has ProjectInfo)."""
        result = await hybrid_repo.get_task("proj-as-task")
        assert result is None


class TestGetProject:
    """Tests for HybridRepository.get_project() -- single project lookup by ID."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "proj-xyz",
                    "name": "My Project",
                    "project_info": {
                        "pk": "pi-proj-xyz",
                        "task": "proj-xyz",
                        "lastReviewDate": _EARLIER_CF,
                        "nextReviewDate": _NOW_CF,
                        "reviewRepetitionString": "@2w",
                        "nextTask": "next-1",
                        "folder": "fold-1",
                        "effectiveStatus": "active",
                    },
                }
            )
        ],
    )
    async def test_found_returns_project_with_all_fields(
        self, hybrid_repo: HybridRepository
    ) -> None:
        proj = await hybrid_repo.get_project("proj-xyz")

        assert proj is not None
        assert proj.id == "proj-xyz"
        assert proj.name == "My Project"
        assert proj.url == "omnifocus:///project/proj-xyz"
        assert proj.review_interval.steps == 2
        assert proj.review_interval.unit == "weeks"
        assert proj.next_task == "next-1"
        assert proj.folder == "fold-1"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(projects=[_minimal_project()])
    async def test_not_found_returns_none(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_project("nonexistent-id")
        assert result is None


class TestGetTag:
    """Tests for HybridRepository.get_tag() -- single tag lookup by ID."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tags=[
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-xyz",
                    "name": "Errands",
                    "childrenAreMutuallyExclusive": 1,
                    "parent": "tag-parent",
                }
            )
        ],
    )
    async def test_found_returns_tag_with_all_fields(self, hybrid_repo: HybridRepository) -> None:
        tag = await hybrid_repo.get_tag("tag-xyz")

        assert tag is not None
        assert tag.id == "tag-xyz"
        assert tag.name == "Errands"
        assert tag.url == "omnifocus:///tag/tag-xyz"
        assert tag.children_are_mutually_exclusive is True
        assert tag.parent == "tag-parent"
        assert tag.added is not None
        assert tag.modified is not None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tags=[_minimal_tag()])
    async def test_not_found_returns_none(self, hybrid_repo: HybridRepository) -> None:
        result = await hybrid_repo.get_tag("nonexistent-id")
        assert result is None


# ============================================================================
# GAP CLOSURE: Note encoding via plainTextNote
# ============================================================================


class TestPlainTextNoteEncoding:
    """Notes should be read from plainTextNote column, not noteXMLData."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "plainTextNote": "Remember oat milk\nAnd eggs",
                }
            )
        ],
    )
    async def test_task_reads_plain_text_note(self, hybrid_repo: HybridRepository) -> None:
        """Task with plainTextNote reads as clean text (no XML artifacts).

        Crucially, noteXMLData is NOT set -- proves we read from plainTextNote.
        """
        result = await hybrid_repo.get_all()
        assert result.tasks[0].note == "Remember oat milk\nAnd eggs"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(tasks=[_minimal_task()])
    async def test_task_null_plain_text_note(self, hybrid_repo: HybridRepository) -> None:
        """Task with NULL plainTextNote reads as empty string."""
        result = await hybrid_repo.get_all()
        assert result.tasks[0].note == ""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "plainTextNote": "Project notes here",
                }
            )
        ],
    )
    async def test_project_reads_plain_text_note(self, hybrid_repo: HybridRepository) -> None:
        """Project with plainTextNote reads as clean text."""
        result = await hybrid_repo.get_all()
        assert result.projects[0].note == "Project notes here"


# ============================================================================
# GAP CLOSURE: Local datetime parsing (DST-aware)
# ============================================================================


class TestLocalDatetimeParsing:
    """dateDue, dateToStart, datePlanned should be parsed as local time with DST."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "dateDue": "2026-01-15T10:00:00.000",
                }
            )
        ],
    )
    async def test_due_date_local_time_winter(self, hybrid_repo: HybridRepository) -> None:
        """dateDue as local-time ISO string in winter converts to UTC correctly."""
        # London winter: UTC+0, so local 10:00 = UTC 10:00
        with patch(
            "omnifocus_operator.repository.hybrid.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.year == 2026
        assert task.due_date.month == 1
        assert task.due_date.day == 15
        assert task.due_date.hour == 10  # UTC+0 in winter
        assert task.due_date.minute == 0

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "dateDue": "2026-07-15T10:00:00.000",
                }
            )
        ],
    )
    async def test_due_date_local_time_summer_dst(self, hybrid_repo: HybridRepository) -> None:
        """dateDue as local-time ISO string in summer (BST) converts to UTC correctly."""
        # London summer (BST): UTC+1, so local 10:00 = UTC 09:00
        with patch(
            "omnifocus_operator.repository.hybrid.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.hour == 9  # BST is UTC+1, so 10:00 BST = 09:00 UTC

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "dateToStart": "2026-07-15T14:00:00.000",
                }
            )
        ],
    )
    async def test_defer_date_local_time(self, hybrid_repo: HybridRepository) -> None:
        """dateToStart stored as local-time ISO text converts to UTC correctly."""
        with patch(
            "omnifocus_operator.repository.hybrid.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.defer_date is not None
        assert task.defer_date.hour == 13  # 14:00 BST = 13:00 UTC

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "datePlanned": "2026-01-20T08:00:00.000",
                }
            )
        ],
    )
    async def test_planned_date_local_time(self, hybrid_repo: HybridRepository) -> None:
        """datePlanned stored as local-time ISO text converts to UTC correctly."""
        with patch(
            "omnifocus_operator.repository.hybrid.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.planned_date is not None
        assert task.planned_date.hour == 8  # UTC+0 in winter
        assert task.planned_date.day == 20

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "effectiveDateDue": _cf_epoch(datetime(2026, 2, 20, 15, 0, 0, tzinfo=UTC)),
                    "effectiveDateToStart": _cf_epoch(datetime(2026, 2, 20, 15, 0, 0, tzinfo=UTC)),
                }
            )
        ],
    )
    async def test_effective_dates_still_use_cf_epoch(self, hybrid_repo: HybridRepository) -> None:
        """effectiveDateDue stored as CF epoch integer still parses correctly (regression)."""
        result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.effective_due_date is not None
        assert task.effective_due_date.year == 2026
        assert task.effective_due_date.month == 2
        assert task.effective_due_date.day == 20
        assert task.effective_due_date.hour == 15
        assert task.effective_defer_date is not None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "dateAdded": _cf_epoch(datetime(2026, 3, 1, 12, 30, 0, tzinfo=UTC)),
                    "dateModified": _cf_epoch(datetime(2026, 3, 1, 12, 30, 0, tzinfo=UTC)),
                }
            )
        ],
    )
    async def test_date_added_modified_cf_epoch_regression(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """dateAdded/dateModified as CF epoch float still parse correctly (regression)."""
        result = await hybrid_repo.get_all()
        task = result.tasks[0]

        assert task.added is not None
        assert task.added.year == 2026
        assert task.added.month == 3
        assert task.added.day == 1
        assert task.added.hour == 12
        assert task.modified is not None
        assert task.modified.hour == 12


# ============================================================================
# LIST TASKS / LIST PROJECTS TESTS (Task 1 - basic method existence + behavior)
# ============================================================================


class TestListTasksBasic:
    """Basic tests proving list_tasks exists and works on HybridRepository."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-avail", "blocked": 0}),
            _minimal_task({"persistentIdentifier": "t-blocked", "blocked": 1}),
            _minimal_task({"persistentIdentifier": "t-completed", "dateCompleted": _NOW_CF}),
        ],
    )
    async def test_list_tasks_default_excludes_completed(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Default query returns available + blocked, excludes completed."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery())
        assert isinstance(result, ListRepoResult)
        assert result.total == 2
        ids = {t.id for t in result.items}
        assert "t-avail" in ids
        assert "t-blocked" in ids
        assert "t-completed" not in ids

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-flag", "flagged": 1}),
            _minimal_task({"persistentIdentifier": "t-noflag", "flagged": 0}),
        ],
    )
    async def test_list_tasks_flagged_filter(self, hybrid_repo: HybridRepository) -> None:
        """Flagged filter returns only flagged tasks."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(flagged=True))
        assert result.total == 1
        assert result.items[0].id == "t-flag"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t1"}),
            _minimal_task({"persistentIdentifier": "t2"}),
            _minimal_task({"persistentIdentifier": "t3"}),
        ],
    )
    async def test_list_tasks_pagination(self, hybrid_repo: HybridRepository) -> None:
        """Pagination with limit returns correct has_more and total."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(limit=2))
        assert len(result.items) == 2
        assert result.total == 3
        assert result.has_more is True


class TestListProjectsBasic:
    """Basic tests proving list_projects exists and works on HybridRepository."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {"persistentIdentifier": "p-active", "project_info": {"effectiveStatus": "active"}}
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "p-dropped",
                    "project_info": {"effectiveStatus": "dropped"},
                }
            ),
        ],
    )
    async def test_list_projects_default_remaining(self, hybrid_repo: HybridRepository) -> None:
        """Default query returns remaining (available + blocked), excludes dropped."""
        result = await hybrid_repo.list_projects(ListProjectsRepoQuery())
        assert isinstance(result, ListRepoResult)
        assert result.total == 1
        assert result.items[0].id == "p-active"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project({"persistentIdentifier": "p-flag", "flagged": 1}),
            _minimal_project({"persistentIdentifier": "p-noflag", "flagged": 0}),
        ],
    )
    async def test_list_projects_flagged_filter(self, hybrid_repo: HybridRepository) -> None:
        """Flagged filter returns only flagged projects."""
        result = await hybrid_repo.list_projects(ListProjectsRepoQuery(flagged=True))
        assert result.total == 1
        assert result.items[0].id == "p-flag"


# ============================================================================
# COMPREHENSIVE LIST TESTS (Task 2)
# ============================================================================


class TestListTasks:
    """Comprehensive tests for list_tasks filters, pagination, and edge cases."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-avail", "blocked": 0}),
            _minimal_task({"persistentIdentifier": "t-blocked", "blocked": 1}),
            _minimal_task({"persistentIdentifier": "t-completed", "dateCompleted": _NOW_CF}),
            _minimal_task({"persistentIdentifier": "t-dropped", "dateHidden": _NOW_CF}),
        ],
    )
    async def test_list_tasks_default_excludes_completed_dropped(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """TASK-11: Default query returns available + blocked, excludes completed and dropped."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery())
        assert result.total == 2
        ids = {t.id for t in result.items}
        assert ids == {"t-avail", "t-blocked"}

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-active"}),
            _minimal_task(
                {"persistentIdentifier": "t-ghost", "effectiveDateCompleted": _NOW_CF}
            ),
        ],
    )
    async def test_list_tasks_default_excludes_ghost_completed(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Ghost task (effectiveDateCompleted only, no dateCompleted) excluded from default."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery())
        ids = {t.id for t in result.items}
        assert "t-active" in ids
        assert "t-ghost" not in ids

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-flag", "flagged": 1}),
            _minimal_task({"persistentIdentifier": "t-noflag", "flagged": 0}),
        ],
    )
    async def test_list_tasks_flagged_true(self, hybrid_repo: HybridRepository) -> None:
        """TASK-02: flagged=True returns only flagged tasks."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(flagged=True))
        assert result.total == 1
        assert result.items[0].id == "t-flag"
        assert result.items[0].flagged is True

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-flag", "flagged": 1}),
            _minimal_task({"persistentIdentifier": "t-noflag", "flagged": 0}),
        ],
    )
    async def test_list_tasks_flagged_false(self, hybrid_repo: HybridRepository) -> None:
        """TASK-02: flagged=False returns only unflagged tasks."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(flagged=False))
        assert result.total == 1
        assert result.items[0].id == "t-noflag"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-inbox", "inInbox": 1}),
            _minimal_task({"persistentIdentifier": "t-noninbox", "inInbox": 0}),
        ],
    )
    async def test_list_tasks_in_inbox(self, hybrid_repo: HybridRepository) -> None:
        """TASK-01: in_inbox=True returns only inbox tasks."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(in_inbox=True))
        assert result.total == 1
        assert result.items[0].id == "t-inbox"
        assert result.items[0].in_inbox is True

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "t-in-proj",
                    "containingProjectInfo": "pi-proj-work",
                }
            ),
            _minimal_task({"persistentIdentifier": "t-no-proj"}),
        ],
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "proj-work",
                    "name": "Work Stuff",
                    "project_info": {
                        "pk": "pi-proj-work",
                        "task": "proj-work",
                        "effectiveStatus": "active",
                    },
                }
            ),
        ],
    )
    async def test_list_tasks_project_filter(self, hybrid_repo: HybridRepository) -> None:
        """TASK-03: project filter matches by project ID."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(project_ids=["proj-work"]))
        assert result.total == 1
        assert result.items[0].id == "t-in-proj"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "t-work-lower",
                    "containingProjectInfo": "pi-proj-work-lower",
                }
            ),
            _minimal_task(
                {
                    "persistentIdentifier": "t-work-upper",
                    "containingProjectInfo": "pi-proj-work-upper",
                }
            ),
            _minimal_task(
                {
                    "persistentIdentifier": "t-personal",
                    "containingProjectInfo": "pi-proj-personal",
                }
            ),
        ],
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "proj-work-lower",
                    "name": "work errands",
                    "project_info": {
                        "pk": "pi-proj-work-lower",
                        "task": "proj-work-lower",
                        "effectiveStatus": "active",
                    },
                }
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "proj-work-upper",
                    "name": "WORK Projects",
                    "project_info": {
                        "pk": "pi-proj-work-upper",
                        "task": "proj-work-upper",
                        "effectiveStatus": "active",
                    },
                }
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "proj-personal",
                    "name": "Personal",
                    "project_info": {
                        "pk": "pi-proj-personal",
                        "task": "proj-personal",
                        "effectiveStatus": "active",
                    },
                }
            ),
        ],
    )
    async def test_list_tasks_project_filter_multiple_ids(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """TASK-03: project filter matches multiple projects by ID list."""
        result = await hybrid_repo.list_tasks(
            ListTasksRepoQuery(project_ids=["proj-work-lower", "proj-work-upper"])
        )
        assert result.total == 2
        ids = {t.id for t in result.items}
        assert ids == {"t-work-lower", "t-work-upper"}

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t1"}),
            _minimal_task({"persistentIdentifier": "t2"}),
        ],
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-001", "name": "Errand"}),
            _minimal_tag({"persistentIdentifier": "tag-002", "name": "Home"}),
        ],
        task_tags=[
            {"task": "t1", "tag": "tag-001"},
            {"task": "t2", "tag": "tag-002"},
        ],
    )
    async def test_list_tasks_tags_filter(self, hybrid_repo: HybridRepository) -> None:
        """TASK-04: tags filter returns tasks with matching tag (OR logic for multiple)."""
        # Single tag
        result_one = await hybrid_repo.list_tasks(ListTasksRepoQuery(tag_ids=["tag-001"]))
        assert result_one.total == 1
        assert result_one.items[0].id == "t1"

        # Multiple tags (OR logic)
        result_both = await hybrid_repo.list_tasks(
            ListTasksRepoQuery(tag_ids=["tag-001", "tag-002"])
        )
        assert result_both.total == 2

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-15", "estimatedMinutes": 15}),
            _minimal_task({"persistentIdentifier": "t-30", "estimatedMinutes": 30}),
            _minimal_task({"persistentIdentifier": "t-60", "estimatedMinutes": 60}),
        ],
    )
    async def test_list_tasks_estimated_minutes_max(self, hybrid_repo: HybridRepository) -> None:
        """TASK-06: estimated_minutes_max returns tasks with estimate <= threshold."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(estimated_minutes_max=30))
        assert result.total == 2
        ids = {t.id for t in result.items}
        assert ids == {"t-15", "t-30"}

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-done", "dateCompleted": _NOW_CF}),
            _minimal_task({"persistentIdentifier": "t-avail"}),
        ],
    )
    async def test_list_tasks_availability_completed(self, hybrid_repo: HybridRepository) -> None:
        """TASK-07: availability=[COMPLETED] returns only completed tasks."""
        query = ListTasksRepoQuery(availability=[Availability.COMPLETED])
        result = await hybrid_repo.list_tasks(query)
        assert result.total == 1
        assert result.items[0].id == "t-done"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-buy", "name": "Buy groceries"}),
            _minimal_task({"persistentIdentifier": "t-write", "name": "Write report"}),
        ],
    )
    async def test_list_tasks_search_name(self, hybrid_repo: HybridRepository) -> None:
        """TASK-08: search matches task name (case-insensitive)."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(search="buy"))
        assert result.total == 1
        assert result.items[0].id == "t-buy"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "t-noted",
                    "name": "Check things",
                    "plainTextNote": "Remember to call dentist",
                }
            ),
            _minimal_task({"persistentIdentifier": "t-plain", "name": "Other task"}),
        ],
    )
    async def test_list_tasks_search_notes(self, hybrid_repo: HybridRepository) -> None:
        """TASK-08: search matches in plainTextNote (case-insensitive)."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(search="dentist"))
        assert result.total == 1
        assert result.items[0].id == "t-noted"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"persistentIdentifier": f"t-{i}"}) for i in range(5)],
    )
    async def test_list_tasks_pagination_limit(self, hybrid_repo: HybridRepository) -> None:
        """TASK-09: limit returns at most N items with correct total and has_more."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(limit=2))
        assert len(result.items) == 2
        assert result.total == 5
        assert result.has_more is True

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"persistentIdentifier": f"t-{i}"}) for i in range(5)],
    )
    async def test_list_tasks_pagination_offset(self, hybrid_repo: HybridRepository) -> None:
        """TASK-09: limit+offset paginates correctly, has_more=False at end."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(limit=2, offset=3))
        assert len(result.items) == 2
        assert result.total == 5
        assert result.has_more is False

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task(
                {
                    "persistentIdentifier": "t-both",
                    "flagged": 1,
                    "inInbox": 1,
                }
            ),
            _minimal_task(
                {
                    "persistentIdentifier": "t-flag-only",
                    "flagged": 1,
                    "inInbox": 0,
                }
            ),
            _minimal_task(
                {
                    "persistentIdentifier": "t-inbox-only",
                    "flagged": 0,
                    "inInbox": 1,
                }
            ),
        ],
    )
    async def test_list_tasks_combined_filters(self, hybrid_repo: HybridRepository) -> None:
        """TASK-10: Multiple filters combine with AND logic."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(flagged=True, in_inbox=True))
        assert result.total == 1
        assert result.items[0].id == "t-both"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[_minimal_task({"persistentIdentifier": "t-unflagged", "flagged": 0})],
    )
    async def test_list_tasks_no_results(self, hybrid_repo: HybridRepository) -> None:
        """No matching tasks returns empty list with total=0, has_more=False."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(flagged=True))
        assert result.items == []
        assert result.total == 0
        assert result.has_more is False

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t1"}),
            _minimal_task({"persistentIdentifier": "t2"}),
        ],
    )
    async def test_list_tasks_has_more_false_when_all_fit(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """When limit > total items, has_more is False."""
        result = await hybrid_repo.list_tasks(ListTasksRepoQuery(limit=10))
        assert len(result.items) == 2
        assert result.has_more is False


class TestListProjects:
    """Comprehensive tests for list_projects filters and pagination."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "p-active",
                    "project_info": {"effectiveStatus": "active"},
                }
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "p-inactive",
                    "project_info": {"effectiveStatus": "inactive"},
                }
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "p-dropped",
                    "project_info": {"effectiveStatus": "dropped"},
                }
            ),
        ],
    )
    async def test_list_projects_default_remaining(self, hybrid_repo: HybridRepository) -> None:
        """PROJ-03: Default returns remaining (available + blocked), excludes dropped."""
        result = await hybrid_repo.list_projects(ListProjectsRepoQuery())
        assert result.total == 2
        ids = {p.id for p in result.items}
        assert ids == {"p-active", "p-inactive"}

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "p-done",
                    "dateCompleted": _NOW_CF,
                    "project_info": {"effectiveStatus": "active"},
                }
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "p-avail",
                    "project_info": {"effectiveStatus": "active"},
                }
            ),
        ],
    )
    async def test_list_projects_availability_completed(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """PROJ-01: availability=[COMPLETED] returns only completed projects."""
        result = await hybrid_repo.list_projects(
            ListProjectsRepoQuery(availability=[Availability.COMPLETED])
        )
        assert result.total == 1
        assert result.items[0].id == "p-done"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "p-in-folder",
                    "project_info": {
                        "effectiveStatus": "active",
                        "folder": "fold-personal",
                    },
                }
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "p-nofolder",
                    "project_info": {"effectiveStatus": "active"},
                }
            ),
        ],
        folders=[
            _minimal_folder(
                {
                    "persistentIdentifier": "fold-personal",
                    "name": "My Personal Projects",
                }
            ),
        ],
    )
    async def test_list_projects_folder_filter(self, hybrid_repo: HybridRepository) -> None:
        """PROJ-04: folder filter matches by folder ID."""
        result = await hybrid_repo.list_projects(
            ListProjectsRepoQuery(folder_ids=["fold-personal"])
        )
        assert result.total == 1
        assert result.items[0].id == "p-in-folder"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project(
                {
                    "persistentIdentifier": "p-review-soon",
                    "project_info": {
                        "effectiveStatus": "active",
                        "nextReviewDate": _cf_epoch(datetime(2026, 3, 15, tzinfo=UTC)),
                    },
                }
            ),
            _minimal_project(
                {
                    "persistentIdentifier": "p-review-later",
                    "project_info": {
                        "effectiveStatus": "active",
                        "nextReviewDate": _cf_epoch(datetime(2026, 6, 1, tzinfo=UTC)),
                    },
                }
            ),
        ],
    )
    async def test_list_projects_review_due_before(self, hybrid_repo: HybridRepository) -> None:
        """PROJ-05: review_due_before returns projects with nextReviewDate <= threshold."""
        result = await hybrid_repo.list_projects(
            ListProjectsRepoQuery(
                review_due_before=datetime(2026, 4, 1, tzinfo=UTC),
            )
        )
        assert result.total == 1
        assert result.items[0].id == "p-review-soon"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project({"persistentIdentifier": "p-flag", "flagged": 1}),
            _minimal_project({"persistentIdentifier": "p-noflag", "flagged": 0}),
        ],
    )
    async def test_list_projects_flagged(self, hybrid_repo: HybridRepository) -> None:
        """PROJ-06: flagged=True returns only flagged projects."""
        result = await hybrid_repo.list_projects(ListProjectsRepoQuery(flagged=True))
        assert result.total == 1
        assert result.items[0].id == "p-flag"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[_minimal_project({"persistentIdentifier": f"p-{i}"}) for i in range(5)],
    )
    async def test_list_projects_pagination(self, hybrid_repo: HybridRepository) -> None:
        """PROJ-07: limit returns at most N items with correct has_more and total."""
        result = await hybrid_repo.list_projects(ListProjectsRepoQuery(limit=2))
        assert len(result.items) == 2
        assert result.total == 5
        assert result.has_more is True


class TestDeterministicOrdering:
    """Pagination returns items sorted by persistentIdentifier for deterministic pages."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-cherry"}),
            _minimal_task({"persistentIdentifier": "t-apple"}),
            _minimal_task({"persistentIdentifier": "t-banana"}),
            _minimal_task({"persistentIdentifier": "t-elderberry"}),
            _minimal_task({"persistentIdentifier": "t-date"}),
        ],
    )
    async def test_list_tasks_paginated_sorted_by_id(self, hybrid_repo: HybridRepository) -> None:
        """Tasks are sorted by persistentIdentifier so offset/limit is deterministic."""
        page1 = await hybrid_repo.list_tasks(ListTasksRepoQuery(limit=3))
        page2 = await hybrid_repo.list_tasks(ListTasksRepoQuery(limit=3, offset=3))

        page1_ids = [t.id for t in page1.items]
        page2_ids = [t.id for t in page2.items]

        assert page1_ids == ["t-apple", "t-banana", "t-cherry"]
        assert page2_ids == ["t-date", "t-elderberry"]
        assert page1.has_more is True
        assert page2.has_more is False

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        projects=[
            _minimal_project({"persistentIdentifier": "p-zebra"}),
            _minimal_project({"persistentIdentifier": "p-alpha"}),
            _minimal_project({"persistentIdentifier": "p-mango"}),
            _minimal_project({"persistentIdentifier": "p-beta"}),
            _minimal_project({"persistentIdentifier": "p-gamma"}),
        ],
    )
    async def test_list_projects_paginated_sorted_by_id(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Projects are sorted by persistentIdentifier so offset/limit is deterministic."""
        page1 = await hybrid_repo.list_projects(ListProjectsRepoQuery(limit=3))
        page2 = await hybrid_repo.list_projects(ListProjectsRepoQuery(limit=3, offset=3))

        page1_ids = [p.id for p in page1.items]
        page2_ids = [p.id for p in page2.items]

        assert page1_ids == ["p-alpha", "p-beta", "p-gamma"]
        assert page2_ids == ["p-mango", "p-zebra"]
        assert page1.has_more is True
        assert page2.has_more is False

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tasks=[
            _minimal_task({"persistentIdentifier": "t-cherry"}),
            _minimal_task({"persistentIdentifier": "t-apple"}),
            _minimal_task({"persistentIdentifier": "t-banana"}),
            _minimal_task({"persistentIdentifier": "t-elderberry"}),
            _minimal_task({"persistentIdentifier": "t-date"}),
        ],
    )
    async def test_list_tasks_consecutive_pages_no_overlap(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Consecutive pages cover all items exactly once with no overlap."""
        all_ids: list[str] = []
        offset = 0
        while True:
            page = await hybrid_repo.list_tasks(ListTasksRepoQuery(limit=2, offset=offset))
            all_ids.extend(t.id for t in page.items)
            if not page.has_more:
                break
            offset += len(page.items)

        assert all_ids == sorted(all_ids)
        assert len(all_ids) == 5
        assert len(set(all_ids)) == 5  # no duplicates


class TestListPerformance:
    """Performance comparison: filtered query vs full snapshot."""

    @pytest.mark.asyncio
    async def test_filtered_faster_than_full_snapshot(self, tmp_path: Path) -> None:
        """INFRA-02: Filtered query executes faster than full get_all() snapshot."""
        # Generate performance seed data
        tasks = []
        tags = []
        folders = []
        projects = []
        task_tags_data = []

        for i in range(15):
            tags.append(
                _minimal_tag(
                    {
                        "persistentIdentifier": f"perf-tag-{i}",
                        "name": f"Tag {i}",
                    }
                )
            )
        for i in range(5):
            folders.append(
                _minimal_folder(
                    {
                        "persistentIdentifier": f"perf-fold-{i}",
                        "name": f"Folder {i}",
                    }
                )
            )
        for i in range(30):
            projects.append(
                _minimal_project(
                    {
                        "persistentIdentifier": f"perf-proj-{i}",
                        "name": f"Project {i}",
                        "project_info": {
                            "pk": f"pi-perf-proj-{i}",
                            "task": f"perf-proj-{i}",
                            "effectiveStatus": "active",
                            "folder": f"perf-fold-{i % 5}",
                        },
                    }
                )
            )
        for i in range(150):
            flagged = 1 if i % 10 == 0 else 0
            completed = _NOW_CF if i % 20 == 0 else None
            est_min = (i % 6) * 15 if i % 3 == 0 else None
            tasks.append(
                _minimal_task(
                    {
                        "persistentIdentifier": f"perf-task-{i}",
                        "name": f"Task {i}",
                        "flagged": flagged,
                        "estimatedMinutes": est_min,
                        "dateCompleted": completed,
                        "containingProjectInfo": f"pi-perf-proj-{i % 30}",
                    }
                )
            )
            if i % 5 == 0:
                task_tags_data.append({"task": f"perf-task-{i}", "tag": f"perf-tag-{i % 15}"})

        db_path = create_test_db(
            tmp_path,
            tasks=tasks,
            projects=projects,
            tags=tags,
            folders=folders,
            task_tags=task_tags_data,
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())

        # Warmup
        await repo.list_tasks(ListTasksRepoQuery(flagged=True))
        await repo.get_all()

        # Time filtered query
        iterations = 20
        start = time.monotonic()
        for _ in range(iterations):
            await repo.list_tasks(ListTasksRepoQuery(flagged=True))
        filtered_time = time.monotonic() - start

        # Time full snapshot
        start = time.monotonic()
        for _ in range(iterations):
            await repo.get_all()
        full_time = time.monotonic() - start

        assert filtered_time < full_time, (
            f"Filtered ({filtered_time:.3f}s) should be faster than "
            f"full snapshot ({full_time:.3f}s)"
        )


# ============================================================================
# LIST TAGS / LIST FOLDERS / LIST PERSPECTIVES TESTS (Plan 02)
# ============================================================================


class TestListTags:
    """Tests for HybridRepository.list_tags -- fetch-all + Python filter."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-avail", "allowsNextAction": 1}),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-blocked",
                    "name": "Blocked Tag",
                    "allowsNextAction": 0,
                }
            ),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-dropped",
                    "name": "Dropped Tag",
                    "dateHidden": _EARLIER_CF,
                }
            ),
        ],
    )
    async def test_list_tags_default_excludes_dropped(self, hybrid_repo: HybridRepository) -> None:
        """Default query returns available + blocked tags, excludes dropped."""
        result = await hybrid_repo.list_tags(ListTagsRepoQuery())
        ids = {t.id for t in result.items}
        assert ids == {"tag-avail", "tag-blocked"}
        assert "tag-dropped" not in ids

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-avail", "allowsNextAction": 1}),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-blocked",
                    "allowsNextAction": 0,
                }
            ),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-dropped",
                    "dateHidden": _EARLIER_CF,
                }
            ),
        ],
    )
    async def test_list_tags_filter_available_only(self, hybrid_repo: HybridRepository) -> None:
        """Filter for available-only returns 1 tag."""
        result = await hybrid_repo.list_tags(
            ListTagsRepoQuery(availability=[TagAvailability.AVAILABLE])
        )
        assert len(result.items) == 1
        assert result.items[0].id == "tag-avail"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-avail", "allowsNextAction": 1}),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-blocked",
                    "allowsNextAction": 0,
                }
            ),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-dropped",
                    "dateHidden": _EARLIER_CF,
                }
            ),
        ],
    )
    async def test_list_tags_filter_dropped_only(self, hybrid_repo: HybridRepository) -> None:
        """Filter for dropped-only returns 1 tag."""
        query = ListTagsRepoQuery(availability=[TagAvailability.DROPPED])
        result = await hybrid_repo.list_tags(query)
        assert len(result.items) == 1
        assert result.items[0].id == "tag-dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-avail", "allowsNextAction": 1}),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-blocked",
                    "allowsNextAction": 0,
                }
            ),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-dropped",
                    "dateHidden": _EARLIER_CF,
                }
            ),
        ],
    )
    async def test_list_tags_all_availability(self, hybrid_repo: HybridRepository) -> None:
        """All availability values returns all 3 tags."""
        result = await hybrid_repo.list_tags(
            ListTagsRepoQuery(
                availability=[
                    TagAvailability.AVAILABLE,
                    TagAvailability.BLOCKED,
                    TagAvailability.DROPPED,
                ]
            )
        )
        assert len(result.items) == 3

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        tags=[
            _minimal_tag({"persistentIdentifier": "tag-avail", "allowsNextAction": 1}),
            _minimal_tag(
                {
                    "persistentIdentifier": "tag-blocked",
                    "allowsNextAction": 0,
                }
            ),
        ],
    )
    async def test_list_tags_result_shape(self, hybrid_repo: HybridRepository) -> None:
        """ListRepoResult has has_more=False and total=len(items)."""
        result = await hybrid_repo.list_tags(ListTagsRepoQuery())
        assert result.has_more is False
        assert result.total == len(result.items)
        assert result.total == 2


class TestListFolders:
    """Tests for HybridRepository.list_folders -- fetch-all + Python filter."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        folders=[
            _minimal_folder({"persistentIdentifier": "folder-avail"}),
            _minimal_folder(
                {
                    "persistentIdentifier": "folder-dropped",
                    "name": "Dropped Folder",
                    "dateHidden": _EARLIER_CF,
                }
            ),
        ],
    )
    async def test_list_folders_default_excludes_dropped(
        self, hybrid_repo: HybridRepository
    ) -> None:
        """Default query returns only available folders, excludes dropped."""
        result = await hybrid_repo.list_folders(ListFoldersRepoQuery())
        assert len(result.items) == 1
        assert result.items[0].id == "folder-avail"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        folders=[
            _minimal_folder({"persistentIdentifier": "folder-avail"}),
            _minimal_folder(
                {
                    "persistentIdentifier": "folder-dropped",
                    "dateHidden": _EARLIER_CF,
                }
            ),
        ],
    )
    async def test_list_folders_filter_dropped(self, hybrid_repo: HybridRepository) -> None:
        """Filter for dropped-only returns 1 folder."""
        result = await hybrid_repo.list_folders(
            ListFoldersRepoQuery(availability=[FolderAvailability.DROPPED])
        )
        assert len(result.items) == 1
        assert result.items[0].id == "folder-dropped"

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        folders=[
            _minimal_folder({"persistentIdentifier": "folder-avail"}),
            _minimal_folder(
                {
                    "persistentIdentifier": "folder-dropped",
                    "dateHidden": _EARLIER_CF,
                }
            ),
        ],
    )
    async def test_list_folders_all(self, hybrid_repo: HybridRepository) -> None:
        """All availability values returns all 2 folders."""
        result = await hybrid_repo.list_folders(
            ListFoldersRepoQuery(
                availability=[FolderAvailability.AVAILABLE, FolderAvailability.DROPPED]
            )
        )
        assert len(result.items) == 2

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        folders=[
            _minimal_folder({"persistentIdentifier": "folder-avail"}),
        ],
    )
    async def test_list_folders_result_shape(self, hybrid_repo: HybridRepository) -> None:
        """ListRepoResult has has_more=False and total=len(items)."""
        result = await hybrid_repo.list_folders(ListFoldersRepoQuery())
        assert result.has_more is False
        assert result.total == len(result.items)
        assert result.total == 1


class TestListPerspectives:
    """Tests for HybridRepository.list_perspectives -- fetch-all, no filter."""

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        perspectives=[
            {
                "persistentIdentifier": "persp-001",
                "valueData": _make_perspective_plist("Custom View"),
            },
            {
                "persistentIdentifier": None,
                "valueData": _make_perspective_plist("Inbox"),
            },
        ],
    )
    async def test_list_perspectives_returns_all(self, hybrid_repo: HybridRepository) -> None:
        """list_perspectives returns all perspectives."""
        result = await hybrid_repo.list_perspectives(ListPerspectivesRepoQuery())
        assert len(result.items) == 2
        names = {p.name for p in result.items}
        assert names == {"Custom View", "Inbox"}

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        perspectives=[
            {
                "persistentIdentifier": "persp-custom",
                "valueData": _make_perspective_plist("My Custom"),
            },
            {
                "persistentIdentifier": None,
                "valueData": _make_perspective_plist("Forecast"),
            },
        ],
    )
    async def test_list_perspectives_builtin_flag(self, hybrid_repo: HybridRepository) -> None:
        """Custom perspectives have builtin=False, built-in have builtin=True."""
        result = await hybrid_repo.list_perspectives(ListPerspectivesRepoQuery())
        by_name = {p.name: p for p in result.items}
        assert by_name["My Custom"].builtin is False
        assert by_name["My Custom"].id == "persp-custom"
        assert by_name["Forecast"].builtin is True
        assert by_name["Forecast"].id is None

    @pytest.mark.asyncio
    @pytest.mark.hybrid_db(
        perspectives=[
            {
                "persistentIdentifier": "persp-001",
                "valueData": _make_perspective_plist("View A"),
            },
            {
                "persistentIdentifier": "persp-002",
                "valueData": _make_perspective_plist("View B"),
            },
            {
                "persistentIdentifier": None,
                "valueData": _make_perspective_plist("Built-in"),
            },
        ],
    )
    async def test_list_perspectives_result_shape(self, hybrid_repo: HybridRepository) -> None:
        """ListRepoResult has has_more=False and total matches item count."""
        result = await hybrid_repo.list_perspectives(ListPerspectivesRepoQuery())
        assert result.has_more is False
        assert result.total == len(result.items)
        assert result.total == 3
