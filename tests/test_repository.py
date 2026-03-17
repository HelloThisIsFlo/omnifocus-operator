"""Tests for BridgeRepository with MtimeSource.

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
from omnifocus_operator.bridge.in_memory import InMemoryBridge
from omnifocus_operator.bridge.mtime import FileMtimeSource
from omnifocus_operator.repository import BridgeRepository, Repository
from omnifocus_operator.repository.in_memory import InMemoryRepository

from .conftest import make_snapshot_dict

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
def repo(bridge: InMemoryBridge, mtime: FakeMtimeSource) -> BridgeRepository:
    """Repository wired to test bridge and fake mtime source."""
    return BridgeRepository(bridge=bridge, mtime_source=mtime)


# ---------------------------------------------------------------------------
# SNAP-01: First call triggers bridge dump and returns populated snapshot
# ---------------------------------------------------------------------------


class TestSNAP01FirstCall:
    """First get_all() call triggers bridge dump."""

    async def test_first_call_returns_snapshot(
        self, repo: BridgeRepository, bridge: InMemoryBridge
    ) -> None:
        snapshot = await repo.get_all()

        assert snapshot is not None
        assert len(snapshot.tasks) == 1
        assert len(snapshot.projects) == 1
        assert len(snapshot.tags) == 1
        assert len(snapshot.folders) == 1
        assert len(snapshot.perspectives) == 1

    async def test_first_call_invokes_bridge(
        self, repo: BridgeRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_all()

        assert bridge.call_count == 1

    async def test_first_call_uses_get_all_operation(
        self, repo: BridgeRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_all()

        assert bridge.calls[0].operation == "get_all"


# ---------------------------------------------------------------------------
# SNAP-02: Cached snapshot returned on same mtime
# ---------------------------------------------------------------------------


class TestSNAP02CachedReturn:
    """Subsequent calls with same mtime return cached snapshot."""

    async def test_second_call_no_bridge_invocation(
        self, repo: BridgeRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_all()
        await repo.get_all()

        assert bridge.call_count == 1

    async def test_second_call_returns_data(self, repo: BridgeRepository) -> None:
        await repo.get_all()
        second = await repo.get_all()

        assert len(second.tasks) == 1


# ---------------------------------------------------------------------------
# SNAP-03: Object identity preserved for cached snapshot
# ---------------------------------------------------------------------------


class TestSNAP03ObjectIdentity:
    """Cached snapshot is the same object (identity via `is`)."""

    async def test_same_object_returned(self, repo: BridgeRepository) -> None:
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
        repo: BridgeRepository,
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
        repo: BridgeRepository,
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
        self, repo: BridgeRepository, bridge: InMemoryBridge
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
        repo = BridgeRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError, match="connection lost"):
            await repo.get_all()

    async def test_validation_error_propagates(self, mtime: FakeMtimeSource) -> None:
        """Invalid data causes Pydantic ValidationError to propagate."""
        bridge = InMemoryBridge(data={"tasks": "not-a-list"})
        repo = BridgeRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(ValidationError):
            await repo.get_all()

    async def test_mtime_error_propagates(self) -> None:
        """MtimeSource errors propagate raw."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        error = OSError("filesystem unavailable")
        mtime = FailingMtimeSource(error)
        repo = BridgeRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(OSError, match="filesystem unavailable"):
            await repo.get_all()

    async def test_failed_refresh_preserves_none_cache(self, mtime: FakeMtimeSource) -> None:
        """After failed first load, cache stays None; next call retries."""
        bridge = InMemoryBridge()
        bridge.set_error(BridgeError("snapshot", "temporary failure"))
        repo = BridgeRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError):
            await repo.get_all()

        # Fix the bridge and retry
        bridge.clear_error()
        bridge._data = make_snapshot_dict()
        snapshot = await repo.get_all()
        assert len(snapshot.tasks) == 1

    async def test_failed_refresh_preserves_old_cache(
        self,
        snapshot_data: dict[str, Any],
        mtime: FakeMtimeSource,
    ) -> None:
        """After failed refresh, old cached snapshot is preserved."""
        bridge = InMemoryBridge(data=snapshot_data)
        repo = BridgeRepository(bridge=bridge, mtime_source=mtime)

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
        repo = BridgeRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError):
            await repo.get_all()

        # Fix and retry
        bridge.clear_error()
        bridge._data = make_snapshot_dict()
        snapshot = await repo.get_all()
        assert len(snapshot.tasks) == 1


# ---------------------------------------------------------------------------
# Concurrency edge cases
# ---------------------------------------------------------------------------


class TestConcurrencyEdgeCases:
    """Additional concurrency scenarios."""

    async def test_concurrent_reads_warm_cache(
        self, repo: BridgeRepository, bridge: InMemoryBridge
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
# InMemoryRepository
# ---------------------------------------------------------------------------


class TestInMemoryRepository:
    """InMemoryRepository returns pre-built snapshots and satisfies protocol."""

    async def test_satisfies_repository_protocol(self) -> None:
        from .conftest import make_snapshot

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)

        assert isinstance(repo, Repository)

    async def test_returns_snapshot(self) -> None:
        from .conftest import make_snapshot

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)

        result = await repo.get_all()

        assert result is snapshot

    async def test_bridge_repository_satisfies_protocol(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        mtime = FakeMtimeSource(mtime_ns=1)
        repo = BridgeRepository(bridge=bridge, mtime_source=mtime)

        assert isinstance(repo, Repository)


# ---------------------------------------------------------------------------
# InMemoryRepository -- add_task
# ---------------------------------------------------------------------------


class TestInMemoryAddTask:
    """Tests for InMemoryRepository.add_task (in-memory write for testing)."""

    async def test_add_task_returns_result(self) -> None:
        """add_task returns TaskCreateResult with success=True."""
        from omnifocus_operator.models.write import TaskCreateResult, TaskCreateSpec

        from .conftest import make_snapshot

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)

        spec = TaskCreateSpec(name="New task")
        result = await repo.add_task(spec)

        assert isinstance(result, TaskCreateResult)
        assert result.success is True
        assert result.name == "New task"
        assert result.id.startswith("mem-")

    async def test_add_task_appends_to_snapshot(self) -> None:
        """add_task appends the new task to the snapshot."""
        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_snapshot

        snapshot = make_snapshot()
        initial_count = len(snapshot.tasks)
        repo = InMemoryRepository(snapshot=snapshot)

        spec = TaskCreateSpec(name="New task")
        await repo.add_task(spec)

        updated_snapshot = await repo.get_all()
        assert len(updated_snapshot.tasks) == initial_count + 1
        new_task = updated_snapshot.tasks[-1]
        assert new_task.name == "New task"

    async def test_add_task_inbox_when_no_parent(self) -> None:
        """Task with no parent goes to inbox (in_inbox=True)."""
        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_snapshot

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)

        spec = TaskCreateSpec(name="Inbox task")
        result = await repo.add_task(spec)

        updated = await repo.get_all()
        new_task = next(t for t in updated.tasks if t.id == result.id)
        assert new_task.in_inbox is True

    async def test_add_task_with_parent(self) -> None:
        """Task with parent sets in_inbox=False."""
        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_snapshot

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)

        spec = TaskCreateSpec(name="Child task", parent="proj-001")
        result = await repo.add_task(spec)

        updated = await repo.get_all()
        new_task = next(t for t in updated.tasks if t.id == result.id)
        assert new_task.in_inbox is False

    async def test_add_task_generates_unique_ids(self) -> None:
        """Each add_task generates a unique ID."""
        from omnifocus_operator.models.write import TaskCreateSpec

        from .conftest import make_snapshot

        snapshot = make_snapshot()
        repo = InMemoryRepository(snapshot=snapshot)

        r1 = await repo.add_task(TaskCreateSpec(name="Task 1"))
        r2 = await repo.add_task(TaskCreateSpec(name="Task 2"))

        assert r1.id != r2.id


class TestInMemoryEditTaskLifecycle:
    """InMemoryRepository.edit_task lifecycle mutations."""

    async def test_lifecycle_complete_sets_availability(self) -> None:
        """edit_task with lifecycle='complete' sets availability to COMPLETED."""
        from omnifocus_operator.models.enums import Availability

        from .conftest import make_snapshot, make_task_dict

        snapshot = make_snapshot(tasks=[make_task_dict(id="task-001")])
        repo = InMemoryRepository(snapshot=snapshot)

        await repo.edit_task({"id": "task-001", "lifecycle": "complete"})
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.availability == Availability.COMPLETED

    async def test_lifecycle_drop_sets_availability(self) -> None:
        """edit_task with lifecycle='drop' sets availability to DROPPED."""
        from omnifocus_operator.models.enums import Availability

        from .conftest import make_snapshot, make_task_dict

        snapshot = make_snapshot(tasks=[make_task_dict(id="task-001")])
        repo = InMemoryRepository(snapshot=snapshot)

        await repo.edit_task({"id": "task-001", "lifecycle": "drop"})
        task = await repo.get_task("task-001")
        assert task is not None
        assert task.availability == Availability.DROPPED
