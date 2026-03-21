"""Canned-response test bridge.

Returns seed data for every operation without maintaining state.
Use InMemoryBridge for stateful snapshot testing.
"""

from __future__ import annotations

from pathlib import Path
from typing import Any

from omnifocus_operator.contracts.protocols import Bridge
from tests.doubles.bridge import BridgeCall


class StubBridge(Bridge):
    """Canned-response test bridge.

    Returns seed data for every operation without maintaining state.
    Use InMemoryBridge for stateful snapshot testing.
    """

    def __init__(
        self,
        data: dict[str, Any] | None = None,
        wal_path: str | Path | None = None,
    ) -> None:
        self._data: dict[str, Any] = data if data is not None else {}
        self._calls: list[BridgeCall] = []
        self._error: Exception | None = None
        self._wal_path: Path | None = Path(wal_path) if wal_path else None
        if self._wal_path:
            self._wal_path.touch()

    @property
    def calls(self) -> list[BridgeCall]:
        """Copy of recorded calls (prevents external mutation)."""
        return list(self._calls)

    @property
    def call_count(self) -> int:
        """Number of ``send_command`` invocations."""
        return len(self._calls)

    def set_error(self, error: Exception) -> None:
        """Configure an error to raise on the next ``send_command``."""
        self._error = error

    def clear_error(self) -> None:
        """Remove the configured error so subsequent calls succeed."""
        self._error = None

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Record call, optionally raise error, touch WAL, return seed data."""
        self._calls.append(BridgeCall(operation=operation, params=params))
        if self._error is not None:
            raise self._error
        if self._wal_path:
            self._wal_path.write_bytes(b"flushed")
        return self._data
