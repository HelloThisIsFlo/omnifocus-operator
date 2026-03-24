"""Experiment 07: Progress Reporting — Bulk Operations

QUESTION: Does ctx.report_progress() emit events a client can see?

CONTEXT:
  add_tasks and edit_tasks process batches. Progress reporting could
  improve agent UX for large batches.

WHAT TO LOOK FOR:
- Does report_progress() work?
- Does the Client receive progress events?
- What does the progress handler signature look like?
- Is this something Claude Desktop / Claude Code would display?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/07_progress.py
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP, Context, Client


mcp = FastMCP("progress-spike")


@mcp.tool()
async def process_batch(items: list[str], ctx: Context) -> dict[str, Any]:
    """Process a batch of items with progress updates."""
    total = len(items)
    results = []

    for i, item in enumerate(items):
        await ctx.report_progress(progress=i, total=total)
        await asyncio.sleep(0.05)  # Simulate work
        results.append(item.upper())

    # Final progress
    await ctx.report_progress(progress=total, total=total)

    return {"processed": len(results), "results": results}


@mcp.tool()
async def process_unknown_total(ctx: Context) -> str:
    """Progress without knowing total — does it work?"""
    for i in range(5):
        await ctx.report_progress(progress=i)  # No total
        await asyncio.sleep(0.05)
    return "done"


async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 07: Progress Reporting")
    print("=" * 60)

    # Capture progress events
    progress_events: list[dict[str, Any]] = []

    def progress_handler(
        progress: float,
        total: float | None = None,
        message: str | None = None,
    ) -> None:
        event = {"progress": progress, "total": total, "message": message}
        progress_events.append(event)
        pct = f"{progress}/{total}" if total else f"{progress}/?"
        print(f"  [PROGRESS] {pct} {message or ''}")

    # Test 1: Batch with known total
    print("\n--- Test 1: Batch processing with known total ---")
    progress_events.clear()
    try:
        async with Client(mcp, progress_handler=progress_handler) as client:
            result = await client.call_tool(
                "process_batch",
                {"items": ["task1", "task2", "task3", "task4", "task5"]},
            )
            print(f"  Result: {result}")
            print(f"  Progress events received: {len(progress_events)}")
    except TypeError as e:
        print(f"  progress_handler not supported on Client(): {e}")
        print("  Trying without progress handler...")
        async with Client(mcp) as client:
            result = await client.call_tool(
                "process_batch",
                {"items": ["task1", "task2", "task3"]},
            )
            print(f"  Result: {result}")

    # Test 2: Unknown total
    print("\n--- Test 2: Progress without total ---")
    progress_events.clear()
    try:
        async with Client(mcp, progress_handler=progress_handler) as client:
            result = await client.call_tool("process_unknown_total", {})
            print(f"  Result: {result}")
    except TypeError:
        async with Client(mcp) as client:
            result = await client.call_tool("process_unknown_total", {})
            print(f"  Result: {result}")

    print("\n" + "=" * 60)
    print("EXPERIMENT 07 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
