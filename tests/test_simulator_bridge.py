"""Tests for SimulatorBridge -- base bridge subclass with no-op trigger."""

from __future__ import annotations

from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import anyio
from mcp.client.session import ClientSession
from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage

if TYPE_CHECKING:
    from pathlib import Path

    import pytest


# ---------------------------------------------------------------------------
# SimulatorBridge unit tests
# ---------------------------------------------------------------------------


class TestSimulatorBridge:
    """SimulatorBridge subclasses the base bridge with a no-op _trigger_omnifocus."""

    def test_trigger_omnifocus_is_noop(self, tmp_path: Path) -> None:
        """_trigger_omnifocus() is callable and returns None (no side effects)."""
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path)
        result = bridge._trigger_omnifocus("test-file-prefix")
        assert result is None

    def test_ipc_dir_returns_configured_path(self, tmp_path: Path) -> None:
        """ipc_dir property returns the configured path."""
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge.ipc_dir == tmp_path

    def test_satisfies_bridge_protocol(self, tmp_path: Path) -> None:
        """SimulatorBridge satisfies the Bridge protocol (structural typing)."""
        from omnifocus_operator.bridge.protocol import Bridge  # noqa: TC001
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        bridge: Bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge is not None
        # Verify send_command method exists and is callable
        assert hasattr(bridge, "send_command")
        assert callable(bridge.send_command)

    def test_ipc_directory_created_on_init(self, tmp_path: Path) -> None:
        """IPC directory is created on init (inherited from base bridge)."""
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        ipc_dir = tmp_path / "ipc"
        assert not ipc_dir.exists()
        SimulatorBridge(ipc_dir=ipc_dir)
        assert ipc_dir.exists()

    def test_has_ipc_mechanics(self, tmp_path: Path) -> None:
        """SimulatorBridge inherits IPC mechanics (ipc_dir, send_command)."""
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert hasattr(bridge, "ipc_dir")
        assert hasattr(bridge, "send_command")
        assert bridge.ipc_dir == tmp_path

    def test_accepts_timeout_kwarg(self, tmp_path: Path) -> None:
        """SimulatorBridge accepts timeout kwargs (inherited from base bridge)."""
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=5.0)
        assert bridge._timeout == 5.0


# ---------------------------------------------------------------------------
# Helpers (reused from test_server.py pattern)
# ---------------------------------------------------------------------------


async def _run_with_client(
    server: FastMCP,
    callback: Any,
) -> Any:
    """Run an in-process MCP server and execute *callback* with a connected ClientSession."""
    s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](0)
    c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](0)

    result: Any = None

    async with anyio.create_task_group() as tg:

        async def _run_server() -> None:
            await server._mcp_server.run(
                c2s_recv,
                s2c_send,
                server._mcp_server.create_initialization_options(),
                raise_exceptions=True,
            )

        tg.start_soon(_run_server)

        async with ClientSession(s2c_recv, c2s_send) as session:
            await session.initialize()
            result = await callback(session)
            tg.cancel_scope.cancel()

    return result


# ---------------------------------------------------------------------------
# Factory wiring tests
# ---------------------------------------------------------------------------


class TestFactory:
    """create_bridge('simulator') returns SimulatorBridge."""

    def test_create_bridge_simulator_returns_simulator_bridge(
        self,
        tmp_path: Path,
    ) -> None:
        """create_bridge('simulator') returns a SimulatorBridge instance."""
        from omnifocus_operator.bridge.factory import create_bridge
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        bridge = create_bridge("simulator")
        assert isinstance(bridge, SimulatorBridge)

    def test_create_bridge_simulator_respects_env_var(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """create_bridge('simulator') respects OMNIFOCUS_IPC_DIR env var."""
        from omnifocus_operator.bridge.factory import create_bridge
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        custom_dir = tmp_path / "custom-ipc"
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(custom_dir))

        bridge = create_bridge("simulator")
        assert isinstance(bridge, SimulatorBridge)
        assert bridge.ipc_dir == custom_dir

    def test_create_bridge_simulator_uses_default_ipc_dir(
        self,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """create_bridge('simulator') uses DEFAULT_IPC_DIR when env var not set."""
        from omnifocus_operator.bridge.factory import create_bridge
        from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        monkeypatch.delenv("OMNIFOCUS_IPC_DIR", raising=False)

        bridge = create_bridge("simulator")
        assert isinstance(bridge, SimulatorBridge)
        assert bridge.ipc_dir == DEFAULT_IPC_DIR


# ---------------------------------------------------------------------------
# Package export tests
# ---------------------------------------------------------------------------


class TestPackageExport:
    """SimulatorBridge is importable from omnifocus_operator.bridge."""

    def test_simulator_bridge_importable_from_package(self) -> None:
        """SimulatorBridge is exported from omnifocus_operator.bridge."""
        from omnifocus_operator.bridge import SimulatorBridge

        assert SimulatorBridge is not None

    def test_simulator_bridge_in_all(self) -> None:
        """SimulatorBridge is listed in __all__."""
        import omnifocus_operator.bridge as bridge_pkg

        assert "SimulatorBridge" in bridge_pkg.__all__


# ---------------------------------------------------------------------------
# Lifespan wiring tests
# ---------------------------------------------------------------------------


class TestLifespan:
    """app_lifespan handles OMNIFOCUS_BRIDGE=simulator with ConstantMtimeSource."""

    @staticmethod
    def _make_simulator_bridge_with_seed(
        tmp_path: Path,
    ) -> Any:
        """Create a SimulatorBridge with mocked send_command returning seed data."""
        from omnifocus_operator.bridge.simulator import SimulatorBridge

        mock_bridge = SimulatorBridge(ipc_dir=tmp_path)

        seed_data: dict[str, Any] = {
            "tasks": [],
            "projects": [],
            "tags": [],
            "folders": [],
            "perspectives": [],
        }

        async def fake_send_command(
            operation: str,
            params: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            return seed_data

        mock_bridge.send_command = fake_send_command  # type: ignore[assignment]
        return mock_bridge

    async def test_lifespan_simulator_completes_without_error(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Server lifespan completes successfully with bridge_type='simulator'."""
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "simulator")
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))

        mock_bridge = self._make_simulator_bridge_with_seed(tmp_path)

        with patch(
            "omnifocus_operator.bridge.create_bridge",
            return_value=mock_bridge,
        ):
            from omnifocus_operator.server._server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            async def _check(session: ClientSession) -> None:
                # If lifespan completes, we can list tools
                result = await session.list_tools()
                assert result.tools is not None

            await _run_with_client(server, _check)

    async def test_lifespan_simulator_can_serve_list_all(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Server with simulator bridge can serve list_all tool calls."""
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "simulator")
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))

        mock_bridge = self._make_simulator_bridge_with_seed(tmp_path)

        with patch(
            "omnifocus_operator.bridge.create_bridge",
            return_value=mock_bridge,
        ):
            from omnifocus_operator.server._server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            async def _check(session: ClientSession) -> None:
                result = await session.call_tool("list_all")
                assert result.structuredContent is not None

            await _run_with_client(server, _check)

    async def test_lifespan_simulator_sweeps_orphaned_files(
        self,
        monkeypatch: pytest.MonkeyPatch,
        tmp_path: Path,
    ) -> None:
        """Lifespan sweeps orphaned IPC files for simulator bridge (has ipc_dir)."""
        from unittest.mock import AsyncMock

        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "simulator")
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))

        mock_bridge = self._make_simulator_bridge_with_seed(tmp_path)
        mock_sweep = AsyncMock()

        with (
            patch(
                "omnifocus_operator.bridge.create_bridge",
                return_value=mock_bridge,
            ),
            patch(
                "omnifocus_operator.bridge.sweep_orphaned_files",
                mock_sweep,
            ),
        ):
            from omnifocus_operator.server._server import _register_tools, app_lifespan

            server = FastMCP("omnifocus-operator", lifespan=app_lifespan)
            _register_tools(server)

            async def _check(session: ClientSession) -> None:
                pass

            await _run_with_client(server, _check)

        mock_sweep.assert_called_once_with(tmp_path)
