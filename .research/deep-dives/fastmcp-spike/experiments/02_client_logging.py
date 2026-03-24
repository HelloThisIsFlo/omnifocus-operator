"""Experiment 02: Client-Facing Logging — Protocol-Level Messages

QUESTION: How does ctx.info() / ctx.warning() / ctx.error() work?
What does the client actually see?

CONTEXT FROM DOCS:
  "This documentation covers MCP client logging — sending messages from
   your server to MCP clients."

These are NOT regular Python logs. They flow through the MCP protocol
to the connected client (Claude Desktop, Claude Code, etc.).

WHAT TO LOOK FOR:
- Do all 4 levels (debug, info, warning, error) arrive at the client?
- What format are the messages in?
- Are they blocking or fire-and-forget?
- Can you pass structured data via `extra`?
- What happens if the client doesn't support logging?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/02_client_logging.py
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP, Context, Client


mcp = FastMCP("logging-spike")


@mcp.tool()
async def log_everything(ctx: Context) -> dict[str, str]:
    """Tool that exercises all 4 logging levels."""

    # Level 1: debug
    await ctx.debug("This is a DEBUG message — most verbose")

    # Level 2: info
    await ctx.info("This is an INFO message — general status")

    # Level 3: warning
    await ctx.warning("This is a WARNING — something might be wrong")

    # Level 4: error
    await ctx.error("This is an ERROR — something went wrong")

    return {"status": "all 4 log levels emitted"}


@mcp.tool()
async def log_with_data(ctx: Context) -> dict[str, str]:
    """Tool that logs with structured extra data."""

    # The docs mention `extra` parameter for structured data
    # Let's see if it works and what it looks like
    try:
        await ctx.info("Processing batch", extra={"batch_size": 5, "tool": "add_tasks"})
        return {"status": "structured logging works!"}
    except TypeError as e:
        # Maybe `extra` isn't a valid kwarg?
        return {"status": f"structured logging failed: {e}"}


@mcp.tool()
async def log_timing_test(ctx: Context) -> dict[str, Any]:
    """Tool that tests whether logging is blocking."""
    import time

    start = time.monotonic()
    for i in range(10):
        await ctx.info(f"Message {i}")
    elapsed = time.monotonic() - start

    return {
        "messages_sent": 10,
        "elapsed_seconds": round(elapsed, 4),
        "per_message_ms": round(elapsed / 10 * 1000, 2),
    }


# --- Client with logging handler ---
async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 02: Client-Facing Logging")
    print("=" * 60)

    # Capture log messages on the client side
    received_logs: list[dict[str, Any]] = []

    def log_handler(level: str, message: str, logger_name: str | None = None) -> None:
        entry = {"level": level, "message": message, "logger": logger_name}
        received_logs.append(entry)
        print(f"  [CLIENT RECEIVED] level={level} logger={logger_name} msg={message}")

    async with Client(mcp, log_handler=log_handler) as client:
        # Test 1: All 4 levels
        print("\n--- Test 1: Log all 4 levels ---")
        received_logs.clear()
        result = await client.call_tool("log_everything", {})
        print(f"  Tool result: {result}")
        print(f"  Logs received: {len(received_logs)}")
        for log in received_logs:
            print(f"    {log}")

        # Test 2: Structured data
        print("\n--- Test 2: Structured extra data ---")
        received_logs.clear()
        result = await client.call_tool("log_with_data", {})
        print(f"  Tool result: {result}")
        print(f"  Logs received: {len(received_logs)}")
        for log in received_logs:
            print(f"    {log}")

        # Test 3: Timing
        print("\n--- Test 3: Logging performance ---")
        received_logs.clear()
        result = await client.call_tool("log_timing_test", {})
        print(f"  Tool result: {result}")

    # Test 4: Client WITHOUT log handler
    print("\n--- Test 4: Client without log_handler (do messages get lost?) ---")
    async with Client(mcp) as client:
        result = await client.call_tool("log_everything", {})
        print(f"  Tool result: {result}")
        print("  (No handler — check if errors or silent)")

    print("\n" + "=" * 60)
    print("EXPERIMENT 02 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
