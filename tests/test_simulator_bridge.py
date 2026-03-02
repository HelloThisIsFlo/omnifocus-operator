"""Tests for SimulatorBridge -- RealBridge subclass with no-op trigger."""

from __future__ import annotations

from pathlib import Path
from typing import TYPE_CHECKING, Any
from unittest.mock import patch

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.server.fastmcp import FastMCP
from mcp.shared.message import SessionMessage

if TYPE_CHECKING:
    from collections.abc import AsyncIterator


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
        self, tmp_path: Path,
    ) -> None:
        """create_bridge('simulator') returns a SimulatorBridge instance."""
        from omnifocus_operator.bridge._factory import create_bridge
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        bridge = create_bridge("simulator")
        assert isinstance(bridge, SimulatorBridge)

    def test_create_bridge_simulator_respects_env_var(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """create_bridge('simulator') respects OMNIFOCUS_IPC_DIR env var."""
        from omnifocus_operator.bridge._factory import create_bridge
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        custom_dir = tmp_path / "custom-ipc"
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(custom_dir))

        bridge = create_bridge("simulator")
        assert isinstance(bridge, SimulatorBridge)
        assert bridge.ipc_dir == custom_dir

    def test_create_bridge_simulator_uses_default_ipc_dir(
        self, monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """create_bridge('simulator') uses DEFAULT_IPC_DIR when env var not set."""
        from omnifocus_operator.bridge._factory import create_bridge
        from omnifocus_operator.bridge._real import DEFAULT_IPC_DIR
        from omnifocus_operator.bridge._simulator import SimulatorBridge

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

    async def test_lifespan_simulator_completes_without_error(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        """Server lifespan completes successfully with bridge_type='simulator'."""
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "simulator")
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))

        from omnifocus_operator.server import create_server

        server = create_server()

        async def _check(session: ClientSession) -> None:
            # If lifespan completes, we can list tools
            result = await session.list_tools()
            assert result.tools is not None

        await _run_with_client(server, _check)

    async def test_lifespan_simulator_can_serve_list_all(
        self, monkeypatch: pytest.MonkeyPatch, tmp_path: Path,
    ) -> None:
        """Server with simulator bridge can serve list_all tool calls.

        The SimulatorBridge.send_command will time out (no simulator process),
        but the server lifespan itself should start up fine and serve the
        initial cache pre-warm. We need to mock the bridge's send_command
        to provide data for the pre-warm step.
        """
        monkeypatch.setenv("OMNIFOCUS_BRIDGE", "simulator")
        monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))

        # Patch create_bridge to return a SimulatorBridge with mocked send_command
        from omnifocus_operator.bridge._simulator import SimulatorBridge

        mock_bridge = SimulatorBridge(ipc_dir=tmp_path)

        seed_data = {
            "tasks": [],
            "projects": [],
            "tags": [],
            "folders": [],
            "perspectives": [],
        }

        async def fake_send_command(
            operation: str, params: dict[str, Any] | None = None,
        ) -> dict[str, Any]:
            return seed_data

        mock_bridge.send_command = fake_send_command  # type: ignore[assignment]

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
