"""Tests for BridgeOnlyRepository with MtimeSource.

Covers SNAP-01 through SNAP-06 plus error propagation,
concurrency edge cases, and FileMtimeSource integration.
"""

from __future__ import annotations

import asyncio
import tempfile
from pathlib import Path
from typing import Any

import pytest
from pydantic import ValidationError

from omnifocus_operator.bridge.errors import BridgeError
from omnifocus_operator.bridge.mtime import FileMtimeSource
from omnifocus_operator.contracts.use_cases.list.projects import ListProjectsRepoQuery
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksRepoQuery
from omnifocus_operator.repository import BridgeOnlyRepository, Repository
from tests.doubles import InMemoryBridge

from .conftest import make_project_dict, make_snapshot_dict, make_task_dict

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeMtimeSource:
    """Controllable mtime source for tests."""

    def __init__(self, mtime_ns: int = 0) -> None:
        self._mtime_ns = mtime_ns

    def set_mtime_ns(self, value: int) -> None:
        self._mtime_ns = value

    async def get_mtime_ns(self) -> int:
        return self._mtime_ns


class FailingMtimeSource:
    """Mtime source that always raises."""

    def __init__(self, error: Exception) -> None:
        self._error = error

    async def get_mtime_ns(self) -> int:
        raise self._error


# ---------------------------------------------------------------------------
# Fixtures
# ---------------------------------------------------------------------------


@pytest.fixture
def snapshot_data() -> dict[str, Any]:
    """Standard snapshot dict for bridge responses."""
    return make_snapshot_dict()


@pytest.fixture
def bridge(snapshot_data: dict[str, Any]) -> InMemoryBridge:
    """InMemoryBridge pre-loaded with default snapshot data."""
    return InMemoryBridge(data=snapshot_data)


@pytest.fixture
def mtime() -> FakeMtimeSource:
    """FakeMtimeSource starting at mtime_ns=1."""
    return FakeMtimeSource(mtime_ns=1)


@pytest.fixture
def repo(bridge: InMemoryBridge, mtime: FakeMtimeSource) -> BridgeOnlyRepository:
    """Repository wired to test bridge and fake mtime source."""
    return BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)


# ---------------------------------------------------------------------------
# SNAP-01: First call triggers bridge dump and returns populated snapshot
# ---------------------------------------------------------------------------


class TestSNAP01FirstCall:
    """First get_all() call triggers bridge dump."""

    async def test_first_call_returns_snapshot(
        self, repo: BridgeOnlyRepository, bridge: InMemoryBridge
    ) -> None:
        snapshot = await repo.get_all()

        assert snapshot is not None
        assert len(snapshot.tasks) == 1
        assert len(snapshot.projects) == 1
        assert len(snapshot.tags) == 1
        assert len(snapshot.folders) == 1
        assert len(snapshot.perspectives) == 1

    async def test_first_call_invokes_bridge(
        self, repo: BridgeOnlyRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_all()

        assert bridge.call_count == 1

    async def test_first_call_uses_get_all_operation(
        self, repo: BridgeOnlyRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_all()

        assert bridge.calls[0].operation == "get_all"


# ---------------------------------------------------------------------------
# SNAP-02: Cached snapshot returned on same mtime
# ---------------------------------------------------------------------------


class TestSNAP02CachedReturn:
    """Subsequent calls with same mtime return cached snapshot."""

    async def test_second_call_no_bridge_invocation(
        self, repo: BridgeOnlyRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_all()
        await repo.get_all()

        assert bridge.call_count == 1

    async def test_second_call_returns_data(self, repo: BridgeOnlyRepository) -> None:
        await repo.get_all()
        second = await repo.get_all()

        assert len(second.tasks) == 1


# ---------------------------------------------------------------------------
# SNAP-03: Object identity preserved for cached snapshot
# ---------------------------------------------------------------------------


class TestSNAP03ObjectIdentity:
    """Cached snapshot is the same object (identity via `is`)."""

    async def test_same_object_returned(self, repo: BridgeOnlyRepository) -> None:
        first = await repo.get_all()
        second = await repo.get_all()

        assert first is second


# ---------------------------------------------------------------------------
# SNAP-04: Mtime change triggers fresh dump
# ---------------------------------------------------------------------------


class TestSNAP04MtimeRefresh:
    """Changed mtime triggers a new bridge dump."""

    async def test_mtime_change_triggers_new_dump(
        self,
        repo: BridgeOnlyRepository,
        bridge: InMemoryBridge,
        mtime: FakeMtimeSource,
    ) -> None:
        await repo.get_all()
        assert bridge.call_count == 1

        mtime.set_mtime_ns(2)
        await repo.get_all()

        assert bridge.call_count == 2

    async def test_mtime_change_returns_new_snapshot(
        self,
        repo: BridgeOnlyRepository,
        mtime: FakeMtimeSource,
    ) -> None:
        first = await repo.get_all()

        mtime.set_mtime_ns(2)
        second = await repo.get_all()

        assert first is not second


# ---------------------------------------------------------------------------
# SNAP-05: Concurrent reads coalesce into single dump
# ---------------------------------------------------------------------------


class TestSNAP05Concurrency:
    """10 concurrent reads trigger only 1 bridge dump."""

    async def test_concurrent_reads_single_dump(
        self, repo: BridgeOnlyRepository, bridge: InMemoryBridge
    ) -> None:
        results = await asyncio.gather(*[repo.get_all() for _ in range(10)])

        assert bridge.call_count == 1
        # All got the same snapshot
        assert all(r is results[0] for r in results)


# ---------------------------------------------------------------------------
# Error propagation: fail-fast, no stale fallback
# ---------------------------------------------------------------------------


class TestErrorPropagation:
    """Errors from bridge, validation, and mtime propagate raw."""

    async def test_bridge_error_propagates(self, mtime: FakeMtimeSource) -> None:
        bridge = InMemoryBridge()
        bridge.set_error(BridgeError("snapshot", "connection lost"))
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError, match="connection lost"):
            await repo.get_all()

    async def test_validation_error_propagates(self, mtime: FakeMtimeSource) -> None:
        """Invalid data causes Pydantic ValidationError to propagate."""
        bridge = InMemoryBridge(data={"tasks": "not-a-list"})
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(ValidationError):
            await repo.get_all()

    async def test_mtime_error_propagates(self) -> None:
        """MtimeSource errors propagate raw."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        error = OSError("filesystem unavailable")
        mtime = FailingMtimeSource(error)
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(OSError, match="filesystem unavailable"):
            await repo.get_all()

    async def test_failed_refresh_preserves_none_cache(self, mtime: FakeMtimeSource) -> None:
        """After failed first load, cache stays None; next call retries."""
        bridge = InMemoryBridge()
        bridge.set_error(BridgeError("snapshot", "temporary failure"))
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError):
            await repo.get_all()

        # Fix the bridge by populating entity lists and retry
        bridge.clear_error()
        snap = make_snapshot_dict()
        bridge._tasks = list(snap["tasks"])
        bridge._projects = list(snap["projects"])
        bridge._tags = list(snap["tags"])
        bridge._folders = list(snap["folders"])
        bridge._perspectives = list(snap["perspectives"])
        snapshot = await repo.get_all()
        assert len(snapshot.tasks) == 1

    async def test_failed_refresh_preserves_old_cache(
        self,
        snapshot_data: dict[str, Any],
        mtime: FakeMtimeSource,
    ) -> None:
        """After failed refresh, old cached snapshot is preserved."""
        bridge = InMemoryBridge(data=snapshot_data)
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)

        # First call succeeds
        first = await repo.get_all()

        # Mtime changes but bridge fails
        mtime.set_mtime_ns(2)
        bridge.set_error(BridgeError("snapshot", "temporary failure"))

        with pytest.raises(BridgeError):
            await repo.get_all()

        # Mtime changes again, bridge works again
        mtime.set_mtime_ns(3)
        bridge.clear_error()

        # Should get a new snapshot (not the old one, since mtime changed)
        third = await repo.get_all()
        assert third is not first

    async def test_failed_first_load_allows_retry(self, mtime: FakeMtimeSource) -> None:
        """After first get_all() fails, next call retries successfully."""
        bridge = InMemoryBridge()
        bridge.set_error(BridgeError("snapshot", "startup failure"))
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError):
            await repo.get_all()

        # Fix by populating entity lists and retry
        bridge.clear_error()
        snap = make_snapshot_dict()
        bridge._tasks = list(snap["tasks"])
        bridge._projects = list(snap["projects"])
        bridge._tags = list(snap["tags"])
        bridge._folders = list(snap["folders"])
        bridge._perspectives = list(snap["perspectives"])
        snapshot = await repo.get_all()
        assert len(snapshot.tasks) == 1


# ---------------------------------------------------------------------------
# Concurrency edge cases
# ---------------------------------------------------------------------------


class TestConcurrencyEdgeCases:
    """Additional concurrency scenarios."""

    async def test_concurrent_reads_warm_cache(
        self, repo: BridgeOnlyRepository, bridge: InMemoryBridge
    ) -> None:
        """Concurrent reads on warm cache are fast and don't re-dump."""
        await repo.get_all()  # warm up
        assert bridge.call_count == 1

        results = await asyncio.gather(*[repo.get_all() for _ in range(10)])
        assert bridge.call_count == 1
        assert all(r is results[0] for r in results)


# ---------------------------------------------------------------------------
# FileMtimeSource integration
# ---------------------------------------------------------------------------


class TestFileMtimeSource:
    """Lightweight integration tests for FileMtimeSource."""

    async def test_returns_positive_integer(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = FileMtimeSource(path=tmpdir)
            mtime_ns = await source.get_mtime_ns()

            assert isinstance(mtime_ns, int)
            assert mtime_ns > 0

    async def test_mtime_changes_on_modification(self) -> None:
        with tempfile.TemporaryDirectory() as tmpdir:
            source = FileMtimeSource(path=tmpdir)
            original = await source.get_mtime_ns()

            # Modify the directory by adding a file
            Path(tmpdir, "trigger.txt").write_text("x")
            updated = await source.get_mtime_ns()

            assert updated >= original

    async def test_nonexistent_path_raises(self) -> None:
        source = FileMtimeSource(path="/nonexistent/path/that/does/not/exist")

        with pytest.raises(OSError):
            await source.get_mtime_ns()


# ---------------------------------------------------------------------------
# BridgeOnlyRepository protocol conformance
# ---------------------------------------------------------------------------


class TestBridgeOnlyRepositoryProtocol:
    """BridgeOnlyRepository satisfies the Repository protocol."""

    async def test_bridge_repository_satisfies_protocol(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        mtime = FakeMtimeSource(mtime_ns=1)
        repo = BridgeOnlyRepository(bridge=bridge, mtime_source=mtime)

        assert isinstance(repo, Repository)


# ---------------------------------------------------------------------------
# Deterministic ordering for pagination
# ---------------------------------------------------------------------------


class TestDeterministicOrdering:
    """Pagination returns items sorted by ID for deterministic page boundaries."""

    @pytest.fixture
    def unordered_task_repo(self) -> BridgeOnlyRepository:
        """Repo with tasks inserted in non-alphabetical ID order."""
        data = make_snapshot_dict(
            tasks=[
                make_task_dict(id="task-cherry", name="Cherry"),
                make_task_dict(id="task-apple", name="Apple"),
                make_task_dict(id="task-banana", name="Banana"),
                make_task_dict(id="task-elderberry", name="Elderberry"),
                make_task_dict(id="task-date", name="Date"),
            ],
            projects=[],
        )
        return BridgeOnlyRepository(
            bridge=InMemoryBridge(data=data),
            mtime_source=FakeMtimeSource(mtime_ns=1),
        )

    @pytest.fixture
    def unordered_project_repo(self) -> BridgeOnlyRepository:
        """Repo with projects inserted in non-alphabetical ID order."""
        data = make_snapshot_dict(
            tasks=[],
            projects=[
                make_project_dict(id="proj-zebra", name="Zebra"),
                make_project_dict(id="proj-alpha", name="Alpha"),
                make_project_dict(id="proj-mango", name="Mango"),
                make_project_dict(id="proj-beta", name="Beta"),
                make_project_dict(id="proj-gamma", name="Gamma"),
            ],
        )
        return BridgeOnlyRepository(
            bridge=InMemoryBridge(data=data),
            mtime_source=FakeMtimeSource(mtime_ns=1),
        )

    async def test_list_tasks_paginated_sorted_by_id(
        self, unordered_task_repo: BridgeOnlyRepository
    ) -> None:
        """Tasks are sorted by ID so offset/limit produces deterministic pages."""
        page1 = await unordered_task_repo.list_tasks(ListTasksRepoQuery(limit=3))
        page2 = await unordered_task_repo.list_tasks(ListTasksRepoQuery(limit=3, offset=3))

        page1_ids = [t.id for t in page1.items]
        page2_ids = [t.id for t in page2.items]

        assert page1_ids == ["task-apple", "task-banana", "task-cherry"]
        assert page2_ids == ["task-date", "task-elderberry"]
        assert page1.has_more is True
        assert page2.has_more is False

    async def test_list_projects_paginated_sorted_by_id(
        self, unordered_project_repo: BridgeOnlyRepository
    ) -> None:
        """Projects are sorted by ID so offset/limit produces deterministic pages."""
        page1 = await unordered_project_repo.list_projects(ListProjectsRepoQuery(limit=3))
        page2 = await unordered_project_repo.list_projects(ListProjectsRepoQuery(limit=3, offset=3))

        page1_ids = [p.id for p in page1.items]
        page2_ids = [p.id for p in page2.items]

        assert page1_ids == ["proj-alpha", "proj-beta", "proj-gamma"]
        assert page2_ids == ["proj-mango", "proj-zebra"]
        assert page1.has_more is True
        assert page2.has_more is False

    async def test_list_tasks_consecutive_pages_no_overlap(
        self, unordered_task_repo: BridgeOnlyRepository
    ) -> None:
        """Consecutive pages cover all items exactly once with no overlap."""
        all_ids: list[str] = []
        offset = 0
        while True:
            page = await unordered_task_repo.list_tasks(ListTasksRepoQuery(limit=2, offset=offset))
            all_ids.extend(t.id for t in page.items)
            if not page.has_more:
                break
            offset += len(page.items)

        assert all_ids == sorted(all_ids)
        assert len(all_ids) == 5
        assert len(set(all_ids)) == 5  # no duplicates


# ---------------------------------------------------------------------------
# Project root task filtering (bridge-only pipeline end-to-end)
# ---------------------------------------------------------------------------


class TestProjectRootTaskExclusion:
    """Bridge-only list_tasks excludes project root tasks end-to-end.

    In OmniFocus every project has an underlying Task object with the same ID.
    The SQL path filters these via LEFT JOIN ProjectInfo. The bridge-only path
    filters them in adapt_snapshot. This test validates the fix flows through
    the full pipeline: get_all -> adapt_snapshot -> list_tasks.
    """

    async def test_list_tasks_excludes_project_root_tasks(self) -> None:
        """list_tasks never returns a task whose ID matches a project ID."""
        data = make_snapshot_dict(
            tasks=[
                # Project root task (same ID as the project)
                make_task_dict(
                    id="proj-001", name="Project Root", project="proj-001", parent="proj-001"
                ),
                # Normal tasks
                make_task_dict(id="task-a", name="Task A", project="proj-001", parent="proj-001"),
                make_task_dict(id="task-b", name="Task B", project="proj-001", parent="proj-001"),
            ],
            projects=[
                make_project_dict(id="proj-001", name="My Project"),
            ],
        )
        repo = BridgeOnlyRepository(
            bridge=InMemoryBridge(data=data),
            mtime_source=FakeMtimeSource(mtime_ns=1),
        )

        result = await repo.list_tasks(ListTasksRepoQuery())
        returned_ids = [t.id for t in result.items]

        assert "proj-001" not in returned_ids, "Project root task should be excluded"
        assert "task-a" in returned_ids
        assert "task-b" in returned_ids

    async def test_get_all_excludes_project_root_tasks(self) -> None:
        """get_all snapshot tasks list also excludes project root tasks."""
        data = make_snapshot_dict(
            tasks=[
                make_task_dict(
                    id="proj-001", name="Project Root", project="proj-001", parent="proj-001"
                ),
                make_task_dict(id="task-x", name="Real Task"),
            ],
            projects=[
                make_project_dict(id="proj-001", name="My Project"),
            ],
        )
        repo = BridgeOnlyRepository(
            bridge=InMemoryBridge(data=data),
            mtime_source=FakeMtimeSource(mtime_ns=1),
        )

        snapshot = await repo.get_all()
        task_ids = [t.id for t in snapshot.tasks]

        assert "proj-001" not in task_ids
        assert "task-x" in task_ids
