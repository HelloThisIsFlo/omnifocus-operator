"""Tests for SimulatorBridge -- RealBridge subclass with no-op trigger."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING

import pytest

if TYPE_CHECKING:
    from typing import Any


# ---------------------------------------------------------------------------
# SimulatorBridge unit tests
# ---------------------------------------------------------------------------


class TestSimulatorBridge:
    """SimulatorBridge subclasses RealBridge with a no-op _trigger_omnifocus."""

    def test_trigger_omnifocus_is_noop(self, tmp_path: Path) -> None:
        """_trigger_omnifocus() is callable and returns None (no side effects)."""
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path)
        result = bridge._trigger_omnifocus("test-dispatch")
        assert result is None

    def test_ipc_dir_returns_configured_path(self, tmp_path: Path) -> None:
        """ipc_dir property returns the configured path."""
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge.ipc_dir == tmp_path

    def test_satisfies_bridge_protocol(self, tmp_path: Path) -> None:
        """SimulatorBridge satisfies the Bridge protocol (structural typing)."""
        from omnifocus_operator.bridge._protocol import Bridge
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        bridge: Bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge is not None
        # Verify send_command method exists and is callable
        assert hasattr(bridge, "send_command")
        assert callable(bridge.send_command)

    def test_ipc_directory_created_on_init(self, tmp_path: Path) -> None:
        """IPC directory is created on init (inherited from RealBridge)."""
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        ipc_dir = tmp_path / "ipc"
        assert not ipc_dir.exists()
        SimulatorBridge(ipc_dir=ipc_dir)
        assert ipc_dir.exists()

    def test_subclasses_real_bridge(self, tmp_path: Path) -> None:
        """SimulatorBridge is a subclass of RealBridge."""
        from omnifocus_operator.bridge._real import RealBridge
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert isinstance(bridge, RealBridge)

    def test_accepts_timeout_kwarg(self, tmp_path: Path) -> None:
        """SimulatorBridge accepts timeout kwargs (inherited from RealBridge)."""
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=5.0)
        assert bridge._timeout == 5.0
