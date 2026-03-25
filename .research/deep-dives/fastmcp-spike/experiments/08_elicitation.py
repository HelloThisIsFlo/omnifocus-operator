"""Experiment 08: Elicitation — Interactive User Prompts During Tool Execution

QUESTION: Can ctx.elicit() add interactive prompts for user input mid-tool?
What response types are supported? How does it look in Claude Code?

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/08_elicitation.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio

  Option B — Claude Code:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 08
    2. Restart Claude Code
    3. Call the tools

GUIDED WALKTHROUGH:
  One tool per response type. Call each and observe what the client renders.

  1. `confirm_action` — None response (just accept/decline/cancel)
  2. `ask_string` — free text input
  3. `ask_number` — integer input
  4. `ask_boolean` — true/false toggle
  5. `ask_choice` — constrained options (pick one)
  6. `ask_multi_select` — pick multiple from a list
  7. `ask_structured` — dataclass with multiple fields
  8. `ask_with_defaults` — pre-populated fields
  9. `multi_turn` — progressive disclosure (multiple prompts in sequence)
  10. `fallback_demo` — what we do today (warning in response, no prompt)
"""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Any, Literal

from fastmcp import FastMCP, Context
from pydantic import BaseModel, Field


mcp = FastMCP("elicitation-spike")


# ── 1. Confirmation (None response) ─────────────────────────────────

@mcp.tool()
async def confirm_action(task_id: str, ctx: Context) -> dict[str, Any]:
    """Pure confirmation — no data, just accept/decline/cancel."""
    result = await ctx.elicit(
        f"Task '{task_id}' is already completed. Edit it anyway?",
        response_type=None,
    )

    match result.action:
        case "accept":
            return {"status": "edited", "task_id": task_id}
        case "decline":
            return {"status": "declined"}
        case _:
            return {"status": "cancelled"}


# ── 2. String input ─────────────────────────────────────────────────

@mcp.tool()
async def ask_string(ctx: Context) -> dict[str, Any]:
    """Ask for free text input."""
    result = await ctx.elicit("What should the task be called?", response_type=str)

    if result.action == "accept":
        return {"name": result.data}
    return {"status": result.action}


# ── 3. Integer input ────────────────────────────────────────────────

@mcp.tool()
async def ask_number(ctx: Context) -> dict[str, Any]:
    """Ask for a number."""
    result = await ctx.elicit("How many minutes to estimate?", response_type=int)

    if result.action == "accept":
        return {"estimated_minutes": result.data}
    return {"status": result.action}


# ── 4. Boolean input ────────────────────────────────────────────────

@mcp.tool()
async def ask_boolean(ctx: Context) -> dict[str, Any]:
    """Ask for true/false."""
    result = await ctx.elicit("Should this task be flagged?", response_type=bool)

    if result.action == "accept":
        return {"flagged": result.data}
    return {"status": result.action}


# ── 5. Constrained choice (pick one) ────────────────────────────────

@mcp.tool()
async def ask_choice(ctx: Context) -> dict[str, Any]:
    """Pick one from a list of options."""
    result = await ctx.elicit(
        "What priority level?",
        response_type=["low", "medium", "high", "critical"],
    )

    if result.action == "accept":
        return {"priority": result.data}
    return {"status": result.action}


# ── 6. Multi-select ─────────────────────────────────────────────────

@mcp.tool()
async def ask_multi_select(ctx: Context) -> dict[str, Any]:
    """Pick multiple from a list of options."""
    result = await ctx.elicit(
        "Which tags should be applied?",
        response_type=[["Work", "Personal", "Urgent", "Waiting", "Someday"]],
    )

    if result.action == "accept":
        return {"tags": result.data}
    return {"status": result.action}


# ── 7. Structured response (dataclass) ──────────────────────────────

@dataclass
class TaskDetails:
    name: str
    project: str
    priority: Literal["low", "medium", "high"]
    flagged: bool


@mcp.tool()
async def ask_structured(ctx: Context) -> dict[str, Any]:
    """Ask for multiple fields at once via a structured form."""
    result = await ctx.elicit(
        "Please provide task details",
        response_type=TaskDetails,
    )

    if result.action == "accept":
        task = result.data
        return {
            "name": task.name,
            "project": task.project,
            "priority": task.priority,
            "flagged": task.flagged,
        }
    return {"status": result.action}


# ── 8. Defaults (Pydantic model with pre-populated fields) ──────────

class Priority(Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"


class TaskWithDefaults(BaseModel):
    name: str = Field(description="Task name")
    note: str = Field(default="", description="Optional note")
    priority: Priority = Field(default=Priority.MEDIUM, description="Priority level")
    flagged: bool = Field(default=False, description="Flag this task?")


@mcp.tool()
async def ask_with_defaults(ctx: Context) -> dict[str, Any]:
    """Structured form with pre-populated default values."""
    result = await ctx.elicit(
        "Create a new task (defaults pre-filled)",
        response_type=TaskWithDefaults,
    )

    if result.action == "accept":
        task = result.data
        return {
            "name": task.name,
            "note": task.note,
            "priority": task.priority.value,
            "flagged": task.flagged,
        }
    return {"status": result.action}


# ── 9. Multi-turn (progressive disclosure) ──────────────────────────

@mcp.tool()
async def multi_turn(ctx: Context) -> dict[str, Any]:
    """Gather information step by step across multiple prompts."""
    name_result = await ctx.elicit("What's the task name?", response_type=str)
    if name_result.action != "accept":
        return {"status": "cancelled at step 1"}

    priority_result = await ctx.elicit(
        f"Priority for '{name_result.data}'?",
        response_type=["low", "medium", "high"],
    )
    if priority_result.action != "accept":
        return {"status": "cancelled at step 2", "name": name_result.data}

    confirm_result = await ctx.elicit(
        f"Create '{name_result.data}' with priority {priority_result.data}?",
        response_type=None,
    )
    if confirm_result.action != "accept":
        return {"status": "cancelled at step 3"}

    return {
        "status": "created",
        "name": name_result.data,
        "priority": priority_result.data,
    }


# ── 10. Fallback (our current pattern — no elicitation) ─────────────

@mcp.tool()
async def fallback_demo(task_id: str) -> dict[str, Any]:
    """What we do today: warning in the response, no interactive prompt."""
    return {
        "status": "edited",
        "task_id": task_id,
        "warning": f"Task '{task_id}' was already completed. "
                   "The edit was applied, but please confirm with the user.",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
