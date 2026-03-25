"""Experiment 08: Elicitation — "Are You Sure?" Prompts

QUESTION: Can ctx.elicit() add confirmation prompts for destructive operations?
Does the client actually show the prompt? What happens when you decline?

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/08_elicitation.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio

  Option B — Claude Code:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 08
    2. Restart Claude Code (or reload MCP servers)
    3. Ask Claude to call the tools
    4. When done: uv run python .../setup_mcp.py remove

GUIDED WALKTHROUGH:
  1. Call `edit_completed_task` with {"task_id": "task-123"}
     - Did you see a confirmation prompt?
     - What did it look like?
     - Accept it — what's the result?

  2. Call `edit_completed_task` again — this time DECLINE.
     - What happens? Does the tool get a decline signal?
     - Or does it error out?

  3. Call `delete_task` with {"task_id": "task-456"}
     - Different warning message. Same mechanism.

  4. Call `no_elicitation_fallback` — this is what we do TODAY.
     - Compare the UX: warning-in-response vs interactive prompt.
     - Which is better for agents?
"""

from __future__ import annotations

from typing import Any

from fastmcp import FastMCP, Context


mcp = FastMCP("elicitation-spike")


@mcp.tool()
async def edit_completed_task(task_id: str, ctx: Context) -> dict[str, Any]:
    """Simulates editing a completed task — asks for confirmation first."""
    try:
        result = await ctx.elicit(
            f"Task '{task_id}' is already completed. Edit it anyway?",
        )

        if hasattr(result, "action"):
            if result.action == "accept":
                return {"status": "edited", "task_id": task_id, "confirmed": True}
            elif result.action == "decline":
                return {"status": "cancelled", "task_id": task_id, "confirmed": False}
            else:
                return {"status": "unknown_action", "action": str(result.action)}
        else:
            return {"status": "no_action_attr", "raw": str(result), "type": type(result).__name__}

    except NotImplementedError:
        return {"status": "not_supported", "fallback": "Client doesn't support elicitation"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
async def delete_task(task_id: str, ctx: Context) -> dict[str, Any]:
    """Simulates deleting a task — ALWAYS asks for confirmation."""
    try:
        result = await ctx.elicit(
            f"DESTRUCTIVE: Delete task '{task_id}'? This cannot be undone.",
        )
        if hasattr(result, "action") and result.action == "accept":
            return {"status": "deleted", "task_id": task_id}
        return {"status": "cancelled", "task_id": task_id}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
async def no_elicitation_fallback(task_id: str) -> dict[str, Any]:
    """What we do TODAY: warning in the response (no interactive prompt).

    Compare this UX with the elicitation approach above.
    """
    return {
        "status": "edited",
        "task_id": task_id,
        "warning": f"Task '{task_id}' was already completed. "
                   "The edit was applied, but you may want to verify the result.",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
