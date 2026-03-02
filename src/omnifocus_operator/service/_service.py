"""OperatorService -- thin passthrough to the repository layer.

The service layer provides the primary API surface for the MCP server.
Currently a simple delegation to ``OmniFocusRepository``; future phases
may add orchestration, caching policies, or multi-repository coordination.
"""

from __future__ import annotations

from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.models._snapshot import DatabaseSnapshot
    from omnifocus_operator.repository._repository import OmniFocusRepository


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
