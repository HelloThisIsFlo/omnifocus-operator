"""Tests for IPC engine -- file-based IPC mechanics via SimulatorBridge.

All IPC mechanics (atomic writes, non-blocking I/O, request envelope,
timeouts, response parsing, orphan sweep) are inherited from the base
bridge class. SimulatorBridge is used here to satisfy SAFE-01: no test
file imports or instantiates the production bridge.
"""

from __future__ import annotations

import asyncio
import json
import os
import subprocess
import sys
import uuid
from pathlib import Path
from typing import Any
from unittest.mock import AsyncMock, patch

import pytest

from omnifocus_operator.bridge.errors import BridgeProtocolError, BridgeTimeoutError
from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, RealBridge, sweep_orphaned_files
from tests.doubles import SimulatorBridge

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


async def _write_response_after_delay(
    ipc_dir: Path,
    pid: int,
    request_id: uuid.UUID,
    data: dict[str, Any],
    *,
    delay: float = 0.05,
    success: bool = True,
) -> None:
    """Write a response file after a short delay, simulating OmniFocus."""
    await asyncio.sleep(delay)
    response_path = ipc_dir / f"{pid}_{request_id}.response.json"
    if success:
        content = json.dumps({"success": True, "data": data})
    else:
        content = json.dumps({"success": False, "error": data.get("error", "Unknown")})
    response_path.write_text(content, encoding="utf-8")


def _find_request_file(ipc_dir: Path) -> Path | None:
    """Find the first .request.json file in ipc_dir."""
    for f in ipc_dir.iterdir():
        if f.name.endswith(".request.json"):
            return f
    return None


def _extract_request_id_from_file(request_file: Path) -> uuid.UUID:
    """Extract UUID from filename like <pid>_<uuid>.request.json."""
    name = request_file.stem.rsplit(".", maxsplit=1)[0]  # strip .request
    uuid_str = name.split("_", maxsplit=1)[1]  # strip pid_
    return uuid.UUID(uuid_str)


# ---------------------------------------------------------------------------
# TestAtomicWrite
# ---------------------------------------------------------------------------


class TestAtomicWrite:
    """IPC-01: File writes use atomic pattern (.tmp + os.replace)."""

    @pytest.mark.asyncio
    async def test_write_request_creates_file(self, tmp_path: Path) -> None:
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        request_id = uuid.uuid4()

        await bridge._write_request(request_id, "test_op")

        request_file = tmp_path / f"{os.getpid()}_{request_id}.request.json"
        assert request_file.exists()
        content = json.loads(request_file.read_text(encoding="utf-8"))
        assert "operation" in content

    @pytest.mark.asyncio
    async def test_write_request_is_atomic(self, tmp_path: Path) -> None:
        """Final path created via os.replace -- no .tmp file remains."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        request_id = uuid.uuid4()

        await bridge._write_request(request_id, "test_op")

        # No .tmp files should remain
        tmp_files = list(tmp_path.glob("*.tmp"))
        assert tmp_files == [], f"Leftover .tmp files: {tmp_files}"

        # The final file exists
        request_file = tmp_path / f"{os.getpid()}_{request_id}.request.json"
        assert request_file.exists()

    @pytest.mark.asyncio
    async def test_write_request_content_format(self, tmp_path: Path) -> None:
        """Request file contains JSON with operation and params envelope."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        request_id = uuid.uuid4()
        operation = "get_tasks"

        await bridge._write_request(request_id, operation)

        request_file = tmp_path / f"{os.getpid()}_{request_id}.request.json"
        content = json.loads(request_file.read_text(encoding="utf-8"))
        assert content == {"operation": "get_tasks", "params": {}}


# ---------------------------------------------------------------------------
# TestNonBlockingIO
# ---------------------------------------------------------------------------


class TestNonBlockingIO:
    """IPC-02: All file I/O is non-blocking via asyncio.to_thread."""

    @pytest.mark.asyncio
    async def test_send_command_is_async(self, tmp_path: Path) -> None:
        """send_command is a coroutine that can be awaited."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        coro = bridge.send_command("test_op")
        assert asyncio.iscoroutine(coro)
        coro.close()  # Clean up without running

    @pytest.mark.asyncio
    async def test_file_operations_use_to_thread(self, tmp_path: Path) -> None:
        """File I/O operations are wrapped in asyncio.to_thread."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        request_id = uuid.uuid4()

        with patch("omnifocus_operator.bridge.real.asyncio") as mock_asyncio:
            # Make to_thread actually work by delegating to real to_thread
            mock_asyncio.to_thread = AsyncMock(side_effect=asyncio.to_thread)
            mock_asyncio.sleep = asyncio.sleep
            mock_asyncio.wait_for = asyncio.wait_for

            await bridge._write_request(request_id, "test_op")

            mock_asyncio.to_thread.assert_called()


# ---------------------------------------------------------------------------
# TestDispatchProtocol
# ---------------------------------------------------------------------------


class TestRequestEnvelope:
    """IPC-03: Request envelope uses {operation, params} format."""

    @pytest.mark.asyncio
    async def test_request_envelope_format(self, tmp_path: Path) -> None:
        """Request envelope contains operation and params keys."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.2)
        pid = os.getpid()

        request_id = uuid.uuid4()
        await bridge._write_request(request_id, "list_tasks")

        request_file = tmp_path / f"{pid}_{request_id}.request.json"
        content = json.loads(request_file.read_text(encoding="utf-8"))
        assert content == {"operation": "list_tasks", "params": {}}

    @pytest.mark.asyncio
    async def test_request_envelope_with_params(self, tmp_path: Path) -> None:
        """Request envelope forwards params when provided."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.2)
        pid = os.getpid()

        request_id = uuid.uuid4()
        await bridge._write_request(request_id, "snapshot", {"filter": "active"})

        request_file = tmp_path / f"{pid}_{request_id}.request.json"
        content = json.loads(request_file.read_text(encoding="utf-8"))
        assert content == {"operation": "snapshot", "params": {"filter": "active"}}

    @pytest.mark.asyncio
    async def test_uuid_in_request_filename(self, tmp_path: Path) -> None:
        """Request filename embeds a valid UUID4."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.2)
        pid = os.getpid()

        request_id = uuid.uuid4()
        await bridge._write_request(request_id, "test_op")

        request_file = tmp_path / f"{pid}_{request_id}.request.json"
        assert request_file.exists()
        # Extract UUID from filename and verify it is valid UUID4
        uuid_str = request_file.name.split("_", maxsplit=1)[1].replace(".request.json", "")
        parsed = uuid.UUID(uuid_str, version=4)
        assert str(parsed) == uuid_str

    @pytest.mark.asyncio
    async def test_different_operations_produce_different_uuids(self, tmp_path: Path) -> None:
        """Two send_command calls produce different request IDs."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.3)
        pid = os.getpid()
        collected_ids: list[str] = []

        async def respond_and_collect() -> None:
            for _ in range(2):
                req = None
                for _ in range(100):
                    req = _find_request_file(tmp_path)
                    if req is not None:
                        break
                    await asyncio.sleep(0.01)
                assert req is not None
                rid = _extract_request_id_from_file(req)
                collected_ids.append(str(rid))
                resp_path = tmp_path / f"{pid}_{rid}.response.json"
                resp_path.write_text(
                    json.dumps({"success": True, "data": {}}),
                    encoding="utf-8",
                )
                # Wait for cleanup
                for _ in range(50):
                    if not req.exists():
                        break
                    await asyncio.sleep(0.01)

        task = asyncio.create_task(respond_and_collect())
        await bridge.send_command("op_a")
        await bridge.send_command("op_b")
        await task

        assert len(collected_ids) == 2
        assert collected_ids[0] != collected_ids[1]


# ---------------------------------------------------------------------------
# TestTimeout
# ---------------------------------------------------------------------------


class TestTimeout:
    """IPC-05: Response timeout with actionable error."""

    @pytest.mark.asyncio
    async def test_timeout_raises_bridge_timeout_error(self, tmp_path: Path) -> None:
        """When no response file appears within timeout, raises BridgeTimeoutError."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.2)

        with pytest.raises(BridgeTimeoutError) as exc_info:
            await bridge.send_command("slow_op")

        assert exc_info.value.operation == "slow_op"

    @pytest.mark.asyncio
    async def test_timeout_error_message_names_omnifocus(self, tmp_path: Path) -> None:
        """Error message includes 'OmniFocus' explicitly."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.2)

        with pytest.raises(BridgeTimeoutError) as exc_info:
            await bridge.send_command("slow_op")

        assert "OmniFocus" in str(exc_info.value)

    @pytest.mark.asyncio
    async def test_timeout_cleans_up_request_file(self, tmp_path: Path) -> None:
        """After timeout, the request file is deleted."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.2)

        with pytest.raises(BridgeTimeoutError):
            await bridge.send_command("slow_op")

        # No request files should remain
        request_files = list(tmp_path.glob("*.request.json"))
        assert request_files == []

    @pytest.mark.asyncio
    async def test_timeout_configurable_for_testing(self, tmp_path: Path) -> None:
        """Bridge accepts a timeout parameter (default 10.0) for fast tests."""
        bridge_default = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge_default._timeout == 10.0

        bridge_custom = SimulatorBridge(ipc_dir=tmp_path, timeout=0.5)
        assert bridge_custom._timeout == 0.5


# ---------------------------------------------------------------------------
# TestSuccessfulRoundTrip
# ---------------------------------------------------------------------------


class TestSuccessfulRoundTrip:
    """Successful IPC round-trip behavior."""

    @pytest.mark.asyncio
    async def test_send_command_returns_parsed_response_data(self, tmp_path: Path) -> None:
        """When response has success:true+data, send_command returns the data dict."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        pid = os.getpid()
        expected_data = {"tasks": [{"id": "t1", "name": "Buy milk"}]}

        async def respond() -> None:
            for _ in range(100):
                req = _find_request_file(tmp_path)
                if req is not None:
                    rid = _extract_request_id_from_file(req)
                    await _write_response_after_delay(tmp_path, pid, rid, expected_data, delay=0.02)
                    return
                await asyncio.sleep(0.01)

        task = asyncio.create_task(respond())
        result = await bridge.send_command("get_tasks")
        await task

        assert result == expected_data

    @pytest.mark.asyncio
    async def test_success_cleans_up_both_files(self, tmp_path: Path) -> None:
        """After successful round-trip, both request and response files deleted."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        pid = os.getpid()

        async def respond() -> None:
            for _ in range(100):
                req = _find_request_file(tmp_path)
                if req is not None:
                    rid = _extract_request_id_from_file(req)
                    await _write_response_after_delay(tmp_path, pid, rid, {"ok": True}, delay=0.02)
                    return
                await asyncio.sleep(0.01)

        task = asyncio.create_task(respond())
        await bridge.send_command("some_op")
        await task

        # Both files should be cleaned up
        remaining = list(tmp_path.iterdir())
        assert remaining == [], f"Files not cleaned up: {remaining}"

    @pytest.mark.asyncio
    async def test_protocol_error_on_bridge_failure(self, tmp_path: Path) -> None:
        """When response has success:false, raises BridgeProtocolError."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        pid = os.getpid()

        async def respond_with_error() -> None:
            for _ in range(100):
                req = _find_request_file(tmp_path)
                if req is not None:
                    rid = _extract_request_id_from_file(req)
                    await _write_response_after_delay(
                        tmp_path,
                        pid,
                        rid,
                        {"error": "Unknown operation: bad_op"},
                        delay=0.02,
                        success=False,
                    )
                    return
                await asyncio.sleep(0.01)

        task = asyncio.create_task(respond_with_error())

        with pytest.raises(BridgeProtocolError) as exc_info:
            await bridge.send_command("bad_op")

        await task
        assert "Unknown operation: bad_op" in str(exc_info.value)


# ---------------------------------------------------------------------------
# TestTriggerHook
# ---------------------------------------------------------------------------


class TestTriggerHook:
    """Template method hook for triggering OmniFocus."""

    @pytest.mark.asyncio
    async def test_simulator_trigger_is_noop(self, tmp_path: Path) -> None:
        """SimulatorBridge._trigger_omnifocus() is a permanent no-op."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=1.0)
        # Should not raise or have side effects
        bridge._trigger_omnifocus("some-file-prefix")
        # No return value (None) -- just verifying it doesn't raise

    @pytest.mark.asyncio
    async def test_trigger_called_between_write_and_wait(self, tmp_path: Path) -> None:
        """_trigger_omnifocus() called after _write_request() and before _wait_response()."""
        bridge = SimulatorBridge(ipc_dir=tmp_path, timeout=0.3)
        call_order: list[str] = []
        pid = os.getpid()

        original_write = bridge._write_request
        original_trigger = bridge._trigger_omnifocus

        async def tracked_write(
            request_id: uuid.UUID, operation: str, params: dict[str, Any] | None = None
        ) -> None:
            call_order.append("write")
            await original_write(request_id, operation, params)

        def tracked_trigger(file_prefix: str) -> None:
            call_order.append("trigger")
            # Also write a response so send_command doesn't timeout
            req = _find_request_file(tmp_path)
            if req is not None:
                rid = _extract_request_id_from_file(req)
                resp_path = tmp_path / f"{pid}_{rid}.response.json"
                resp_path.write_text(
                    json.dumps({"success": True, "data": {}}),
                    encoding="utf-8",
                )
            original_trigger(file_prefix)

        bridge._write_request = tracked_write  # type: ignore[method-assign]
        bridge._trigger_omnifocus = tracked_trigger  # type: ignore[method-assign]

        await bridge.send_command("test_op")

        assert call_order.index("write") < call_order.index("trigger")


# ---------------------------------------------------------------------------
# TestIPCDirectory
# ---------------------------------------------------------------------------


class TestIPCDirectory:
    """IPC-04: Default directory, env var override, auto-creation."""

    def test_default_ipc_dir_constant(self) -> None:
        """DEFAULT_IPC_DIR points to OmniFocus 4 documentsDirectory IPC path."""
        expected = (
            Path.home()
            / "Library"
            / "Containers"
            / "com.omnigroup.OmniFocus4"
            / "Data"
            / "Documents"
            / "omnifocus-operator"
            / "ipc"
        )
        assert expected == DEFAULT_IPC_DIR

    def test_constructor_accepts_ipc_dir(self, tmp_path: Path) -> None:
        """SimulatorBridge(ipc_dir=tmp_path) uses the provided path."""
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge._ipc_dir == tmp_path

    def test_ipc_dir_auto_created(self, tmp_path: Path) -> None:
        """If ipc_dir does not exist, SimulatorBridge creates it during init."""
        new_dir = tmp_path / "nonexistent" / "deep" / "ipc"
        assert not new_dir.exists()

        SimulatorBridge(ipc_dir=new_dir)

        assert new_dir.exists()
        assert new_dir.is_dir()

    def test_ipc_dir_already_exists_ok(self, tmp_path: Path) -> None:
        """If ipc_dir already exists, initialization does not raise."""
        assert tmp_path.exists()
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge._ipc_dir == tmp_path


# ---------------------------------------------------------------------------
# TestOrphanSweep
# ---------------------------------------------------------------------------


class TestOrphanSweep:
    """Orphaned IPC file cleanup on startup."""

    def _dead_pid(self) -> int:
        """Return a PID that is guaranteed to be dead."""
        result = subprocess.run(
            [sys.executable, "-c", "import os; print(os.getpid())"],
            capture_output=True,
            text=True,
            check=True,
        )
        return int(result.stdout.strip())

    @pytest.mark.asyncio
    async def test_sweep_removes_files_from_dead_pid(self, tmp_path: Path) -> None:
        """Files with a dead PID prefix are deleted."""
        dead_pid = self._dead_pid()
        req_file = tmp_path / f"{dead_pid}_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.request.json"
        req_file.write_text("{}", encoding="utf-8")

        await sweep_orphaned_files(tmp_path)

        assert not req_file.exists()

    @pytest.mark.asyncio
    async def test_sweep_keeps_files_from_alive_pid(self, tmp_path: Path) -> None:
        """Files with current process PID are NOT deleted."""
        alive_pid = os.getpid()
        req_file = tmp_path / f"{alive_pid}_aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee.request.json"
        req_file.write_text("{}", encoding="utf-8")

        await sweep_orphaned_files(tmp_path)

        assert req_file.exists()

    @pytest.mark.asyncio
    async def test_sweep_handles_empty_directory(self, tmp_path: Path) -> None:
        """No error when IPC dir is empty."""
        await sweep_orphaned_files(tmp_path)  # Should not raise

    @pytest.mark.asyncio
    async def test_sweep_handles_nonexistent_directory(self, tmp_path: Path) -> None:
        """No error when IPC dir does not exist."""
        nonexistent = tmp_path / "does_not_exist"
        await sweep_orphaned_files(nonexistent)  # Should not raise

    @pytest.mark.asyncio
    async def test_sweep_ignores_non_ipc_files(self, tmp_path: Path) -> None:
        """Files not matching IPC pattern are left alone."""
        non_ipc = tmp_path / "config.json"
        non_ipc.write_text("{}", encoding="utf-8")
        readme = tmp_path / "README.md"
        readme.write_text("# IPC", encoding="utf-8")

        await sweep_orphaned_files(tmp_path)

        assert non_ipc.exists()
        assert readme.exists()

    @pytest.mark.asyncio
    async def test_sweep_removes_both_request_and_response_files(self, tmp_path: Path) -> None:
        """Both .request.json and .response.json from dead PIDs are cleaned."""
        dead_pid = self._dead_pid()
        uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        req_file = tmp_path / f"{dead_pid}_{uid}.request.json"
        resp_file = tmp_path / f"{dead_pid}_{uid}.response.json"
        req_file.write_text("{}", encoding="utf-8")
        resp_file.write_text("{}", encoding="utf-8")

        await sweep_orphaned_files(tmp_path)

        assert not req_file.exists()
        assert not resp_file.exists()

    @pytest.mark.asyncio
    async def test_sweep_handles_tmp_files(self, tmp_path: Path) -> None:
        """Leftover .tmp files are cleaned up during sweep."""
        dead_pid = self._dead_pid()
        uid = "aaaaaaaa-bbbb-cccc-dddd-eeeeeeeeeeee"
        tmp_file = tmp_path / f"{dead_pid}_{uid}.request.json.tmp"
        tmp_file.write_text("{}", encoding="utf-8")

        await sweep_orphaned_files(tmp_path)

        assert not tmp_file.exists()


# ---------------------------------------------------------------------------
# TestRealBridgeSafety
# ---------------------------------------------------------------------------


class TestRealBridgeSafety:
    """SAFE-01: RealBridge refuses instantiation during automated testing."""

    def test_real_bridge_refused_during_pytest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RealBridge() raises RuntimeError when PYTEST_CURRENT_TEST is set."""
        assert os.environ.get("PYTEST_CURRENT_TEST") is not None
        monkeypatch.setenv("OPERATOR_IPC_DIR", str(tmp_path))
        with pytest.raises(RuntimeError, match="PYTEST_CURRENT_TEST"):
            RealBridge(ipc_dir=tmp_path)

    def test_real_bridge_allowed_when_not_in_pytest(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        """RealBridge() succeeds when PYTEST_CURRENT_TEST is NOT set."""
        monkeypatch.delenv("PYTEST_CURRENT_TEST", raising=False)
        monkeypatch.setenv("OPERATOR_IPC_DIR", str(tmp_path))
        bridge = RealBridge(ipc_dir=tmp_path)
        assert hasattr(bridge, "ipc_dir")
        assert bridge.ipc_dir == tmp_path


# ---------------------------------------------------------------------------
# TestExports
# ---------------------------------------------------------------------------


class TestExports:
    """Package-level exports for SimulatorBridge and sweep_orphaned_files."""

    def test_simulator_bridge_not_importable_from_package(self) -> None:
        """from omnifocus_operator.bridge import SimulatorBridge raises ImportError."""
        with pytest.raises(ImportError):
            from omnifocus_operator.bridge import SimulatorBridge  # noqa: F401, PLC0415

    def test_sweep_importable_from_package(self) -> None:
        """from omnifocus_operator.bridge import sweep_orphaned_files works."""
        from omnifocus_operator.bridge import sweep_orphaned_files as sweep  # noqa: PLC0415

        assert sweep is sweep_orphaned_files


# ---------------------------------------------------------------------------
# TestIpcDirProperty
# ---------------------------------------------------------------------------


class TestIpcDirProperty:
    """IPC-06: SimulatorBridge exposes ipc_dir as a read-only property."""

    def test_ipc_dir_property_returns_constructor_path(self, tmp_path: Path) -> None:
        """SimulatorBridge.ipc_dir returns the path passed to __init__."""
        bridge = SimulatorBridge(ipc_dir=tmp_path)
        assert bridge.ipc_dir == tmp_path

    def test_ipc_dir_property_with_custom_path(self, tmp_path: Path) -> None:
        """SimulatorBridge.ipc_dir works with a custom nested path."""
        custom = tmp_path / "custom" / "ipc"
        bridge = SimulatorBridge(ipc_dir=custom)
        assert bridge.ipc_dir == custom
