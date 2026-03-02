"""FastMCP server setup, lifespan, and tool registration.

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

logger = logging.getLogger("omnifocus_operator")


@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    """Create the service stack and pre-warm the repository cache.

    The bridge type is read from ``OMNIFOCUS_BRIDGE`` (default ``"real"``).
    For ``"inmemory"`` a ``ConstantMtimeSource`` is used (no cache
    invalidation).  Other bridge types require a ``FileMtimeSource`` path
    which is not yet configured -- they raise ``NotImplementedError``.
    """
    from omnifocus_operator.bridge import create_bridge, sweep_orphaned_files
    from omnifocus_operator.repository import ConstantMtimeSource, OmniFocusRepository
    from omnifocus_operator.service import OperatorService

    bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "real")
    logger.info("Bridge type: %s", bridge_type)

    bridge = create_bridge(bridge_type)

    # Sweep orphaned IPC files from dead processes (only for bridge types with IPC)
    if hasattr(bridge, "ipc_dir"):
        logger.info("Sweeping orphaned IPC files...")
        await sweep_orphaned_files(bridge.ipc_dir)
        logger.info("IPC sweep complete")

    # ConstantMtimeSource for inmemory (no cache invalidation needed)
    # FileMtimeSource for real/simulator (future phases)
    if bridge_type == "inmemory":
        mtime_source = ConstantMtimeSource()
    else:
        msg = f"FileMtimeSource path not configured for bridge type: {bridge_type}"
        raise NotImplementedError(msg)

    repository = OmniFocusRepository(bridge=bridge, mtime_source=mtime_source)
    service = OperatorService(repository=repository)

    logger.info("Pre-warming repository cache...")
    await repository.initialize()
    logger.info("Cache pre-warmed successfully")

    yield {"service": service}

    logger.info("Server shutting down")


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
