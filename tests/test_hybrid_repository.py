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

from omnifocus_operator.models.snapshot import AllEntities
from omnifocus_operator.repository.hybrid import HybridRepository
from omnifocus_operator.repository.protocol import Repository

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
                context TEXT
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
                "INSERT INTO TaskToTag (task, context) VALUES (?, ?)",
                [tt["task"], tt["context"]],
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
# TESTS
# ============================================================================


class TestProtocol:
    def test_satisfies_repository_protocol(self, tmp_path: Path) -> None:
        db_path = create_test_db(tmp_path)
        repo = HybridRepository(db_path=db_path)
        assert isinstance(repo, Repository)


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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert isinstance(result, AllEntities)
        assert len(result.tasks) == 1
        assert len(result.projects) == 1
        assert len(result.tags) == 1
        assert len(result.folders) == 1
        assert len(result.perspectives) == 1


class TestConnectionSemantics:
    def test_read_only_connection(self, tmp_path: Path) -> None:
        """Verify that the connection string contains ?mode=ro."""
        db_path = create_test_db(tmp_path)
        repo = HybridRepository(db_path=db_path)
        # Inspect the connection URI by calling _read_all and checking the path usage
        # We'll monkeypatch sqlite3.connect to capture the URI
        calls: list[str] = []
        original_connect = sqlite3.connect

        def capturing_connect(uri_str: str, **kwargs: Any) -> Any:
            calls.append(uri_str)
            return original_connect(uri_str, **kwargs)

        with patch("sqlite3.connect", side_effect=capturing_connect):
            repo._read_all()

        assert len(calls) == 1
        assert "?mode=ro" in calls[0]

    @pytest.mark.asyncio
    async def test_fresh_connection_per_read(self, tmp_path: Path) -> None:
        """Two consecutive get_all() calls create two separate connections."""
        db_path = create_test_db(tmp_path)
        repo = HybridRepository(db_path=db_path)
        call_count = 0
        original_connect = sqlite3.connect

        def counting_connect(uri_str: str, **kwargs: Any) -> Any:
            nonlocal call_count
            call_count += 1
            return original_connect(uri_str, **kwargs)

        with patch("sqlite3.connect", side_effect=counting_connect):
            await repo.get_all()
            await repo.get_all()

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
                        "noteXMLData": _make_note_xml("Remember oat milk"),
                        "flagged": 1,
                        "effectiveFlagged": 1,
                        "inInbox": 1,
                        "childrenCount": 3,
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path)
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
    async def test_task_dates_cf_epoch(self, tmp_path: Path) -> None:
        """CF epoch float timestamps parse to correct AwareDatetime."""
        target_dt = datetime(2026, 2, 20, 15, 15, 16, tzinfo=UTC)
        cf_value = _cf_epoch(target_dt)
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "dateDue": cf_value,
                        "dateToStart": cf_value,
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.year == 2026
        assert task.due_date.month == 2
        assert task.due_date.day == 20
        assert task.defer_date is not None
        assert task.defer_date.year == 2026

    @pytest.mark.asyncio
    async def test_task_dates_iso8601(self, tmp_path: Path) -> None:
        """ISO 8601 string timestamps parse to correct AwareDatetime."""
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "dateDue": "2026-02-16T22:00:00.000Z",
                        "dateToStart": "2026-01-10T09:00:00.000+00:00",
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        task = result.tasks[0]

        assert task.due_date is not None
        assert task.due_date.year == 2026
        assert task.due_date.month == 2
        assert task.due_date.day == 16
        assert task.defer_date is not None

    @pytest.mark.asyncio
    async def test_task_null_dates(self, tmp_path: Path) -> None:
        """NULL date columns produce None fields."""
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task()],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].urgency == "overdue"

    @pytest.mark.asyncio
    async def test_task_urgency_due_soon(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"overdue": 0, "dueSoon": 1})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].urgency == "due_soon"

    @pytest.mark.asyncio
    async def test_task_urgency_none(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"overdue": 0, "dueSoon": 0})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].urgency == "none"

    @pytest.mark.asyncio
    async def test_task_urgency_overdue_priority(self, tmp_path: Path) -> None:
        """Overdue takes priority over due_soon."""
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"overdue": 1, "dueSoon": 1})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].urgency == "overdue"

    @pytest.mark.asyncio
    async def test_task_availability_dropped(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"dateHidden": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_task_availability_completed(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"dateCompleted": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].availability == "completed"

    @pytest.mark.asyncio
    async def test_task_availability_blocked(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task({"blocked": 1})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].availability == "blocked"

    @pytest.mark.asyncio
    async def test_task_availability_available(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task()],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
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
                {"task": "t1", "context": "tag-a"},
                {"task": "t1", "context": "tag-b"},
            ],
        )
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        task = result.tasks[0]
        assert task.repetition_rule is not None
        assert task.repetition_rule.rule_string == "FREQ=WEEKLY;INTERVAL=1"
        assert task.repetition_rule.schedule_type == "regularly"
        assert task.repetition_rule.anchor_date_key == "due_date"
        assert task.repetition_rule.catch_up_automatically is True

    @pytest.mark.asyncio
    async def test_task_no_repetition_rule(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task()],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].repetition_rule is None


class TestTaskNotes:
    @pytest.mark.asyncio
    async def test_task_note_xml_extraction(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "noteXMLData": _make_note_xml("Buy oat milk and eggs"),
                    }
                )
            ],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].note == "Buy oat milk and eggs"

    @pytest.mark.asyncio
    async def test_task_note_null(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[_minimal_task()],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tasks[0].note == ""


class TestTaskRelationships:
    @pytest.mark.asyncio
    async def test_task_relationships(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tasks=[
                _minimal_task(
                    {
                        "containingProjectInfo": "proj-001",
                        "parent": "parent-task-001",
                    }
                )
            ],
            projects=[_minimal_project()],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        task = result.tasks[0]
        assert task.project == "proj-001"
        assert task.parent == "parent-task-001"


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
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.projects[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_project_availability_dropped_by_date_hidden(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[_minimal_project({"dateHidden": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.projects[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_project_availability_completed(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[_minimal_project({"dateCompleted": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.projects[0].availability == "blocked"

    @pytest.mark.asyncio
    async def test_project_availability_available(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            projects=[_minimal_project()],
        )
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tags[0].availability == "blocked"

    @pytest.mark.asyncio
    async def test_tag_availability_dropped(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tags=[_minimal_tag({"dateHidden": _NOW_CF})],
        )
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.tags[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_tag_availability_available(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            tags=[_minimal_tag()],
        )
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert result.folders[0].availability == "dropped"

    @pytest.mark.asyncio
    async def test_folder_availability_available(self, tmp_path: Path) -> None:
        db_path = create_test_db(
            tmp_path,
            folders=[_minimal_folder()],
        )
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        persp = result.perspectives[0]
        assert persp.id is None
        assert persp.builtin is True


class TestEdgeCases:
    @pytest.mark.asyncio
    async def test_empty_database(self, tmp_path: Path) -> None:
        db_path = create_test_db(tmp_path)
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
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
        repo = HybridRepository(db_path=db_path)
        result = await repo.get_all()
        assert len(result.tasks) == 1
        assert len(result.tags) == 1


class TestFreshness:
    """Tests for WAL-based freshness detection after TEMPORARY_simulate_write."""

    @pytest.mark.asyncio
    async def test_freshness_wal_polling(self, tmp_path: Path) -> None:
        """After simulate_write(), get_all() polls WAL mtime; fresh data after change."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        # Create a WAL file to simulate WAL presence
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        repo = HybridRepository(db_path=db_path)
        # First read to establish baseline
        await repo.get_all()

        # Simulate write -- captures current mtime
        repo.TEMPORARY_simulate_write()

        # Schedule a WAL mtime change after a short delay
        async def modify_wal() -> None:
            await asyncio.sleep(0.15)
            # Force a visible mtime change by writing to the file
            wal_path.write_bytes(b"changed")

        task = asyncio.create_task(modify_wal())
        # get_all() should poll and detect the change
        result = await repo.get_all()
        await task
        assert isinstance(result, AllEntities)
        assert len(result.tasks) == 1

    @pytest.mark.asyncio
    async def test_freshness_db_fallback(self, tmp_path: Path) -> None:
        """When WAL file does not exist, freshness uses main .db file mtime."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        # Ensure no WAL file
        wal_path = db_path.parent / (db_path.name + "-wal")
        if wal_path.exists():
            wal_path.unlink()

        repo = HybridRepository(db_path=db_path)
        await repo.get_all()
        repo.TEMPORARY_simulate_write()

        # Modify DB file mtime after short delay
        async def modify_db() -> None:
            await asyncio.sleep(0.15)
            db_path.write_bytes(db_path.read_bytes() + b"\x00")

        task = asyncio.create_task(modify_db())
        result = await repo.get_all()
        await task
        assert isinstance(result, AllEntities)

    @pytest.mark.asyncio
    async def test_freshness_timeout(self, tmp_path: Path) -> None:
        """If WAL mtime never changes within timeout, get_all() returns anyway."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        repo = HybridRepository(db_path=db_path)
        await repo.get_all()
        repo.TEMPORARY_simulate_write()

        # Don't modify WAL -- should timeout and return data anyway
        start = time.monotonic()
        result = await repo.get_all()
        elapsed = time.monotonic() - start

        # Should complete in ~2s (timeout), not immediately
        assert elapsed >= 1.5
        # But not much longer than 2s
        assert elapsed < 3.0
        # Data returned despite timeout
        assert isinstance(result, AllEntities)
        assert len(result.tasks) == 1

    @pytest.mark.asyncio
    async def test_freshness_poll_interval(self, tmp_path: Path) -> None:
        """Polling occurs at ~50ms intervals."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        repo = HybridRepository(db_path=db_path)
        await repo.get_all()
        repo.TEMPORARY_simulate_write()

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
            await repo.get_all()
        await task

        # All sleep calls should be 0.05 (50ms)
        assert len(sleep_calls) > 0
        for call in sleep_calls:
            assert call == pytest.approx(0.05)

    @pytest.mark.asyncio
    async def test_freshness_no_stale_flag_normal_read(self, tmp_path: Path) -> None:
        """Normal get_all() (no simulate_write) does NOT trigger freshness polling."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        repo = HybridRepository(db_path=db_path)

        sleep_calls: list[float] = []
        original_sleep = asyncio.sleep

        async def tracking_sleep(duration: float) -> None:
            sleep_calls.append(duration)
            await original_sleep(duration)

        with patch(
            "omnifocus_operator.repository.hybrid.asyncio.sleep", side_effect=tracking_sleep
        ):
            result = await repo.get_all()

        assert isinstance(result, AllEntities)
        # No polling should have occurred
        assert len(sleep_calls) == 0

    @pytest.mark.asyncio
    async def test_simulate_write_marks_stale(self, tmp_path: Path) -> None:
        """TEMPORARY_simulate_write() sets stale flag; next get_all() clears it."""
        db_path = create_test_db(tmp_path, tasks=[_minimal_task()])
        wal_path = db_path.parent / (db_path.name + "-wal")
        wal_path.touch()

        repo = HybridRepository(db_path=db_path)
        await repo.get_all()

        assert repo._stale is False
        repo.TEMPORARY_simulate_write()
        assert repo._stale is True

        # Modify WAL so freshness check passes quickly
        wal_path.write_bytes(b"modified")
        await repo.get_all()
        assert repo._stale is False

    def test_simulate_write_not_on_protocol(self) -> None:
        """TEMPORARY_simulate_write is on HybridRepository only, not on Repository protocol."""
        assert not hasattr(Repository, "TEMPORARY_simulate_write")
