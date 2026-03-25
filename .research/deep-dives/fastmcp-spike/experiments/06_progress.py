"""Experiment 06: Progress Reporting — Does the Client Render It?

QUESTION: Does ctx.report_progress() emit events the client can see?
This can only be answered by connecting a real client.

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/06_progress.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio

  Option B — Claude Code:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 06
    2. Restart Claude Code (or reload MCP servers)
    3. Ask Claude to call the tools
    4. When done: uv run python .../setup_mcp.py remove

GUIDED WALKTHROUGH:
  1. Call `process_batch` with {"items": ["task1", "task2", "task3", "task4", "task5"]}
     - Do you see a progress indicator? A percentage? Individual updates?
     - Each item takes 500ms — slow enough to observe.
     - What does Claude Code show? What does Inspector show?

  2. Call `process_with_messages` — same as above but with status messages.
     - Does the message text appear alongside the progress?

  3. Call `process_unknown_total` — progress without knowing the total.
     - Does the client handle indeterminate progress?
     - Or does it just ignore it?
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP, Context


mcp = FastMCP("progress-spike")


@mcp.tool()
async def process_batch(items: list[str], ctx: Context) -> dict[str, Any]:
    """Process items with progress updates. Each item takes 500ms."""
    total = len(items)
    results = []

    for i, item in enumerate(items):
        await ctx.report_progress(progress=i, total=total)
        await asyncio.sleep(0.5)  # Slow enough to observe
        results.append(item.upper())

    await ctx.report_progress(progress=total, total=total)

    return {"processed": len(results), "results": results}


@mcp.tool()
async def process_with_messages(items: list[str], ctx: Context) -> dict[str, Any]:
    """Progress updates WITH status messages."""
    total = len(items)
    results = []

    for i, item in enumerate(items):
        await ctx.report_progress(progress=i, total=total)
        await ctx.info(f"Processing item {i+1}/{total}: {item}")
        await asyncio.sleep(0.5)
        results.append(item.upper())

    await ctx.report_progress(progress=total, total=total)
    await ctx.info(f"All {total} items processed")

    return {"processed": len(results), "results": results}


@mcp.tool()
async def process_unknown_total(ctx: Context) -> str:
    """Progress without knowing the total — indeterminate progress."""
    for i in range(5):
        await ctx.report_progress(progress=i)
        await ctx.info(f"Discovered item {i+1}...")
        await asyncio.sleep(0.5)
    return "Processed 5 items (total was unknown upfront)"


if __name__ == "__main__":
    mcp.run(transport="stdio")
