"""Lifespan context manager for the FastMCP server.

Creates the service stack (repository + preferences -> OperatorService)
and yields it for tool handlers.  Falls back to ErrorOperatorService
on startup failure so the server can still serve diagnostic responses.
"""

from __future__ import annotations

import logging
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING

from fastmcp import FastMCP

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

logger = logging.getLogger(__name__)


@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    """Create the service stack and yield it for tool handlers.

    1. IPC sweep runs first (always, regardless of repository mode).
    2. ``create_repository()`` selects the repository based on
       ``OPERATOR_REPOSITORY`` env var (default ``"hybrid"``).
    3. Startup errors are caught and served through ``ErrorOperatorService``.
    """
    # IPC sweep always runs -- cleans orphaned files from dead processes.
    # This is safe even when using sqlite mode (sweep handles missing dirs).
    from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, sweep_orphaned_files

    logger.info("Sweeping orphaned IPC files...")
    await sweep_orphaned_files(DEFAULT_IPC_DIR)
    logger.info("IPC sweep complete")

    try:
        from omnifocus_operator.config import get_settings
        from omnifocus_operator.repository import create_real_bridge, create_repository
        from omnifocus_operator.service import OperatorService
        from omnifocus_operator.service.preferences import OmniFocusPreferences

        repo_type = get_settings().repository
        logger.info("Repository type: %s", repo_type)

        bridge = create_real_bridge()
        repository = create_repository(bridge, repo_type)
        preferences = OmniFocusPreferences(bridge)
        service = OperatorService(repository=repository, preferences=preferences)

        yield {"service": service}

        logger.info("Server shutting down")
    except Exception as exc:
        logger.exception("Fatal error during startup")
        from omnifocus_operator.service import ErrorOperatorService

        error_service = ErrorOperatorService(exc)
        yield {"service": error_service}
        logger.info("Error-mode server shutting down")
