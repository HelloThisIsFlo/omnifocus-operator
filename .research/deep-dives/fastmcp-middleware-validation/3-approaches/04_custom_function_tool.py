"""
Approach 4: Subclass FunctionTool, override run() to catch validation errors.

Bypasses middleware entirely. The custom tool class wraps the super().run()
call in try/except, catches ValidationError, and reformats it as a ToolError
using the project's existing _format_validation_errors().

Key questions:
    - Does from_function() work on the subclass? (It uses cls(...) so it should)
    - Does mcp.add_tool() accept arbitrary Tool subclasses?
    - Is this more or less coupling to FastMCP internals than middleware?
    - Does this compose with existing middleware (ToolLoggingMiddleware)?
    - How much FastMCP-internal knowledge is needed vs middleware approach?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/3-approaches/04_custom_function_tool.py
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from typing import Any

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.tools.function_tool import FunctionTool
from fastmcp.tools.tool import ToolResult
from pydantic import ValidationError

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand
from omnifocus_operator.server import _format_validation_errors

# ============================================================
# 1. ReformattingFunctionTool — subclass with validation interception
# ============================================================


class ReformattingFunctionTool(FunctionTool):
    """FunctionTool subclass that catches ValidationError in run() and
    reformats it as a ToolError with agent-friendly messages.

    Uses the project's existing _format_validation_errors() to produce
    clean error messages, bypassing the need for middleware.
    """

    async def run(self, arguments: dict[str, Any]) -> ToolResult:
        try:
            return await super().run(arguments)
        except ValidationError as exc:
            messages = _format_validation_errors(exc)
            raise ToolError("; ".join(messages) or "Invalid input") from None


# ============================================================
# 2. Server setup — register tools via add_tool()
# ============================================================

mcp = FastMCP("custom-function-tool-spike")


# --- Tool functions (plain functions, not decorated) ---

async def add_task(command: AddTaskCommand) -> str:
    """Create a task (uses real AddTaskCommand model)."""
    return f"Created task: {command.name}"


async def edit_task(command: EditTaskCommand) -> str:
    """Edit a task (uses real EditTaskCommand model)."""
    return f"Edited task: {command.id}"


# --- Registration ---

print("=" * 70)
print("STEP 1: Create ReformattingFunctionTool instances via from_function()")
print("=" * 70)

try:
    add_task_tool = ReformattingFunctionTool.from_function(
        add_task, name="add_task", description="Create a task"
    )
    print(f"  from_function() returned: {type(add_task_tool).__name__}")
    print(f"  Is ReformattingFunctionTool? {isinstance(add_task_tool, ReformattingFunctionTool)}")
    print(f"  Is FunctionTool? {isinstance(add_task_tool, FunctionTool)}")
    print(f"  Tool name: {add_task_tool.name}")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    raise

try:
    edit_task_tool = ReformattingFunctionTool.from_function(
        edit_task, name="edit_task", description="Edit a task"
    )
    print(f"  edit_task tool created: {type(edit_task_tool).__name__}")
except Exception as e:
    print(f"  FAILED: {type(e).__name__}: {e}")
    raise

print()
print("STEP 2: Register tools via mcp.add_tool()")

try:
    mcp.add_tool(add_task_tool)
    print(f"  mcp.add_tool(add_task_tool) succeeded")
except Exception as e:
    print(f"  mcp.add_tool(add_task_tool) FAILED: {type(e).__name__}: {e}")

try:
    mcp.add_tool(edit_task_tool)
    print(f"  mcp.add_tool(edit_task_tool) succeeded")
except Exception as e:
    print(f"  mcp.add_tool(edit_task_tool) FAILED: {type(e).__name__}: {e}")


# ============================================================
# 3. Also add ToolLoggingMiddleware to test composition
# ============================================================

import logging

logger = logging.getLogger("spike")
logging.basicConfig(level=logging.INFO, format="%(name)s: %(message)s")

middleware_calls: list[str] = []


class TrackingMiddleware(Middleware):
    """Simple middleware to verify it still fires with custom tool classes."""

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        tool_name = context.message.name
        middleware_calls.append(tool_name)
        logger.info(f"TrackingMiddleware: on_call_tool for '{tool_name}'")
        return await call_next(context)


mcp.add_middleware(TrackingMiddleware())


# ============================================================
# 4. Test cases
# ============================================================

SEPARATOR = "=" * 70
SUB_SEPARATOR = "-" * 50

results: list[dict[str, Any]] = []


async def call_and_report(
    client: Client,
    label: str,
    tool_name: str,
    arguments: dict[str, Any],
    expect_error: bool = False,
) -> None:
    """Call a tool, report results, and accumulate for summary."""
    print(f"\n{SUB_SEPARATOR}")
    print(f"TEST: {label}")
    print(f"  Tool: {tool_name}")
    print(f"  Args: {json.dumps(arguments, indent=4, default=str)}")

    entry: dict[str, Any] = {"label": label, "tool": tool_name, "expect_error": expect_error}

    try:
        result = await client.call_tool(tool_name, arguments)
        # Handle both old (list) and new (CallToolResult) return types
        if isinstance(result, list):
            text = result[0].text if result else "(empty)"
        elif hasattr(result, "content"):
            text = result.content[0].text if result.content else "(empty)"
        else:
            text = str(result)
        print(f"  RESULT: {text}")
        entry["outcome"] = "success"
        entry["text"] = text
    except Exception as e:
        error_text = str(e)
        print(f"  ERROR: {type(e).__name__}: {error_text[:300]}")
        entry["outcome"] = "error"
        entry["error_type"] = type(e).__name__
        entry["error_text"] = error_text

    entry["middleware_fired"] = tool_name in middleware_calls
    results.append(entry)


async def run_tests() -> None:
    print(f"\n\n{SEPARATOR}")
    print("STEP 3: Run tests through fastmcp.Client")
    print(SEPARATOR)

    async with Client(mcp) as client:

        # ---- Valid inputs ----

        await call_and_report(
            client,
            "Valid AddTaskCommand",
            "add_task",
            {"command": {"name": "Buy groceries"}},
            expect_error=False,
        )

        await call_and_report(
            client,
            "Valid EditTaskCommand",
            "edit_task",
            {"command": {"id": "abc123"}},
            expect_error=False,
        )

        # ---- Invalid inputs: should get reformatted errors ----

        await call_and_report(
            client,
            "AddTaskCommand: missing required field (name)",
            "add_task",
            {"command": {"flagged": True}},
            expect_error=True,
        )

        await call_and_report(
            client,
            "AddTaskCommand: unknown field (extra=forbid)",
            "add_task",
            {"command": {"name": "test", "bogusField": "surprise"}},
            expect_error=True,
        )

        await call_and_report(
            client,
            "AddTaskCommand: invalid frequency discriminator",
            "add_task",
            {
                "command": {
                    "name": "test",
                    "repetitionRule": {
                        "frequency": {"type": "biweekly"},
                        "schedule": "regularly",
                        "basedOn": "due_date",
                    },
                }
            },
            expect_error=True,
        )

        await call_and_report(
            client,
            "EditTaskCommand: invalid lifecycle literal",
            "edit_task",
            {"command": {"id": "abc", "actions": {"lifecycle": "delete"}}},
            expect_error=True,
        )

        await call_and_report(
            client,
            "EditTaskCommand: extra field at top level",
            "edit_task",
            {"command": {"id": "abc", "bogus": True}},
            expect_error=True,
        )

        await call_and_report(
            client,
            "AddTaskCommand: wrong type for bool (flagged='yes')",
            "add_task",
            {"command": {"name": "test", "flagged": "yes"}},
            expect_error=True,
        )

    # ============================================================
    # 5. Summary
    # ============================================================

    print(f"\n\n{SEPARATOR}")
    print("SUMMARY")
    print(SEPARATOR)

    print(f"\nTotal tests: {len(results)}")
    successes = [r for r in results if r["outcome"] == "success"]
    errors = [r for r in results if r["outcome"] == "error"]
    print(f"  Successes: {len(successes)}")
    print(f"  Errors:    {len(errors)}")

    print(f"\nMiddleware composition check:")
    print(f"  TrackingMiddleware fired for: {middleware_calls}")
    all_fired = all(r["middleware_fired"] for r in results)
    print(f"  All tools went through middleware: {all_fired}")

    print(f"\n{'Label':<55} {'Outcome':<10} {'Middleware'}")
    print("-" * 80)
    for r in results:
        mw_status = "yes" if r["middleware_fired"] else "NO"
        outcome = r["outcome"]
        if r["expect_error"] and outcome == "error":
            outcome = "error (expected)"
        elif not r["expect_error"] and outcome == "success":
            outcome = "ok"
        else:
            outcome = f"UNEXPECTED: {outcome}"
        print(f"  {r['label']:<53} {outcome:<20} {mw_status}")

    print(f"\nError messages received by client:")
    for r in errors:
        print(f"\n  [{r['label']}]")
        # Wrap long error text for readability
        wrapped = textwrap.fill(r["error_text"], width=70, initial_indent="    ", subsequent_indent="    ")
        print(wrapped)

    # ============================================================
    # 6. Analysis: coupling comparison
    # ============================================================

    print(f"\n\n{SEPARATOR}")
    print("ANALYSIS: Coupling & Internals Knowledge")
    print(SEPARATOR)

    print("""
    from_function() works on subclass?
      -> Check above: "Is ReformattingFunctionTool?" should be True
      -> from_function() uses cls(...) at line 234 of function_tool.py

    mcp.add_tool() accepts Tool subclasses?
      -> Check above: add_tool succeeded
      -> add_tool checks isinstance(tool, Tool), our subclass passes

    Coupling to FastMCP internals:
      MIDDLEWARE APPROACH:
        - Middleware, MiddlewareContext (public API)
        - on_call_tool / call_next pattern (public API)
        - Knows: ValidationError flows through call_next()
        - Coupling: LOW — uses documented middleware protocol

      CUSTOM TOOL SUBCLASS APPROACH:
        - FunctionTool.from_function() (semi-internal)
        - FunctionTool.run() signature and behavior (semi-internal)
        - mcp.add_tool() (public API)
        - Knows: run() is where validation happens
        - Knows: from_function uses cls() so subclassing works
        - Coupling: MEDIUM — relies on FunctionTool internals

    Composition with middleware:
      -> Middleware fires AROUND the tool, tool.run() is INSIDE call_next()
      -> So ToolLoggingMiddleware sees the ToolError (already reformatted)
      -> This is GOOD: middleware sees clean errors, not raw ValidationError

    Comparison:
      Middleware:        Apply once, covers ALL tools automatically
      Custom tool class: Must register each tool manually (no @mcp.tool decorator)
      Middleware:        More aligned with FastMCP's extension model
      Custom tool class: More explicit, no global interception
      Middleware:        Error reformatting runs outside the tool boundary
      Custom tool class: Error reformatting runs inside the tool boundary
    """)


if __name__ == "__main__":
    asyncio.run(run_tests())
