"""Experiment 05: Middleware — Stacking Multiple Middleware

QUESTION: Can we stack middleware? How do they compose?
Could middleware replace our manual log_tool_call() with automatic
timing + logging to both stderr and file?

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/05_middleware.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio

  Option B — Claude Code / Desktop:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 05
    2. Restart client
    3. Call the tools

GUIDED WALKTHROUGH:
  1. Call `fast_tool` — check stderr (Claude Desktop log page) AND /tmp/fastmcp-spike-middleware.log
     - Do both middleware fire? In what order?
  2. Call `slow_tool` — does timing show up in both places?
  3. Call `failing_tool` — does error handling work across the middleware stack?
  4. Call `check_timing_log` — see the file log contents
"""

from __future__ import annotations

import asyncio
import logging
import sys
import time
from typing import Any

from fastmcp import FastMCP, Context
from fastmcp.server.middleware import Middleware, MiddlewareContext

# ── Logger factory ───────────────────────────────────────────────────

LOG_FILE = "/tmp/fastmcp-spike-middleware.log"


def create_logger(name: str, handler: logging.Handler, formatter: logging.Formatter) -> logging.Logger:
    handler.setFormatter(formatter)
    logger = logging.getLogger(name)
    logger.setLevel(logging.DEBUG)
    logger.propagate = False
    logger.addHandler(handler)
    return logger


file_logger = create_logger(
    "middleware.file",
    logging.FileHandler(LOG_FILE, mode="w"),
    logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s"),
)

stderr_logger = create_logger(
    "middleware.stderr",
    logging.StreamHandler(sys.stderr),
    logging.Formatter("%(asctime)s %(levelname)-8s [%(name)s] %(message)s", datefmt="%H:%M:%S"),
)


# ── Reusable logging middleware ───────────────────────────────────────

class ToolLoggingMiddleware(Middleware):
    """Logs tool calls with timing. Inject any logger you want."""

    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        tool_name = context.message.name
        start = time.monotonic()

        args = context.message.arguments
        self._log.info(f">>> {tool_name}({args})" if args else f">>> {tool_name}()")

        try:
            result = await call_next(context)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.info(f"<<< {tool_name} — {elapsed_ms:.1f}ms OK")
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.error(f"!!! {tool_name} — {elapsed_ms:.1f}ms FAILED: {e}")
            raise


# ── Server ───────────────────────────────────────────────────────────

mcp = FastMCP("middleware-spike")
mcp.add_middleware(ToolLoggingMiddleware(stderr_logger))
mcp.add_middleware(ToolLoggingMiddleware(file_logger))


@mcp.tool()
async def echo(text: str) -> str:
    """Returns the text uppercased. Tests argument logging in middleware."""
    return text.upper()


@mcp.tool()
async def fast_tool(ctx: Context) -> str:
    """Returns immediately. Check both log destinations."""
    return "fast!"


@mcp.tool()
async def slow_tool(ctx: Context) -> str:
    """Takes ~500ms. Compare timing in both logs."""
    await asyncio.sleep(0.5)
    return "slow but done!"


@mcp.tool()
async def failing_tool() -> str:
    """Raises ValueError. Do both middleware catch it?"""
    raise ValueError("Something went wrong — does the middleware stack handle this?")


@mcp.tool()
async def check_timing_log() -> dict[str, str]:
    """Returns the file log contents so you can compare with stderr."""
    try:
        with open(LOG_FILE) as f:
            return {"log_file": LOG_FILE, "contents": f.read()}
    except FileNotFoundError:
        return {"log_file": LOG_FILE, "contents": "(file not found)"}


if __name__ == "__main__":
    file_logger.info("=== Middleware spike server starting ===")
    stderr_logger.info("=== Middleware spike server starting ===")
    mcp.run(transport="stdio")
