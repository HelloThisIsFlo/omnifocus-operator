"""Bridge protocol -- structural typing interface for OmniFocus data sources."""

from __future__ import annotations

from typing import Any, Protocol


class Bridge(Protocol):
    """Protocol for OmniFocus bridge implementations.

    Any class with a matching ``async send_command`` method satisfies this
    protocol via structural subtyping -- no inheritance required.
    """

    async def send_command(
        self,
        operation: str,
        params: dict[str, Any] | None = None,
    ) -> dict[str, Any]:
        """Send a command to OmniFocus and return the raw response."""
        ...
