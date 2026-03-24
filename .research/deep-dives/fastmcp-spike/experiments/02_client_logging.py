"""Experiment 02: Client Logging — What Does the Client See?

QUESTION: How does ctx.info() / ctx.warning() / ctx.error() work?
What does the client actually see? This is THE main reason for migrating.

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/02_client_logging.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio to the running server

  Option B — Claude Code:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 02
    2. Restart Claude Code (or reload MCP servers)
    3. Ask Claude to call the tools below
    4. When done: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py remove

GUIDED WALKTHROUGH:
  1. Call `log_all_levels` — look at the client output.
     - Did all 4 levels appear? (debug, info, warning, error)
     - Where did they render? Inline? In a log panel? Stderr?
     - Was debug filtered out?

  2. Call `log_with_structure` — check if structured data appears.
     - Does the client show the extra fields?
     - Or just the message string?

  3. Call `log_rapid_fire` — 10 messages in quick succession.
     - Do all 10 arrive? In order?
     - Any visible delay?

  4. Call `log_in_real_scenario` — simulates what our real tools would do.
     - This mimics get_all / add_tasks logging patterns.
     - Does this feel useful from the agent's perspective?
"""

from __future__ import annotations

from fastmcp import FastMCP, Context

mcp = FastMCP("logging-spike")


@mcp.tool()
async def log_all_levels(ctx: Context) -> str:
    """Emits one message at each log level."""
    await ctx.debug("DEBUG: Detailed diagnostic info — usually hidden from clients")
    await ctx.info("INFO: Starting tool execution")
    await ctx.warning("WARNING: Something might need attention")
    await ctx.error("ERROR: Something went wrong (but we recovered)")
    return "Logged at all 4 levels. Check what appeared on your end."


@mcp.tool()
async def log_with_structure(ctx: Context) -> str:
    """Logs with structured extra data — does the client see it?"""
    await ctx.info("Processing batch of 5 tasks")
    await ctx.info("Resolved tag 'Work' to tag ID tkAbc123")
    await ctx.warning("Task 'oRx3bL' is already completed — editing anyway")
    return "Logged 3 messages with real-world content. Check your client."


@mcp.tool()
async def log_rapid_fire(ctx: Context) -> str:
    """Sends 10 messages quickly — do they all arrive? In order?"""
    for i in range(1, 11):
        await ctx.info(f"Message {i} of 10")
    return "Sent 10 messages. Did they all arrive? In order?"


@mcp.tool()
async def log_in_real_scenario(ctx: Context) -> dict[str, str]:
    """Simulates realistic logging from our actual tools.

    This is what add_tasks or edit_tasks would log during execution.
    """
    await ctx.info("add_tasks: Processing 3 items")
    await ctx.info("Item 1: Resolving parent 'pJKx9xL5beb'...")
    await ctx.info("Item 1: Resolving tags ['Work', 'Planning']...")
    await ctx.warning("Item 2: Tag 'Urgnt' not found — did you mean 'Urgent'?")
    await ctx.info("Item 3: Created in inbox (no parent specified)")
    await ctx.info("add_tasks: 3/3 items processed successfully")
    return {
        "status": "success",
        "created": "3",
        "message": "Check client logs — this simulates real add_tasks logging",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
