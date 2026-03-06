"""Tests for OmniFocusRepository with MtimeSource.

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

from omnifocus_operator.bridge._errors import BridgeError
from omnifocus_operator.bridge._in_memory import InMemoryBridge
from omnifocus_operator.repository import FileMtimeSource, OmniFocusRepository

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
def repo(bridge: InMemoryBridge, mtime: FakeMtimeSource) -> OmniFocusRepository:
    """Repository wired to test bridge and fake mtime source."""
    return OmniFocusRepository(bridge=bridge, mtime_source=mtime)


# ---------------------------------------------------------------------------
# SNAP-01: First call triggers bridge dump and returns populated snapshot
# ---------------------------------------------------------------------------


class TestSNAP01FirstCall:
    """First get_snapshot() call triggers bridge dump."""

    async def test_first_call_returns_snapshot(
        self, repo: OmniFocusRepository, bridge: InMemoryBridge
    ) -> None:
        snapshot = await repo.get_snapshot()

        assert snapshot is not None
        assert len(snapshot.tasks) == 1
        assert len(snapshot.projects) == 1
        assert len(snapshot.tags) == 1
        assert len(snapshot.folders) == 1
        assert len(snapshot.perspectives) == 1

    async def test_first_call_invokes_bridge(
        self, repo: OmniFocusRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_snapshot()

        assert bridge.call_count == 1

    async def test_first_call_uses_snapshot_operation(
        self, repo: OmniFocusRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_snapshot()

        assert bridge.calls[0].operation == "snapshot"


# ---------------------------------------------------------------------------
# SNAP-02: Cached snapshot returned on same mtime
# ---------------------------------------------------------------------------


class TestSNAP02CachedReturn:
    """Subsequent calls with same mtime return cached snapshot."""

    async def test_second_call_no_bridge_invocation(
        self, repo: OmniFocusRepository, bridge: InMemoryBridge
    ) -> None:
        await repo.get_snapshot()
        await repo.get_snapshot()

        assert bridge.call_count == 1

    async def test_second_call_returns_data(self, repo: OmniFocusRepository) -> None:
        await repo.get_snapshot()
        second = await repo.get_snapshot()

        assert len(second.tasks) == 1


# ---------------------------------------------------------------------------
# SNAP-03: Object identity preserved for cached snapshot
# ---------------------------------------------------------------------------


class TestSNAP03ObjectIdentity:
    """Cached snapshot is the same object (identity via `is`)."""

    async def test_same_object_returned(self, repo: OmniFocusRepository) -> None:
        first = await repo.get_snapshot()
        second = await repo.get_snapshot()

        assert first is second


# ---------------------------------------------------------------------------
# SNAP-04: Mtime change triggers fresh dump
# ---------------------------------------------------------------------------


class TestSNAP04MtimeRefresh:
    """Changed mtime triggers a new bridge dump."""

    async def test_mtime_change_triggers_new_dump(
        self,
        repo: OmniFocusRepository,
        bridge: InMemoryBridge,
        mtime: FakeMtimeSource,
    ) -> None:
        await repo.get_snapshot()
        assert bridge.call_count == 1

        mtime.set_mtime_ns(2)
        await repo.get_snapshot()

        assert bridge.call_count == 2

    async def test_mtime_change_returns_new_snapshot(
        self,
        repo: OmniFocusRepository,
        mtime: FakeMtimeSource,
    ) -> None:
        first = await repo.get_snapshot()

        mtime.set_mtime_ns(2)
        second = await repo.get_snapshot()

        assert first is not second


# ---------------------------------------------------------------------------
# SNAP-05: Concurrent reads coalesce into single dump
# ---------------------------------------------------------------------------


class TestSNAP05Concurrency:
    """10 concurrent reads trigger only 1 bridge dump."""

    async def test_concurrent_reads_single_dump(
        self, repo: OmniFocusRepository, bridge: InMemoryBridge
    ) -> None:
        results = await asyncio.gather(*[repo.get_snapshot() for _ in range(10)])

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
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError, match="connection lost"):
            await repo.get_snapshot()

    async def test_validation_error_propagates(self, mtime: FakeMtimeSource) -> None:
        """Invalid data causes Pydantic ValidationError to propagate."""
        bridge = InMemoryBridge(data={"tasks": "not-a-list"})
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(ValidationError):
            await repo.get_snapshot()

    async def test_mtime_error_propagates(self) -> None:
        """MtimeSource errors propagate raw."""
        bridge = InMemoryBridge(data=make_snapshot_dict())
        error = OSError("filesystem unavailable")
        mtime = FailingMtimeSource(error)
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(OSError, match="filesystem unavailable"):
            await repo.get_snapshot()

    async def test_failed_refresh_preserves_none_cache(self, mtime: FakeMtimeSource) -> None:
        """After failed first load, cache stays None; next call retries."""
        bridge = InMemoryBridge()
        bridge.set_error(BridgeError("snapshot", "temporary failure"))
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError):
            await repo.get_snapshot()

        # Fix the bridge and retry
        bridge.clear_error()
        bridge._data = make_snapshot_dict()
        snapshot = await repo.get_snapshot()
        assert len(snapshot.tasks) == 1

    async def test_failed_refresh_preserves_old_cache(
        self,
        snapshot_data: dict[str, Any],
        mtime: FakeMtimeSource,
    ) -> None:
        """After failed refresh, old cached snapshot is preserved."""
        bridge = InMemoryBridge(data=snapshot_data)
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)

        # First call succeeds
        first = await repo.get_snapshot()

        # Mtime changes but bridge fails
        mtime.set_mtime_ns(2)
        bridge.set_error(BridgeError("snapshot", "temporary failure"))

        with pytest.raises(BridgeError):
            await repo.get_snapshot()

        # Mtime changes again, bridge works again
        mtime.set_mtime_ns(3)
        bridge.clear_error()

        # Should get a new snapshot (not the old one, since mtime changed)
        third = await repo.get_snapshot()
        assert third is not first

    async def test_failed_first_load_allows_retry(self, mtime: FakeMtimeSource) -> None:
        """After first get_snapshot() fails, next call retries successfully."""
        bridge = InMemoryBridge()
        bridge.set_error(BridgeError("snapshot", "startup failure"))
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)

        with pytest.raises(BridgeError):
            await repo.get_snapshot()

        # Fix and retry
        bridge.clear_error()
        bridge._data = make_snapshot_dict()
        snapshot = await repo.get_snapshot()
        assert len(snapshot.tasks) == 1


# ---------------------------------------------------------------------------
# Concurrency edge cases
# ---------------------------------------------------------------------------


class TestConcurrencyEdgeCases:
    """Additional concurrency scenarios."""

    async def test_concurrent_reads_warm_cache(
        self, repo: OmniFocusRepository, bridge: InMemoryBridge
    ) -> None:
        """Concurrent reads on warm cache are fast and don't re-dump."""
        await repo.get_snapshot()  # warm up
        assert bridge.call_count == 1

        results = await asyncio.gather(*[repo.get_snapshot() for _ in range(10)])
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
