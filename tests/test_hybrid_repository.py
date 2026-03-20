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

if TYPE_CHECKING:
    from pathlib import Path

import pytest

from tests.doubles import InMemoryBridge
from omnifocus_operator.contracts.protocols import Repository
from omnifocus_operator.contracts.use_cases.add_task import AddTaskRepoPayload
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskRepoPayload
from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.repository.hybrid import _FRESHNESS_TIMEOUT, HybridRepository

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
def empty_db(tmp_path: Path) -> Path:
    """Empty OmniFocus-schema SQLite database."""
    return create_test_db(tmp_path)


@pytest.fixture
def empty_repo(empty_db: Path) -> HybridRepository:
    """HybridRepository backed by an empty DB + InMemoryBridge."""
    return HybridRepository(db_path=empty_db, bridge=InMemoryBridge())


@pytest.fixture
def minimal_task_db(tmp_path: Path) -> Path:
    """DB with one minimal task row."""
    return create_test_db(tmp_path, tasks=[_minimal_task()])


@pytest.fixture
def minimal_task_repo(minimal_task_db: Path) -> HybridRepository:
    """HybridRepository with one minimal task + InMemoryBridge."""
    return HybridRepository(db_path=minimal_task_db, bridge=InMemoryBridge())


# ============================================================================
# TESTS
# ============================================================================


class TestProtocol:
    def test_satisfies_repository_protocol(self, empty_repo: HybridRepository) -> None:
        assert isinstance(empty_repo, Repository)


class TestReadAllEntities:
    @pytest.mark.asyncio
    async def test_read_all_entities(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert isinstance(result, AllEntities)
        assert len(result.tasks) == 1
        assert len(result.projects) == 1
        assert len(result.tags) == 1
        assert len(result.folders) == 1
        assert len(result.perspectives) == 1


class TestConnectionSemantics:
    def test_read_only_connection(self, empty_repo: HybridRepository) -> None:
        """Verify that the connection string contains ?mode=ro."""
        # Inspect the connection URI by calling _read_all and checking the path usage
        # We'll monkeypatch sqlite3.connect to capture the URI
        calls: list[str] = []
        original_connect = sqlite3.connect

        def capturing_connect(uri_str: str, **kwargs: Any) -> Any:
            calls.append(uri_str)
            return original_connect(uri_str, **kwargs)

        with patch("sqlite3.connect", side_effect=capturing_connect):
            empty_repo._read_all()

        assert len(calls) == 1
        assert "?mode=ro" in calls[0]

    @pytest.mark.asyncio
    async def test_fresh_connection_per_read(self, empty_repo: HybridRepository) -> None:
        """Two consecutive get_all() calls create two separate connections."""
        call_count = 0
        original_connect = sqlite3.connect

        def counting_connect(uri_str: str, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return original_connect(uri_str, **kwargs)

        with patch("sqlite3.connect", side_effect=counting_connect):
            await empty_repo.get_all()
            await empty_repo.get_all()

        assert call_count == 2


class TestTaskBasicFields:
    @pytest.mark.asyncio
    async def test_task_basic_fields(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
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
    async def test_task_dates_local_time_string(self, tmp_path: Path) -> None:
        """dateDue/dateToStart as local-time ISO strings parse correctly."""
        from zoneinfo import ZoneInfo

        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "dateDue": "2026-02-20T15:15:16.000",
                        "dateToStart": "2026-02-20T15:15:16.000",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        # Use UTC timezone so local time == UTC for predictable assertions
        with patch(
            "omnifocus_operator.repository.hybrid._LOCAL_TZ",
            ZoneInfo("UTC"),
        ):
            result = await repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.year == 2026
        assert task.due_date.month == 2
        assert task.due_date.day == 20
        assert task.defer_date is not None
        assert task.defer_date.year == 2026

    @pytest.mark.asyncio
    async def test_effective_dates_cf_epoch(self, tmp_path: Path) -> None:
        """effectiveDateDue/effectiveDateToStart as CF epoch floats parse correctly."""
        target_dt = datetime(2026, 2, 16, 22, 0, 0, tzinfo=UTC)
        cf_value = _cf_epoch(target_dt)
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "effectiveDateDue": cf_value,
                        "effectiveDateToStart": cf_value,
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        task = result.tasks[0]

        assert task.effective_due_date is not None
        assert task.effective_due_date.year == 2026
        assert task.effective_due_date.month == 2
        assert task.effective_due_date.day == 16
        assert task.effective_defer_date is not None

    @pytest.mark.asyncio
    async def test_task_null_dates(self, minimal_task_repo: HybridRepository) -> None:
        """NULL date columns produce None fields."""
        result = await minimal_task_repo.get_all()
        task = result.tasks[0]

        assert task.due_date is None
        assert task.defer_date is None
        assert task.completion_date is None
        assert task.drop_date is None
        assert task.planned_date is None


class TestTaskStatus:
    @pytest.mark.asyncio
    async def test_task_urgency_overdue(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"overdue": 1, "dueSoon": 0})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].urgency == "overdue"

    @pytest.mark.asyncio
    async def test_task_urgency_due_soon(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"overdue": 0, "dueSoon": 1})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].urgency == "due_soon"

    @pytest.mark.asyncio
    async def test_task_urgency_none(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"overdue": 0, "dueSoon": 0})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].urgency == "none"

    @pytest.mark.asyncio
    async def test_task_urgency_overdue_priority(self, tmp_path: Path) -> None:
        """Overdue takes priority over due_soon."""
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"overdue": 1, "dueSoon": 1})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].urgency == "overdue"

    @pytest.mark.asyncio
    async def test_task_availability_dropped(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"dateHidden": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_task_availability_completed(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"dateCompleted": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].availability == "completed"

    @pytest.mark.asyncio
    async def test_task_availability_blocked(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"blocked": 1})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].availability == "blocked"

    @pytest.mark.asyncio
    async def test_task_availability_available(self, minimal_task_repo: HybridRepository) -> None:
        result = await minimal_task_repo.get_all()
        assert result.tasks[0].availability == "available"


class TestTaskTags:
    @pytest.mark.asyncio
    async def test_task_tags_via_join(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        task = result.tasks[0]
        assert len(task.tags) == 2
        tag_names = {t.name for t in task.tags}
        assert tag_names == {"Errand", "Home"}
        tag_ids = {t.id for t in task.tags}
        assert tag_ids == {"tag-a", "tag-b"}


class TestTaskRepetition:
    @pytest.mark.asyncio
    async def test_task_repetition_rule(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        task = result.tasks[0]
        assert task.repetition_rule is not None
        assert task.repetition_rule.rule_string == "FREQ=WEEKLY;INTERVAL=1"
        assert task.repetition_rule.schedule_type == "regularly"
        assert task.repetition_rule.anchor_date_key == "due_date"
        assert task.repetition_rule.catch_up_automatically is True

    @pytest.mark.asyncio
    async def test_task_no_repetition_rule(self, minimal_task_repo: HybridRepository) -> None:
        result = await minimal_task_repo.get_all()
        assert result.tasks[0].repetition_rule is None


class TestTaskNotes:
    @pytest.mark.asyncio
    async def test_task_note_plain_text(self, tmp_path: Path) -> None:
        """Notes are read from plainTextNote column (not noteXMLData)."""
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "plainTextNote": "Buy oat milk and eggs",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].note == "Buy oat milk and eggs"

    @pytest.mark.asyncio
    async def test_task_note_null(self, minimal_task_repo: HybridRepository) -> None:
        result = await minimal_task_repo.get_all()
        assert result.tasks[0].note == ""


class TestTaskRelationships:
    @pytest.mark.asyncio
    async def test_inbox_task_parent_null(self, minimal_task_repo: HybridRepository) -> None:
        """Task with no project and no parent has parent=None."""
        result = await minimal_task_repo.get_all()
        task = result.tasks[0]
        assert task.parent is None

    @pytest.mark.asyncio
    async def test_task_in_project_parent_ref(self, tmp_path: Path) -> None:
        """Task in a project gets parent={type:'project', id, name}."""
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "containingProjectInfo": "pi-proj-001",
                    }
                )
            ],
            projects=[_minimal_project()],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        task = result.tasks[0]
        assert task.parent is not None
        assert task.parent.type == "project"
        assert task.parent.id == "proj-001"
        assert task.parent.name == "Test Project"

    @pytest.mark.asyncio
    async def test_subtask_parent_ref(self, tmp_path: Path) -> None:
        """Subtask gets parent={type:'task', id, name} using parent task."""
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        subtask = next(t for t in result.tasks if t.id == "subtask-001")
        assert subtask.parent is not None
        assert subtask.parent.type == "task"
        assert subtask.parent.id == "parent-task-001"
        assert subtask.parent.name == "Parent Task"


class TestProjectFields:
    @pytest.mark.asyncio
    async def test_project_fields(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
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
    async def test_project_availability_dropped_by_status(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[
                _minimal_project(
                    {
                        "project_info": {"effectiveStatus": "dropped"},
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_project_availability_dropped_by_date_hidden(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[_minimal_project({"dateHidden": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_project_availability_completed(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[_minimal_project({"dateCompleted": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].availability == "completed"

    @pytest.mark.asyncio
    async def test_project_availability_blocked(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[
                _minimal_project(
                    {
                        "project_info": {"effectiveStatus": "inactive"},
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].availability == "blocked"

    @pytest.mark.asyncio
    async def test_project_availability_available(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[_minimal_project()],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].availability == "available"

    @pytest.mark.asyncio
    async def test_project_review_interval_weekly(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[
                _minimal_project(
                    {
                        "project_info": {"reviewRepetitionString": "@1w"},
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].review_interval.steps == 1
        assert result.projects[0].review_interval.unit == "weeks"

    @pytest.mark.asyncio
    async def test_project_review_interval_monthly(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[
                _minimal_project(
                    {
                        "project_info": {"reviewRepetitionString": "~2m"},
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].review_interval.steps == 2
        assert result.projects[0].review_interval.unit == "months"


class TestTagFields:
    @pytest.mark.asyncio
    async def test_tag_fields(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        tag = result.tags[0]
        assert tag.id == "tag-xyz"
        assert tag.name == "Errands"
        assert tag.url == "omnifocus:///tag/tag-xyz"
        assert tag.children_are_mutually_exclusive is True
        assert tag.parent == "tag-parent"
        assert tag.added is not None
        assert tag.modified is not None

    @pytest.mark.asyncio
    async def test_tag_availability_blocked(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tags=[_minimal_tag({"allowsNextAction": 0})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tags[0].availability == "blocked"

    @pytest.mark.asyncio
    async def test_tag_availability_dropped(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tags=[_minimal_tag({"dateHidden": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tags[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_tag_availability_available(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tags=[_minimal_tag()],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tags[0].availability == "available"


class TestFolderFields:
    @pytest.mark.asyncio
    async def test_folder_fields(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        folder = result.folders[0]
        assert folder.id == "fold-1"
        assert folder.name == "Work"
        assert folder.url == "omnifocus:///folder/fold-1"
        assert folder.parent == "fold-parent"
        assert folder.added is not None
        assert folder.modified is not None

    @pytest.mark.asyncio
    async def test_folder_availability_dropped(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            folders=[_minimal_folder({"dateHidden": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.folders[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_folder_availability_available(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            folders=[_minimal_folder()],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.folders[0].availability == "available"


class TestPerspective:
    @pytest.mark.asyncio
    async def test_perspective_from_plist(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            perspectives=[
                {
                    "persistentIdentifier": "persp-custom",
                    "valueData": _make_perspective_plist("My Custom View"),
                }
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        persp = result.perspectives[0]
        assert persp.id == "persp-custom"
        assert persp.name == "My Custom View"
        assert persp.builtin is False

    @pytest.mark.asyncio
    async def test_perspective_builtin_detection(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            perspectives=[
                {
                    "persistentIdentifier": None,
                    "valueData": _make_perspective_plist("Inbox"),
                }
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        persp = result.perspectives[0]
        assert persp.id is None
        assert persp.builtin is True


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_database(self, empty_repo: HybridRepository) -> None:
        result = await empty_repo.get_all()
        assert result.tasks == []
        assert result.projects == []
        assert result.tags == []
        assert result.folders == []
        assert result.perspectives == []

    @pytest.mark.asyncio
    async def test_reads_without_omnifocus(self, tmp_path: Path) -> None:
        """Reading from a file-based SQLite works without OmniFocus process."""
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task()],
            tags=[_minimal_tag()],
        )
        # This is already a file-based test (using tmp_path).
        # The point: no OmniFocus dependency, just a SQLite file.
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
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

        bridge = InMemoryBridge(data={"id": "task-001", "name": "Edited"})
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

        bridge = InMemoryBridge(data={"id": "task-001", "name": "Edited"})
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

        bridge = InMemoryBridge(data={"id": "task-001", "name": "Edited"})
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
        bridge = InMemoryBridge(data={"id": "task-001", "name": "Edited"}, wal_path=wal_path)
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

        bridge = InMemoryBridge(data={"id": "task-001", "name": "Edited"})
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
            "omnifocus_operator.repository.hybrid.asyncio.sleep", side_effect=tracking_sleep
        ):
            await repo.edit_task(EditTaskRepoPayload(id="task-001", name="Edited"))
        await task

        # All sleep calls should be 0.05 (50ms)
        assert len(sleep_calls) > 0
        for call in sleep_calls:
            assert call == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_reads_never_poll(self, minimal_task_repo: HybridRepository) -> None:
        """Read methods never trigger freshness polling."""
        sleep_calls: list[float] = []
        original_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            sleep_calls.append(duration)
            await original_sleep(duration)

        with patch(
            "omnifocus_operator.repository.hybrid.asyncio.sleep", side_effect=tracking_sleep
        ):
            await minimal_task_repo.get_all()
            await minimal_task_repo.get_task("task-001")

        assert len(sleep_calls) == 0

    @pytest.mark.asyncio
    async def test_write_through_add_task(self, tmp_path: Path) -> None:
        """add_task blocks until WAL confirms write."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        bridge = InMemoryBridge(data={"id": "new-1", "name": "Test"})
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

        bridge = InMemoryBridge(data={"id": "task-001", "name": "Test"})
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
            "omnifocus_operator.repository.hybrid.asyncio.sleep", side_effect=tracking_sleep
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
        bridge = InMemoryBridge(data={"id": "new-task-1", "name": "Buy milk"}, wal_path=wal_path)
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
        from omnifocus_operator.contracts.use_cases.add_task import AddTaskRepoResult

        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = str(db_path) + "-wal"
        bridge = InMemoryBridge(data={"id": "new-task-1", "name": "Buy milk"}, wal_path=wal_path)
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
        bridge = InMemoryBridge(data={"id": "t1", "name": "Test"}, wal_path=wal_path)
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
        bridge = InMemoryBridge(data={"id": "t1", "name": "Test"}, wal_path=wal_path)
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
        bridge = InMemoryBridge(data={"id": "t1", "name": "Test"}, wal_path=wal_path)
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
    async def test_found_returns_task_with_all_fields(self, tmp_path: Path) -> None:
        """Found task returns a complete Task model with all fields populated."""
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        task = await repo.get_task("task-abc")

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
    async def test_not_found_returns_none(self, minimal_task_repo: HybridRepository) -> None:
        result = await minimal_task_repo.get_task("nonexistent-id")
        assert result is None

    @pytest.mark.asyncio
    async def test_task_with_project_parent_ref(self, tmp_path: Path) -> None:
        """Task in a project gets ParentRef with type='project'."""
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        task = await repo.get_task("task-in-proj")

        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "project"
        assert task.parent.id == "proj-001"
        assert task.parent.name == "Test Project"

    @pytest.mark.asyncio
    async def test_task_with_task_parent_ref(self, tmp_path: Path) -> None:
        """Subtask gets ParentRef with type='task'."""
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        task = await repo.get_task("subtask-1")

        assert task is not None
        assert task.parent is not None
        assert task.parent.type == "task"
        assert task.parent.id == "parent-task-1"
        assert task.parent.name == "Parent Task"

    @pytest.mark.asyncio
    async def test_inbox_task_parent_none(self, tmp_path: Path) -> None:
        """Inbox task (no project, no parent) has parent=None."""
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"persistentIdentifier": "inbox-task", "inInbox": 1})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        task = await repo.get_task("inbox-task")

        assert task is not None
        assert task.parent is None

    @pytest.mark.asyncio
    async def test_task_with_tags(self, tmp_path: Path) -> None:
        """Task tags are included in get_task result."""
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        task = await repo.get_task("tagged-task")

        assert task is not None
        assert len(task.tags) == 2
        tag_names = {t.name for t in task.tags}
        assert tag_names == {"Errand", "Home"}

    @pytest.mark.asyncio
    async def test_does_not_return_project_as_task(self, tmp_path: Path) -> None:
        """A project's task row is excluded from get_task (has ProjectInfo)."""
        db_path = create_test_db(
            tmp_path,
            projects=[_minimal_project({"persistentIdentifier": "proj-as-task"})],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_task("proj-as-task")
        assert result is None


class TestGetProject:
    """Tests for HybridRepository.get_project() -- single project lookup by ID."""

    @pytest.mark.asyncio
    async def test_found_returns_project_with_all_fields(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        proj = await repo.get_project("proj-xyz")

        assert proj is not None
        assert proj.id == "proj-xyz"
        assert proj.name == "My Project"
        assert proj.url == "omnifocus:///project/proj-xyz"
        assert proj.review_interval.steps == 2
        assert proj.review_interval.unit == "weeks"
        assert proj.next_task == "next-1"
        assert proj.folder == "fold-1"

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, tmp_path: Path) -> None:
        db_path = create_test_db(tmp_path, projects=[_minimal_project()])
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_project("nonexistent-id")
        assert result is None


class TestGetTag:
    """Tests for HybridRepository.get_tag() -- single tag lookup by ID."""

    @pytest.mark.asyncio
    async def test_found_returns_tag_with_all_fields(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
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
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        tag = await repo.get_tag("tag-xyz")

        assert tag is not None
        assert tag.id == "tag-xyz"
        assert tag.name == "Errands"
        assert tag.url == "omnifocus:///tag/tag-xyz"
        assert tag.children_are_mutually_exclusive is True
        assert tag.parent == "tag-parent"
        assert tag.added is not None
        assert tag.modified is not None

    @pytest.mark.asyncio
    async def test_not_found_returns_none(self, tmp_path: Path) -> None:
        db_path = create_test_db(tmp_path, tags=[_minimal_tag()])
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_tag("nonexistent-id")
        assert result is None


# ============================================================================
# GAP CLOSURE: Note encoding via plainTextNote
# ============================================================================


class TestPlainTextNoteEncoding:
    """Notes should be read from plainTextNote column, not noteXMLData."""

    @pytest.mark.asyncio
    async def test_task_reads_plain_text_note(self, tmp_path: Path) -> None:
        """Task with plainTextNote reads as clean text (no XML artifacts).

        Crucially, noteXMLData is NOT set -- proves we read from plainTextNote.
        """
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "plainTextNote": "Remember oat milk\nAnd eggs",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.tasks[0].note == "Remember oat milk\nAnd eggs"

    @pytest.mark.asyncio
    async def test_task_null_plain_text_note(self, minimal_task_repo: HybridRepository) -> None:
        """Task with NULL plainTextNote reads as empty string."""
        result = await minimal_task_repo.get_all()
        assert result.tasks[0].note == ""

    @pytest.mark.asyncio
    async def test_project_reads_plain_text_note(self, tmp_path: Path) -> None:
        """Project with plainTextNote reads as clean text."""
        db_path = create_test_db(
            tmp_path,
            projects=[
                _minimal_project(
                    {
                        "plainTextNote": "Project notes here",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        assert result.projects[0].note == "Project notes here"


# ============================================================================
# GAP CLOSURE: Local datetime parsing (DST-aware)
# ============================================================================


class TestLocalDatetimeParsing:
    """dateDue, dateToStart, datePlanned should be parsed as local time with DST."""

    @pytest.mark.asyncio
    async def test_due_date_local_time_winter(self, tmp_path: Path) -> None:
        """dateDue as local-time ISO string in winter converts to UTC correctly."""
        from zoneinfo import ZoneInfo

        # London winter: UTC+0, so local 10:00 = UTC 10:00
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "dateDue": "2026-01-15T10:00:00.000",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        with patch(
            "omnifocus_operator.repository.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.year == 2026
        assert task.due_date.month == 1
        assert task.due_date.day == 15
        assert task.due_date.hour == 10  # UTC+0 in winter
        assert task.due_date.minute == 0

    @pytest.mark.asyncio
    async def test_due_date_local_time_summer_dst(self, tmp_path: Path) -> None:
        """dateDue as local-time ISO string in summer (BST) converts to UTC correctly."""
        from zoneinfo import ZoneInfo

        # London summer (BST): UTC+1, so local 10:00 = UTC 09:00
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "dateDue": "2026-07-15T10:00:00.000",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        with patch(
            "omnifocus_operator.repository.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.hour == 9  # BST is UTC+1, so 10:00 BST = 09:00 UTC

    @pytest.mark.asyncio
    async def test_defer_date_local_time(self, tmp_path: Path) -> None:
        """dateToStart stored as local-time ISO text converts to UTC correctly."""
        from zoneinfo import ZoneInfo

        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "dateToStart": "2026-07-15T14:00:00.000",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        with patch(
            "omnifocus_operator.repository.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await repo.get_all()
        task = result.tasks[0]

        assert task.defer_date is not None
        assert task.defer_date.hour == 13  # 14:00 BST = 13:00 UTC

    @pytest.mark.asyncio
    async def test_planned_date_local_time(self, tmp_path: Path) -> None:
        """datePlanned stored as local-time ISO text converts to UTC correctly."""
        from zoneinfo import ZoneInfo

        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "datePlanned": "2026-01-20T08:00:00.000",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        with patch(
            "omnifocus_operator.repository.hybrid._LOCAL_TZ",
            ZoneInfo("Europe/London"),
        ):
            result = await repo.get_all()
        task = result.tasks[0]

        assert task.planned_date is not None
        assert task.planned_date.hour == 8  # UTC+0 in winter
        assert task.planned_date.day == 20

    @pytest.mark.asyncio
    async def test_effective_dates_still_use_cf_epoch(self, tmp_path: Path) -> None:
        """effectiveDateDue stored as CF epoch integer still parses correctly (regression)."""
        target_dt = datetime(2026, 2, 20, 15, 0, 0, tzinfo=UTC)
        cf_value = _cf_epoch(target_dt)
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "effectiveDateDue": cf_value,
                        "effectiveDateToStart": cf_value,
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        task = result.tasks[0]

        assert task.effective_due_date is not None
        assert task.effective_due_date.year == 2026
        assert task.effective_due_date.month == 2
        assert task.effective_due_date.day == 20
        assert task.effective_due_date.hour == 15
        assert task.effective_defer_date is not None

    @pytest.mark.asyncio
    async def test_date_added_modified_cf_epoch_regression(self, tmp_path: Path) -> None:
        """dateAdded/dateModified as CF epoch float still parse correctly (regression)."""
        target_dt = datetime(2026, 3, 1, 12, 30, 0, tzinfo=UTC)
        cf_value = _cf_epoch(target_dt)
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "dateAdded": cf_value,
                        "dateModified": cf_value,
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path, bridge=InMemoryBridge())
        result = await repo.get_all()
        task = result.tasks[0]

        assert task.added is not None
        assert task.added.year == 2026
        assert task.added.month == 3
        assert task.added.day == 1
        assert task.added.hour == 12
        assert task.modified is not None
        assert task.modified.hour == 12
