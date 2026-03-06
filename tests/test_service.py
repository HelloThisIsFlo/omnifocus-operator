"""Tests for OperatorService, ConstantMtimeSource, and bridge factory.

Covers the service layer (thin passthrough to repository), the constant
mtime source (always returns 0 for InMemoryBridge usage), and the bridge
factory function (creates the appropriate bridge implementation).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from pathlib import Path

from omnifocus_operator.bridge import BridgeError, InMemoryBridge, create_bridge
from omnifocus_operator.repository import (
    ConstantMtimeSource,
    MtimeSource,
    OmniFocusRepository,
)
from omnifocus_operator.service import OperatorService

from .conftest import make_snapshot_dict

# ---------------------------------------------------------------------------
# Test doubles
# ---------------------------------------------------------------------------


class FakeMtimeSource:
    """Controllable mtime source for tests."""

    def __init__(self, mtime_ns: int = 0) -> None:
        self._mtime_ns = mtime_ns

    async def get_mtime_ns(self) -> int:
        return self._mtime_ns


# ---------------------------------------------------------------------------
# OperatorService
# ---------------------------------------------------------------------------


class TestOperatorService:
    """OperatorService delegates to repository and passes through results."""

    async def test_get_all_data_returns_snapshot(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        mtime = FakeMtimeSource()
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)
        service = OperatorService(repository=repo)

        snapshot = await service.get_all_data()

        assert len(snapshot.tasks) == 1
        assert len(snapshot.projects) == 1
        assert len(snapshot.tags) == 1
        assert len(snapshot.folders) == 1
        assert len(snapshot.perspectives) == 1

    async def test_get_all_data_delegates_to_repository(self) -> None:
        bridge = InMemoryBridge(data=make_snapshot_dict())
        mtime = FakeMtimeSource()
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)
        service = OperatorService(repository=repo)

        await service.get_all_data()

        assert bridge.call_count == 1

    async def test_get_all_data_propagates_errors(self) -> None:
        bridge = InMemoryBridge()
        bridge.set_error(BridgeError("snapshot", "connection lost"))
        mtime = FakeMtimeSource()
        repo = OmniFocusRepository(bridge=bridge, mtime_source=mtime)
        service = OperatorService(repository=repo)

        with pytest.raises(BridgeError, match="connection lost"):
            await service.get_all_data()


# ---------------------------------------------------------------------------
# ConstantMtimeSource
# ---------------------------------------------------------------------------


class TestConstantMtimeSource:
    """ConstantMtimeSource always returns 0 and satisfies MtimeSource."""

    async def test_always_returns_zero(self) -> None:
        source = ConstantMtimeSource()

        first = await source.get_mtime_ns()
        second = await source.get_mtime_ns()

        assert first == 0
        assert second == 0

    async def test_satisfies_mtime_protocol(self) -> None:
        source = ConstantMtimeSource()

        assert isinstance(source, MtimeSource)


# ---------------------------------------------------------------------------
# Bridge factory (create_bridge)
# ---------------------------------------------------------------------------


class TestCreateBridge:
    """create_bridge() factory returns the correct bridge or raises."""

    def test_inmemory_returns_inmemory_bridge(self) -> None:
        bridge = create_bridge("inmemory")

        assert isinstance(bridge, InMemoryBridge)

    def test_simulator_returns_simulator_bridge(self) -> None:
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        bridge = create_bridge("simulator")
        assert isinstance(bridge, SimulatorBridge)

    def test_real_refused_during_pytest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """SAFE-01: create_bridge('real') is refused during automated testing."""
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))
        with pytest.raises(RuntimeError, match="PYTEST_CURRENT_TEST"):
            create_bridge("real")

    def test_unknown_raises_value_error(self) -> None:
        with pytest.raises(ValueError, match="Unknown bridge type"):
            create_bridge("something_else")


# ---------------------------------------------------------------------------
# ErrorOperatorService
# ---------------------------------------------------------------------------


class TestErrorOperatorService:
    """ErrorOperatorService serves startup errors through tool responses."""

    def test_getattr_raises_runtime_error(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="OmniFocus Operator failed to start"):
            _ = service._repository

    def test_getattr_raises_for_arbitrary_attribute(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="bad config"):
            _ = service.some_future_method

    def test_error_message_includes_restart_instruction(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with pytest.raises(RuntimeError, match="Restart the server after fixing"):
            _ = service._repository

    def test_getattr_logs_warning(self, caplog: pytest.LogCaptureFixture) -> None:
        import logging

        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("bad config"))

        with caplog.at_level(logging.WARNING), pytest.raises(RuntimeError):
            _ = service._repository

        assert any("error mode" in r.message.lower() for r in caplog.records)

    def test_does_not_call_super_init(self) -> None:
        from omnifocus_operator.service import ErrorOperatorService

        service = ErrorOperatorService(ValueError("x"))

        assert not hasattr(service, "_repository")
