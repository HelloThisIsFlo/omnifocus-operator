"""Experiment 05: Middleware — Timing, Logging, Error Handling

QUESTION: What middleware exists? Could it replace our manual _log_tool_call()?
What happens when middleware catches an error?

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/05_middleware.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio

  Option B — Claude Code:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 05
    2. Restart Claude Code (or reload MCP servers)
    3. Ask Claude to call the tools
    4. When done: uv run python .../setup_mcp.py remove

GUIDED WALKTHROUGH:
  1. Call `fast_tool` — check your client.
     - Does any timing info appear? A log message?
     - The middleware logs to ctx.info() — does the client show it?

  2. Call `slow_tool` — this takes ~500ms.
     - Compare the timing output to fast_tool.

  3. Call `failing_tool` — this raises ValueError.
     - Does the client get a clean error message?
     - Or a raw traceback?
     - Check if the middleware caught it.

  4. After calling all tools, check:
     - /tmp/fastmcp-spike-middleware.log for server-side timing data
     - The middleware captures every call with duration — useful?
"""

from __future__ import annotations

import asyncio
import logging
import time
from typing import Any

from fastmcp import FastMCP, Context
from fastmcp.server.middleware import Middleware, MiddlewareContext

# ── File logger for server-side timing records ───────────────────────

LOG_FILE = "/tmp/fastmcp-spike-middleware.log"
file_logger = logging.getLogger("spike_middleware")
file_logger.setLevel(logging.DEBUG)
file_logger.propagate = False
handler = logging.FileHandler(LOG_FILE, mode="w")
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(message)s"))
file_logger.addHandler(handler)


# ── Custom Middleware: Tool Timing ───────────────────────────────────

class ToolTimingMiddleware(Middleware):
    """Logs every tool call with duration — potential replacement for _log_tool_call()."""

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        start = time.monotonic()

        # Extract tool name from the request
        tool_name = "unknown"
        if hasattr(context, "params") and isinstance(context.params, dict):
            tool_name = context.params.get("name", "unknown")

        file_logger.info(f">>> {tool_name} — starting")

        try:
            result = await call_next(context)
            elapsed_ms = (time.monotonic() - start) * 1000
            file_logger.info(f"<<< {tool_name} — {elapsed_ms:.1f}ms (success)")
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            file_logger.info(f"!!! {tool_name} — {elapsed_ms:.1f}ms (FAILED: {e})")
            raise


# ── Server ───────────────────────────────────────────────────────────

mcp = FastMCP("middleware-spike")
mcp.add_middleware(ToolTimingMiddleware())


@mcp.tool()
async def fast_tool(ctx: Context) -> str:
    """Returns immediately. Check timing output."""
    await ctx.info("fast_tool: executing (should be <5ms)")
    return "fast!"


@mcp.tool()
async def slow_tool(ctx: Context) -> str:
    """Takes ~500ms. Compare timing with fast_tool."""
    await ctx.info("slow_tool: starting 500ms work...")
    await asyncio.sleep(0.5)
    await ctx.info("slow_tool: done")
    return "slow but done!"


@mcp.tool()
async def failing_tool() -> str:
    """Raises ValueError. What does the client see?"""
    raise ValueError("Something went wrong — does middleware catch this cleanly?")


@mcp.tool()
async def check_timing_log() -> dict[str, str]:
    """Returns the contents of the middleware timing log."""
    try:
        with open(LOG_FILE) as f:
            return {"log_file": LOG_FILE, "contents": f.read()}
    except FileNotFoundError:
        return {"log_file": LOG_FILE, "contents": "(file not found)"}


if __name__ == "__main__":
    file_logger.info("=== Middleware spike server starting ===")
    mcp.run(transport="stdio")
