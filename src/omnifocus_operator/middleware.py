"""Middleware module -- cross-cutting concerns for MCP tool calls."""

from __future__ import annotations

import logging
import time
from typing import Any

from fastmcp.server.middleware import Middleware, MiddlewareContext

__all__ = ["ToolLoggingMiddleware"]


class ToolLoggingMiddleware(Middleware):
    """Log every tool call with name, arguments, timing, and errors.

    Receives an injected logger (per D-02) so all log lines appear under
    the server's namespace rather than a middleware-specific one.
    """

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    async def on_call_tool(
        self, context: MiddlewareContext, call_next: Any
    ) -> Any:
        tool_name = context.message.name
        args = context.message.arguments
        # D-04: Log full arguments at INFO on entry
        if args:
            self._log.info(">>> %s(%s)", tool_name, args)
        else:
            self._log.info(">>> %s()", tool_name)
        start = time.monotonic()
        try:
            result = await call_next(context)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.info("<<< %s -- %.1fms OK", tool_name, elapsed_ms)
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.error("!!! %s -- %.1fms FAILED: %s", tool_name, elapsed_ms, e)
            raise
