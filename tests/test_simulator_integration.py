"""Integration tests for the mock simulator + SimulatorBridge round-trip.

These tests spawn the simulator as a subprocess, communicate through
file-based IPC via SimulatorBridge, and verify end-to-end behaviour
including error simulation modes and MCP server integration.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
import time
from typing import TYPE_CHECKING, Any

import anyio
import pytest
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage

from omnifocus_operator.bridge.errors import BridgeProtocolError, BridgeTimeoutError
from tests.doubles import SimulatorBridge
from omnifocus_operator.simulator.data import SIMULATOR_SNAPSHOT

if TYPE_CHECKING:
    from collections.abc import Generator
    from pathlib import Path

    from mcp.server.fastmcp import FastMCP


# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _start_simulator(
    ipc_dir: Path,
    *,
    fail_mode: str | None = None,
    fail_after: int | None = None,
    delay: float = 0.0,
    timeout: float = 10.0,
) -> subprocess.Popen[str]:
    """Start a simulator subprocess and wait for readiness.

    Returns the running Popen process.  Raises ``RuntimeError`` if the
    simulator does not become ready within *timeout* seconds.
    """
    cmd = [sys.executable, "-m", "omnifocus_operator.simulator", "--ipc-dir", str(ipc_dir)]
    if fail_mode is not None:
        cmd.extend(["--fail-mode", fail_mode])
    if fail_after is not None:
        cmd.extend(["--fail-after", str(fail_after)])
    if delay > 0:
        cmd.extend(["--delay", str(delay)])

    env = {**os.environ, "PYTHONUNBUFFERED": "1"}
    proc = subprocess.Popen(
        cmd,
        stderr=subprocess.PIPE,
        stdout=subprocess.DEVNULL,
        text=True,
        env=env,
    )

    # Wait for the readiness marker on stderr
    assert proc.stderr is not None
    deadline = time.monotonic() + timeout
    while time.monotonic() < deadline:
        line = proc.stderr.readline()
        if not line:
            # Process may have exited
            if proc.poll() is not None:
                msg = f"Simulator exited with code {proc.returncode}"
                raise RuntimeError(msg)
            continue
        if "ready" in line.lower():
            return proc

    proc.terminate()
    proc.wait(timeout=5)
    msg = "Simulator did not become ready within timeout"
    raise RuntimeError(msg)


@pytest.fixture()
def simulator_process(tmp_path: Path) -> Generator[subprocess.Popen[str], None, None]:
    """Spawn a default (no-failure) simulator subprocess."""
    proc = _start_simulator(tmp_path)
    yield proc
    proc.terminate()
    proc.wait(timeout=5)


def _make_bridge(ipc_dir: Path, *, timeout: float = 5.0) -> SimulatorBridge:
    """Create a SimulatorBridge pointed at *ipc_dir* with a short timeout."""
    return SimulatorBridge(ipc_dir=ipc_dir, timeout=timeout)


# ---------------------------------------------------------------------------
# MCP in-process client helper (mirrors test_server.py pattern)
# ---------------------------------------------------------------------------


async def _run_with_client(
    server: FastMCP,
    callback: Any,
) -> Any:
    """Run an in-process MCP server and execute *callback* with a ClientSession."""
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
# TestSimulatorProcess
# ---------------------------------------------------------------------------


class TestSimulatorProcess:
    """Tests for basic simulator process lifecycle."""

    @pytest.mark.timeout(30)
    def test_starts_and_becomes_ready(
        self,
        simulator_process: subprocess.Popen[str],
    ) -> None:
        """Simulator starts and is alive after readiness marker."""
        assert simulator_process.poll() is None  # still running

    @pytest.mark.timeout(30)
    def test_shutdown_on_terminate(self, tmp_path: Path) -> None:
        """Simulator exits cleanly after SIGTERM."""
        proc = _start_simulator(tmp_path)
        proc.terminate()
        exit_code = proc.wait(timeout=5)
        # Terminated processes return negative signal number or 0
        assert exit_code is not None


# ---------------------------------------------------------------------------
# TestEndToEnd
# ---------------------------------------------------------------------------


class TestEndToEnd:
    """Round-trip IPC tests: SimulatorBridge <-> Simulator process."""

    @pytest.mark.timeout(30)
    async def test_round_trip_snapshot(
        self,
        tmp_path: Path,
        simulator_process: subprocess.Popen[str],
    ) -> None:
        """send_command('snapshot') returns full SIMULATOR_SNAPSHOT data."""
        bridge = _make_bridge(tmp_path)
        result = await bridge.send_command("snapshot")

        assert "tasks" in result
        assert "projects" in result
        assert "tags" in result
        assert "folders" in result
        assert "perspectives" in result
        assert len(result["tasks"]) == len(SIMULATOR_SNAPSHOT["tasks"])
        assert len(result["projects"]) == len(SIMULATOR_SNAPSHOT["projects"])
        assert len(result["tags"]) == len(SIMULATOR_SNAPSHOT["tags"])
        assert len(result["folders"]) == len(SIMULATOR_SNAPSHOT["folders"])
        assert len(result["perspectives"]) == len(SIMULATOR_SNAPSHOT["perspectives"])

    @pytest.mark.timeout(30)
    async def test_multiple_requests(
        self,
        tmp_path: Path,
        simulator_process: subprocess.Popen[str],
    ) -> None:
        """Two sequential requests both succeed (seen-set does not interfere)."""
        bridge = _make_bridge(tmp_path)

        result1 = await bridge.send_command("snapshot")
        assert "tasks" in result1

        result2 = await bridge.send_command("snapshot")
        assert "tasks" in result2


# ---------------------------------------------------------------------------
# TestErrorSimulation
# ---------------------------------------------------------------------------


class TestErrorSimulation:
    """Error injection modes: error, malformed, timeout."""

    @pytest.mark.timeout(30)
    async def test_fail_mode_error(self, tmp_path: Path) -> None:
        """--fail-mode error causes BridgeProtocolError with 'simulated error'."""
        proc = _start_simulator(tmp_path, fail_mode="error")
        try:
            bridge = _make_bridge(tmp_path)
            with pytest.raises(BridgeProtocolError, match="simulated error"):
                await bridge.send_command("snapshot")
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    @pytest.mark.timeout(30)
    async def test_fail_mode_malformed(self, tmp_path: Path) -> None:
        """--fail-mode malformed causes JSONDecodeError (malformed JSON response)."""
        proc = _start_simulator(tmp_path, fail_mode="malformed")
        try:
            bridge = _make_bridge(tmp_path)
            with pytest.raises(json.JSONDecodeError):
                await bridge.send_command("snapshot")
        finally:
            proc.terminate()
            proc.wait(timeout=5)

    @pytest.mark.timeout(30)
    async def test_fail_mode_timeout(self, tmp_path: Path) -> None:
        """--fail-mode timeout causes BridgeTimeoutError."""
        proc = _start_simulator(tmp_path, fail_mode="timeout")
        try:
            bridge = _make_bridge(tmp_path, timeout=2.0)
            with pytest.raises(BridgeTimeoutError):
                await bridge.send_command("snapshot")
        finally:
            proc.terminate()
            proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# TestFailAfter
# ---------------------------------------------------------------------------


class TestFailAfter:
    """--fail-after N transitions from success to failure."""

    @pytest.mark.timeout(30)
    async def test_fail_after_transitions(self, tmp_path: Path) -> None:
        """First request succeeds, second triggers error mode."""
        proc = _start_simulator(tmp_path, fail_mode="error", fail_after=1)
        try:
            bridge = _make_bridge(tmp_path)

            # First request succeeds (within fail_after threshold)
            result = await bridge.send_command("snapshot")
            assert "tasks" in result

            # Second request fails (exceeds fail_after)
            with pytest.raises(BridgeProtocolError, match="simulated error"):
                await bridge.send_command("snapshot")
        finally:
            proc.terminate()
            proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# TestDelay
# ---------------------------------------------------------------------------


class TestDelay:
    """--delay flag slows response delivery."""

    @pytest.mark.timeout(30)
    async def test_delay_still_completes(self, tmp_path: Path) -> None:
        """Response with 0.5s delay still completes within the bridge timeout."""
        proc = _start_simulator(tmp_path, delay=0.5)
        try:
            bridge = _make_bridge(tmp_path, timeout=5.0)
            result = await bridge.send_command("snapshot")
            assert "tasks" in result
        finally:
            proc.terminate()
            proc.wait(timeout=5)


# ---------------------------------------------------------------------------
# TestMcpIntegration
# ---------------------------------------------------------------------------


class TestMcpIntegration:
    """MCP server integration with SimulatorBridge + live simulator."""

    @pytest.mark.timeout(30)
    async def test_get_all_with_simulator(
        self,
        tmp_path: Path,
        monkeypatch: pytest.MonkeyPatch,
    ) -> None:
        """MCP get_all tool returns simulator data via full stack."""
        proc = _start_simulator(tmp_path)
        try:
            monkeypatch.setenv("OMNIFOCUS_REPOSITORY", "bridge-only")
            monkeypatch.setenv("OMNIFOCUS_IPC_DIR", str(tmp_path))
            # Create a fake .ofocus bundle for FileMtimeSource
            ofocus_bundle = tmp_path / "OmniFocus.ofocus"
            ofocus_bundle.mkdir(exist_ok=True)
            monkeypatch.setenv("OMNIFOCUS_OFOCUS_PATH", str(ofocus_bundle))
            monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)

            from omnifocus_operator.server import create_server

            server = create_server()

            async def _check(session: ClientSession) -> None:
                # Verify get_all tool is available
                tools_result = await session.list_tools()
                tool_names = [t.name for t in tools_result.tools]
                assert "get_all" in tool_names

                # Call get_all and verify simulator data comes through
                result = await session.call_tool("get_all")
                assert result.structuredContent is not None
                keys = set(result.structuredContent.keys())
                assert keys == {"tasks", "projects", "tags", "folders", "perspectives"}
                # Verify counts match simulator data
                assert len(result.structuredContent["tasks"]) == len(SIMULATOR_SNAPSHOT["tasks"])

            await _run_with_client(server, _check)
        finally:
            proc.terminate()
            proc.wait(timeout=5)
