"""Server module -- FastMCP server for OmniFocus Operator.

The server uses a lifespan context manager to wire the three-layer
architecture: ``FastMCP tool -> OperatorService -> OmniFocusRepository``.
The bridge implementation is selected via the ``OMNIFOCUS_BRIDGE`` env
var (defaulting to ``"real"``).
"""

from __future__ import annotations

import logging
import os
from contextlib import asynccontextmanager
from typing import TYPE_CHECKING, Any

from mcp.server.fastmcp import Context, FastMCP
from mcp.types import ToolAnnotations

# NOTE: DatabaseSnapshot MUST be a runtime import (not TYPE_CHECKING) because
# FastMCP introspects the return type annotation at registration time to
# generate outputSchema.  With `from __future__ import annotations` the
# annotation is a string; FastMCP resolves it via get_type_hints() which
# needs the name in the module namespace.
from omnifocus_operator.models import DatabaseSnapshot  # noqa: TC001

if TYPE_CHECKING:
    from collections.abc import AsyncIterator

__all__ = ["create_server"]

logger = logging.getLogger("omnifocus_operator")


@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    """Create the service stack and yield it for tool handlers.

    The bridge type is read from ``OMNIFOCUS_BRIDGE`` (default ``"real"``).
    For ``"inmemory"`` and ``"simulator"`` a ``ConstantMtimeSource`` is
    used (no cache invalidation).  The ``"real"`` bridge type requires a
    ``FileMtimeSource`` which watches the ``.ofocus`` bundle mtime.
    """
    try:
        from omnifocus_operator.bridge import create_bridge, sweep_orphaned_files
        from omnifocus_operator.repository import (
            ConstantMtimeSource,
            MtimeSource,
            OmniFocusRepository,
        )
        from omnifocus_operator.service import OperatorService

        bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "real")
        logger.info("Bridge type: %s", bridge_type)

        bridge = create_bridge(bridge_type)

        # Sweep orphaned IPC files from dead processes (only for bridge types with IPC)
        if hasattr(bridge, "ipc_dir"):
            logger.info("Sweeping orphaned IPC files...")
            await sweep_orphaned_files(bridge.ipc_dir)
            logger.info("IPC sweep complete")

        # ConstantMtimeSource for inmemory/simulator (no cache invalidation needed)
        # FileMtimeSource for real (watches .ofocus bundle mtime)
        mtime_source: MtimeSource
        if bridge_type in ("inmemory", "simulator"):
            mtime_source = ConstantMtimeSource()
        else:  # pragma: no cover — SAFE-01: real bridge path, tested via UAT
            from omnifocus_operator.bridge.real import DEFAULT_OFOCUS_PATH
            from omnifocus_operator.repository import FileMtimeSource

            ofocus_path = os.environ.get("OMNIFOCUS_OFOCUS_PATH", str(DEFAULT_OFOCUS_PATH))
            if not os.path.exists(ofocus_path):
                logger.error(
                    "OmniFocus database not found at: %s — "
                    "set OMNIFOCUS_OFOCUS_PATH or verify OmniFocus 4 is installed.",
                    ofocus_path,
                )
                raise FileNotFoundError(f"OmniFocus database not found: {ofocus_path}")
            mtime_source = FileMtimeSource(path=ofocus_path)

        repository = OmniFocusRepository(bridge=bridge, mtime_source=mtime_source)
        service = OperatorService(repository=repository)

        yield {"service": service}

        logger.info("Server shutting down")
    except Exception as exc:
        logger.exception("Fatal error during startup")
        from omnifocus_operator.service import ErrorOperatorService

        error_service = ErrorOperatorService(exc)
        yield {"service": error_service}
        logger.info("Error-mode server shutting down")


def _register_tools(mcp: FastMCP) -> None:
    """Register all MCP tools on the given server instance.

    Separated from ``create_server`` so tests can register tools on a
    custom server with a patched lifespan.
    """

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def list_all(ctx: Context[Any, Any, Any]) -> DatabaseSnapshot:
        """Return the full OmniFocus database as structured data.

        Returns all tasks, projects, tags, folders, and perspectives as a
        single snapshot.  The response uses camelCase field names.
        """
        from omnifocus_operator.service import OperatorService  # noqa: TC001

        service: OperatorService = ctx.request_context.lifespan_context["service"]
        return await service.get_all_data()


def create_server() -> FastMCP:
    """Create and return a configured FastMCP server instance.

    The server is not started -- call ``server.run(transport="stdio")``
    or use the in-process testing pattern with ``server._mcp_server.run()``.
    """
    mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
    _register_tools(mcp)
    return mcp
