"""Experiment 09: Elicitation — "Are You Sure?" Prompts

QUESTION: Can ctx.elicit() add confirmation prompts for destructive ops?

CONTEXT:
  We have agent-facing warnings in tool responses, e.g.:
    "Warning: You are editing a completed task."

  Elicitation would make this INTERACTIVE:
    "You're about to edit a completed task — proceed?"

  The agent would need to confirm before the action executes.

WHAT TO LOOK FOR:
- Does ctx.elicit() work?
- What does the UX look like from the client side?
- Does the Client support elicitation handlers?
- What response types are supported? (yes/no, free text, structured?)
- Is this something Claude Desktop / Claude Code would actually use?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/09_elicitation.py
"""

from __future__ import annotations

import asyncio
from typing import Any

from fastmcp import FastMCP, Context, Client


mcp = FastMCP("elicitation-spike")


@mcp.tool()
async def edit_completed_task(task_id: str, ctx: Context) -> dict[str, Any]:
    """Simulates editing a completed task with confirmation."""
    try:
        result = await ctx.elicit(
            f"You're about to edit completed task '{task_id}'. Are you sure?",
        )
        print(f"  [SERVER] Elicitation result: {result}")
        print(f"  [SERVER] Result type: {type(result).__name__}")

        # Check the response
        if hasattr(result, "action"):
            if result.action == "accept":
                return {"status": "edited", "task_id": task_id, "confirmed": True}
            elif result.action == "decline":
                return {"status": "cancelled", "task_id": task_id, "confirmed": False}
            else:
                return {"status": "unknown_action", "action": result.action}
        else:
            return {"status": "no_action_attr", "raw": str(result)}

    except NotImplementedError as e:
        return {"status": "not_supported", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
async def delete_task(task_id: str, ctx: Context) -> dict[str, Any]:
    """Simulates deleting a task — should ALWAYS confirm."""
    try:
        result = await ctx.elicit(
            f"DESTRUCTIVE: Delete task '{task_id}'? This cannot be undone.",
        )
        if hasattr(result, "action") and result.action == "accept":
            return {"status": "deleted", "task_id": task_id}
        return {"status": "cancelled"}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


@mcp.tool()
async def structured_elicitation(ctx: Context) -> dict[str, Any]:
    """Test structured response types."""
    try:
        # Can we request a specific response type?
        result = await ctx.elicit(
            "Choose a priority level:",
            response_type=str,
        )
        return {"status": "got_response", "value": str(result)}
    except TypeError as e:
        return {"status": "response_type_not_supported", "error": str(e)}
    except Exception as e:
        return {"status": "error", "error": f"{type(e).__name__}: {e}"}


async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 09: Elicitation")
    print("=" * 60)

    # Test 1: Basic elicitation with auto-accept handler
    print("\n--- Test 1: Elicitation with auto-accept handler ---")
    elicitation_requests: list[dict[str, Any]] = []

    async def auto_accept_handler(message: str, **kwargs: Any) -> Any:
        """Auto-accepts all elicitation requests (for testing)."""
        elicitation_requests.append({"message": message, "kwargs": kwargs})
        print(f"  [CLIENT] Elicitation received: {message}")
        print(f"  [CLIENT] Auto-accepting...")
        # Return something that looks like acceptance
        # The exact format depends on the FastMCP API
        return {"action": "accept"}

    try:
        async with Client(mcp, elicitation_handler=auto_accept_handler) as client:
            result = await client.call_tool("edit_completed_task", {"task_id": "task-123"})
            print(f"  Result: {result}")
    except TypeError as e:
        print(f"  elicitation_handler not supported on Client: {e}")
        print("  Trying without handler...")
        async with Client(mcp) as client:
            result = await client.call_tool("edit_completed_task", {"task_id": "task-123"})
            print(f"  Result: {result}")

    # Test 2: Destructive operation
    print("\n--- Test 2: Destructive operation confirmation ---")
    try:
        async with Client(mcp, elicitation_handler=auto_accept_handler) as client:
            result = await client.call_tool("delete_task", {"task_id": "task-456"})
            print(f"  Result: {result}")
    except TypeError:
        async with Client(mcp) as client:
            result = await client.call_tool("delete_task", {"task_id": "task-456"})
            print(f"  Result: {result}")

    # Test 3: Structured elicitation
    print("\n--- Test 3: Structured response type ---")
    try:
        async with Client(mcp) as client:
            result = await client.call_tool("structured_elicitation", {})
            print(f"  Result: {result}")
    except Exception as e:
        print(f"  Error: {e}")

    # Summary
    print("\n" + "=" * 60)
    print("ELICITATION ASSESSMENT")
    print("=" * 60)
    print("""
  Questions to answer:
  1. Does elicitation work at all with the in-memory Client?
  2. Would Claude Desktop / Claude Code display these prompts?
  3. Is this better than our current "warning in response" approach?
  4. What happens when the client doesn't support elicitation?

  Our current approach (warning in response text):
    return {"status": "edited", "warning": "Task was already completed"}

  Elicitation approach (interactive confirmation):
    result = await ctx.elicit("Task is completed — proceed?")
    if result.action != "accept": return {"status": "cancelled"}

  Trade-off: Interactive is nicer UX but requires client support.
    """)
    print("EXPERIMENT 09 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
