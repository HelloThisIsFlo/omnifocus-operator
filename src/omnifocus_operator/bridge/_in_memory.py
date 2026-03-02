"""InMemoryBridge -- test double that returns data from memory."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any


@dataclass(frozen=True)
class BridgeCall:
    """Record of a single ``send_command`` invocation."""

    operation: str
    params: dict[str, Any] | None


class InMemoryBridge:
    """Test bridge: returns data from memory with call tracking.

    Designed for unit tests.  Supports:
    - Constructor-injected return data
    - Full call history via ``calls`` / ``call_count``
    - Configurable error simulation via ``set_error`` / ``clear_error``
    """

    def __init__(self, data: dict[str, Any] | None = None) -> None:
        self._data: dict[str, Any] = data if data is not None else {}
        self._calls: list[BridgeCall] = []
        self._error: Exception | None = None

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
        """Record call, optionally raise error, return data."""
        self._calls.append(BridgeCall(operation=operation, params=params))
        if self._error is not None:
            raise self._error
        return self._data
