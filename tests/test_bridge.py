"""Tests for the bridge protocol, error hierarchy, and InMemoryBridge."""

from __future__ import annotations

import pytest

from omnifocus_operator.bridge import (
    Bridge,
    BridgeConnectionError,
    BridgeError,
    BridgeProtocolError,
    BridgeTimeoutError,
)
from tests.doubles import BridgeCall, InMemoryBridge

# ---------------------------------------------------------------------------
# Error hierarchy
# ---------------------------------------------------------------------------


class TestBridgeErrors:
    """BridgeError hierarchy: base + timeout + connection + protocol."""

    def test_all_errors_inherit_from_bridge_error(self) -> None:
        """All specific errors are subclasses of BridgeError."""
        assert issubclass(BridgeTimeoutError, BridgeError)
        assert issubclass(BridgeConnectionError, BridgeError)
        assert issubclass(BridgeProtocolError, BridgeError)

    def test_bridge_error_stores_operation(self) -> None:
        """BridgeError exposes the operation that failed."""
        err = BridgeError("snapshot", "something broke")
        assert err.operation == "snapshot"
        assert str(err) == "something broke"

    def test_bridge_error_chaining(self) -> None:
        """BridgeError supports exception chaining via __cause__."""
        original = OSError("disk full")
        err = BridgeError("snapshot", "write failed", cause=original)
        assert err.__cause__ is original

    def test_bridge_error_no_cause_defaults_to_none(self) -> None:
        """BridgeError.__cause__ is None when no cause is provided."""
        err = BridgeError("snapshot", "fail")
        assert err.__cause__ is None

    def test_timeout_error_message_format(self) -> None:
        """BridgeTimeoutError formats message with operation and seconds."""
        err = BridgeTimeoutError("snapshot", timeout_seconds=10.0)
        assert str(err) == (
            "OmniFocus did not respond within 10.0s (operation: 'snapshot'). Is OmniFocus running?"
        )
        assert err.operation == "snapshot"
        assert err.timeout_seconds == 10.0

    def test_connection_error_message_format(self) -> None:
        """BridgeConnectionError formats message with reason."""
        err = BridgeConnectionError("snapshot", reason="app not running")
        assert str(err) == "Cannot connect to OmniFocus: app not running"
        assert err.operation == "snapshot"
        assert err.reason == "app not running"

    def test_protocol_error_message_format(self) -> None:
        """BridgeProtocolError formats message with operation and detail."""
        err = BridgeProtocolError("snapshot", detail="invalid JSON")
        assert str(err) == "Protocol error on 'snapshot': invalid JSON"
        assert err.operation == "snapshot"
        assert err.detail == "invalid JSON"

    def test_timeout_error_chaining(self) -> None:
        """BridgeTimeoutError supports exception chaining."""
        original = TimeoutError("OS timeout")
        err = BridgeTimeoutError("snapshot", timeout_seconds=5.0, cause=original)
        assert err.__cause__ is original

    def test_connection_error_chaining(self) -> None:
        """BridgeConnectionError supports exception chaining."""
        original = ConnectionRefusedError("refused")
        err = BridgeConnectionError("snapshot", reason="refused", cause=original)
        assert err.__cause__ is original

    def test_protocol_error_chaining(self) -> None:
        """BridgeProtocolError supports exception chaining."""
        original = ValueError("bad json")
        err = BridgeProtocolError("snapshot", detail="parse fail", cause=original)
        assert err.__cause__ is original


# ---------------------------------------------------------------------------
# InMemoryBridge
# ---------------------------------------------------------------------------


class TestInMemoryBridge:
    """InMemoryBridge: data return, call tracking, error simulation."""

    async def test_send_command_returns_data(self) -> None:
        """send_command returns the configured data dict."""
        data = {"tasks": [], "projects": []}
        bridge = InMemoryBridge(data=data)

        result = await bridge.send_command("snapshot")

        assert result == data

    async def test_send_command_with_params(self) -> None:
        """send_command records params in call history."""
        bridge = InMemoryBridge(data={})
        params = {"task_id": "abc-123"}

        await bridge.send_command("complete_task", params=params)

        assert bridge.calls[0].params == {"task_id": "abc-123"}

    async def test_call_count(self) -> None:
        """call_count returns number of invocations."""
        bridge = InMemoryBridge(data={})

        await bridge.send_command("snapshot")
        await bridge.send_command("snapshot")

        assert bridge.call_count == 2

    async def test_calls_returns_bridge_call_records(self) -> None:
        """calls returns list of BridgeCall records."""
        bridge = InMemoryBridge(data={})

        await bridge.send_command("snapshot")
        await bridge.send_command("complete_task", params={"id": "1"})

        assert bridge.calls == [
            BridgeCall(operation="snapshot", params=None),
            BridgeCall(operation="complete_task", params={"id": "1"}),
        ]

    async def test_calls_returns_copy(self) -> None:
        """Mutating calls does not affect internal state."""
        bridge = InMemoryBridge(data={})
        await bridge.send_command("snapshot")

        calls_copy = bridge.calls
        calls_copy.clear()

        assert bridge.call_count == 1
        assert len(bridge.calls) == 1

    async def test_error_simulation(self) -> None:
        """set_error causes send_command to raise the configured error."""
        bridge = InMemoryBridge(data={})
        bridge.set_error(BridgeTimeoutError("snapshot", timeout_seconds=10.0))

        with pytest.raises(BridgeTimeoutError) as exc_info:
            await bridge.send_command("snapshot")

        assert exc_info.value.operation == "snapshot"
        assert exc_info.value.timeout_seconds == 10.0

    async def test_call_recorded_before_error(self) -> None:
        """Call is recorded BEFORE error is raised."""
        bridge = InMemoryBridge(data={})
        bridge.set_error(BridgeError("test", "fail"))

        with pytest.raises(BridgeError):
            await bridge.send_command("snapshot")

        assert bridge.call_count == 1

    async def test_clear_error(self) -> None:
        """clear_error removes the configured error."""
        bridge = InMemoryBridge(data={"ok": True})
        bridge.set_error(BridgeError("test", "fail"))
        bridge.clear_error()

        result = await bridge.send_command("snapshot")

        assert result == {"ok": True}

    async def test_default_empty_data(self) -> None:
        """InMemoryBridge() defaults to empty dict."""
        bridge = InMemoryBridge()

        result = await bridge.send_command("snapshot")

        assert result == {}

    async def test_data_none_defaults_to_empty_dict(self) -> None:
        """InMemoryBridge(data=None) defaults to empty dict."""
        bridge = InMemoryBridge(data=None)

        result = await bridge.send_command("snapshot")

        assert result == {}

    def test_bridge_call_is_frozen(self) -> None:
        """BridgeCall is immutable (frozen dataclass)."""
        call = BridgeCall(operation="snapshot", params=None)

        with pytest.raises(AttributeError):
            call.operation = "other"  # type: ignore[misc]


# ---------------------------------------------------------------------------
# Protocol satisfaction
# ---------------------------------------------------------------------------


class TestBridgeProtocol:
    """Bridge protocol: structural typing satisfaction."""

    def test_in_memory_bridge_satisfies_protocol(self) -> None:
        """InMemoryBridge structurally satisfies the Bridge protocol.

        If this line type-checks with mypy --strict, the protocol is satisfied.
        No isinstance check -- structural typing is static.
        """
        bridge: Bridge = InMemoryBridge(data={})
        assert bridge is not None


# ---------------------------------------------------------------------------
# Negative import tests -- old production paths are broken (Phase 24)
# ---------------------------------------------------------------------------


class TestTestDoubleRelocation:
    """Test doubles are NOT importable from old production paths (Phase 24)."""

    def test_in_memory_bridge_not_importable_from_old_path(self) -> None:
        """in_memory module removed from bridge package."""
        with pytest.raises(ModuleNotFoundError):
            from omnifocus_operator.bridge.in_memory import InMemoryBridge  # noqa: F401, F811

    def test_bridge_call_not_importable_from_old_path(self) -> None:
        """BridgeCall removed with in_memory module."""
        with pytest.raises(ModuleNotFoundError):
            from omnifocus_operator.bridge.in_memory import BridgeCall  # noqa: F401, F811

    def test_simulator_bridge_not_importable_from_old_path(self) -> None:
        """simulator module removed from bridge package."""
        with pytest.raises(ModuleNotFoundError):
            from omnifocus_operator.bridge.simulator import SimulatorBridge  # noqa: F401

    def test_in_memory_repository_not_importable_from_old_path(self) -> None:
        """in_memory module removed from repository package."""
        with pytest.raises(ModuleNotFoundError):
            from omnifocus_operator.repository.in_memory import InMemoryRepository  # noqa: F401

    def test_constant_mtime_source_not_importable_from_old_path(self) -> None:
        """ConstantMtimeSource removed from bridge.mtime module."""
        with pytest.raises(ImportError):
            from omnifocus_operator.bridge.mtime import ConstantMtimeSource  # noqa: F401
