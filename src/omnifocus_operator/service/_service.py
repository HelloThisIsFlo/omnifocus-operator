"""OperatorService -- thin passthrough to the repository layer.

The service layer provides the primary API surface for the MCP server.
Currently a simple delegation to ``OmniFocusRepository``; future phases
may add orchestration, caching policies, or multi-repository coordination.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, NoReturn

if TYPE_CHECKING:
    from omnifocus_operator.models.snapshot import DatabaseSnapshot
    from omnifocus_operator.repository._repository import OmniFocusRepository

logger = logging.getLogger("omnifocus_operator")


class OperatorService:
    """Service layer that delegates to the OmniFocus repository.

    Parameters
    ----------
    repository:
        The underlying ``OmniFocusRepository`` that fetches and caches
        ``DatabaseSnapshot`` instances from the bridge.
    """

    def __init__(self, repository: OmniFocusRepository) -> None:
        self._repository = repository

    async def get_all_data(self) -> DatabaseSnapshot:
        """Return the current ``DatabaseSnapshot`` from the repository.

        Delegates directly to ``repository.get_snapshot()``.  Any errors
        from the repository (bridge errors, validation errors, mtime
        errors) propagate to the caller unchanged.
        """
        return await self._repository.get_snapshot()


class ErrorOperatorService(OperatorService):
    """Stand-in service that raises on every attribute access.

    Used when the server fails to start (e.g. missing OmniFocus database).
    Instead of crashing, the MCP server stays alive in degraded mode and
    serves the startup error through tool responses.
    """

    def __init__(self, error: Exception) -> None:
        # Bypass OperatorService.__init__ -- we have no repository.
        # Use object.__setattr__ to avoid triggering __getattr__.
        object.__setattr__(
            self,
            "_error_message",
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\nRestart the server after fixing.",
        )

    def __getattr__(self, name: str) -> NoReturn:
        """Intercept every attribute access and raise with the startup error."""
        logger.warning("Tool call in error mode (attribute: %s)", name)
        raise RuntimeError(self._error_message)
