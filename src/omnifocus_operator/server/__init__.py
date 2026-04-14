"""Server package -- FastMCP server for OmniFocus Operator."""

from __future__ import annotations

import logging

from fastmcp import FastMCP

from omnifocus_operator.middleware import (
    ToolLoggingMiddleware,
    ValidationReformatterMiddleware,
)
from omnifocus_operator.server.handlers import _register_tools
from omnifocus_operator.server.lifespan import app_lifespan

__all__ = ["create_server"]

logger = logging.getLogger(__name__)


def create_server() -> FastMCP:
    """Create and return a configured FastMCP server instance.

    The server is not started -- call ``server.run(transport="stdio")``
    or use the in-process testing pattern with ``server._mcp_server.run()``.
    """
    mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
    _register_tools(mcp)
    mcp.add_middleware(ValidationReformatterMiddleware())  # innermost (added first)
    mcp.add_middleware(ToolLoggingMiddleware(logger))  # outermost (added second)
    return mcp
