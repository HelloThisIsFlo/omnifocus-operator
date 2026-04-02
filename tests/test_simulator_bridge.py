"""Tests for SimulatorBridge -- base bridge subclass with no-op trigger."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import AsyncMock, patch

import pytest
from fastmcp import Client

import omnifocus_operator.bridge as bridge_pkg
from omnifocus_operator.repository import BridgeOnlyRepository
from omnifocus_operator.server import create_server
from tests.doubles import ConstantMtimeSource, InMemoryBridge, SimulatorBridge

if TYPE_CHECKING:
    from pathlib import Path

    from omnifocus_operator.contracts.protocols import Bridge


# ---------------------------------------------------------------------------
# SimulatorBridge unit tests
# ---------------------------------------------------------------------------


class TestSimulatorBridge:
    """SimulatorBridge subclasses the base bridge with a no-op _trigger_omnifocus."""

    def test_trigger_omnifocus_is_noop(self, tmp_path: Path) -> None:
        """_trigger_omnifocus() is callable and returns None (no side effects)."""
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        result = bridge._trigger_omnifocus("test-file-prefix")
        assert result is None

    def test_ipc_dir_returns_configured_path(self, tmp_path: Path) -> None:
        """ipc_dir property returns the configured path."""
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge.ipc_dir == tmp_path

    def test_satisfies_bridge_protocol(self, tmp_path: Path) -> None:
        """SimulatorBridge satisfies the Bridge protocol (structural typing)."""
        bridge: Bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge is not None
        # Verify send_command method exists and is callable
        assert hasattr(bridge, "send_command")
        assert callable(bridge.send_command)

    def test_ipc_directory_created_on_init(self, tmp_path: Path) -> None:
        """IPC directory is created on init (inherited from base bridge)."""
        ipc_dir = tmp_path / "ipc"
        assert not ipc_dir.exists()
        SimulatorBridge(ipc_dir=ipc_dir)
        assert ipc_dir.exists()

    def test_has_ipc_mechanics(self, tmp_path: Path) -> None:
        """SimulatorBridge inherits IPC mechanics (ipc_dir, send_command)."""
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert hasattr(bridge, "ipc_dir")
        assert hasattr(bridge, "send_command")
        assert bridge.ipc_dir == tmp_path

    def test_accepts_timeout_kwarg(self, tmp_path: Path) -> None:
        """SimulatorBridge accepts timeout kwargs (inherited from base bridge)."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=5.0)
        assert bridge._timeout == 5.0


# ---------------------------------------------------------------------------
# Package export tests (negative — removed from public API)
# ---------------------------------------------------------------------------


class TestPackageExport:
    """SimulatorBridge is NOT importable from omnifocus_operator.bridge."""

    def test_simulator_bridge_not_importable_from_package(self) -> None:
        """SimulatorBridge is NOT exported from omnifocus_operator.bridge."""
        with pytest.raises(ImportError):
            from omnifocus_operator.bridge import SimulatorBridge  # noqa: F401, PLC0415

    def test_simulator_bridge_not_in_all(self) -> None:
        """SimulatorBridge is NOT listed in __all__."""
        assert "SimulatorBridge" not in bridge_pkg.__all__

    def test_create_bridge_not_importable_from_package(self) -> None:
        """create_bridge is NOT exported from omnifocus_operator.bridge."""
        with pytest.raises(ImportError):
            from omnifocus_operator.bridge import create_bridge  # noqa: F401, PLC0415

    def test_create_bridge_not_in_all(self) -> None:
        """create_bridge is NOT listed in __all__."""
        assert "create_bridge" not in bridge_pkg.__all__


# ---------------------------------------------------------------------------
# Lifespan wiring tests
# ---------------------------------------------------------------------------


class TestLifespan:
    """app_lifespan wiring with monkeypatched BridgeOnlyRepository + InMemoryBridge."""

    @staticmethod
    def _make_repo() -> Any:
        """Create a BridgeOnlyRepository with empty InMemoryBridge."""
        return BridgeOnlyRepository(
            bridge=InMemoryBridge(
                data={"tasks": [], "projects": [], "tags": [], "folders": [], "perspectives": []}
            ),
            mtime_source=ConstantMtimeSource(),
        )

    async def test_lifespan_completes_without_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Server lifespan completes successfully with monkeypatched repository."""
        repo = self._make_repo()

        with patch(
            "omnifocus_operator.repository.create_repository",
            return_value=repo,
        ):
            server = create_server()

            async with Client(server) as client:
                tools = await client.list_tools()
                assert isinstance(tools, list)

    async def test_lifespan_can_serve_get_all(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Server with monkeypatched repository can serve get_all tool calls."""
        repo = self._make_repo()

        with patch(
            "omnifocus_operator.repository.create_repository",
            return_value=repo,
        ):
            server = create_server()

            async with Client(server) as client:
                result = await client.call_tool("get_all")
                assert result.structured_content is not None

    async def test_lifespan_sweeps_orphaned_files(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Lifespan always sweeps orphaned IPC files (DEFAULT_IPC_DIR)."""
        repo = self._make_repo()
        mock_sweep = AsyncMock()

        with (
            patch(
                "omnifocus_operator.repository.create_repository",
                return_value=repo,
            ),
            patch(
                "omnifocus_operator.bridge.real.sweep_orphaned_files",
                mock_sweep,
            ),
        ):
            server = create_server()

            async with Client(server) as _client:
                pass

        # Sweep is called with DEFAULT_IPC_DIR (always), not bridge.ipc_dir
        mock_sweep.assert_called_once()
