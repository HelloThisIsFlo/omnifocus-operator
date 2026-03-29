"""
Spike: Can FastMCP middleware intercept validation errors from typed parameters?

Key questions this answers:
1. Does validation happen INSIDE call_next() (middleware can catch it)?
   Or BEFORE middleware runs (middleware never sees it)?
2. If middleware catches it, what exception type do we get?
3. Can we reformat errors and return a ToolError instead?
4. Does the typed parameter generate a rich inputSchema in tools/list?

Run:
    pip install fastmcp --break-system-packages
    python spike_middleware_validation.py
"""

import asyncio
import json
from enum import Enum
from typing import Literal

from pydantic import BaseModel, Field
from fastmcp import FastMCP, Client
from fastmcp.server.middleware import Middleware, MiddlewareContext
from fastmcp.exceptions import ToolError


# ============================================================
# 1. Define a Pydantic model similar to your domain
# ============================================================


class Schedule(str, Enum):
    regularly = "regularly"
    regularly_with_catch_up = "regularly_with_catch_up"
    from_completion = "from_completion"


class WeeklyOnDays(BaseModel):
    type: Literal["weekly_on_days"]
    interval: int = Field(default=1, ge=1)
    onDays: list[str] = Field(
        ..., description="Two-letter day codes: MO, TU, WE, TH, FR, SA, SU"
    )


class Daily(BaseModel):
    type: Literal["daily"]
    interval: int = Field(default=1, ge=1)


# Simplified discriminated union
Frequency = WeeklyOnDays | Daily


class TaskCommand(BaseModel):
    """A simplified task command to test schema generation and error handling."""

    model_config = {"extra": "forbid"}

    name: str = Field(..., description="Task name")
    schedule: Schedule = Field(..., description="Repetition schedule type")
    frequency: Frequency = Field(
        ..., description="Frequency details", discriminator="type"
    )


# ============================================================
# 2. Middleware that tries to catch validation errors
# ============================================================

caught_errors = []


class ErrorInterceptMiddleware(Middleware):
    """Test whether middleware can intercept validation errors."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        print(f"\n{'='*60}")
        print(f"MIDDLEWARE: on_call_tool fired for '{context.message.name}'")
        print(
            f"MIDDLEWARE: arguments = {json.dumps(context.message.arguments, indent=2)}"
        )

        try:
            result = await call_next(context)
            print("MIDDLEWARE: call_next() succeeded")
            return result
        except Exception as exc:
            error_type = type(exc).__name__
            error_module = type(exc).__module__
            print(f"MIDDLEWARE: CAUGHT {error_module}.{error_type}")
            print(f"MIDDLEWARE: message = {exc}")
            caught_errors.append(
                {
                    "type": error_type,
                    "module": error_module,
                    "message": str(exc),
                }
            )

            # Try to reformat and raise as ToolError
            raise ToolError(f"[REFORMATTED] {exc}") from exc


# ============================================================
# 3. Set up server with typed tool + middleware
# ============================================================

mcp = FastMCP("spike")
mcp.add_middleware(ErrorInterceptMiddleware())


@mcp.tool()
async def create_task(command: TaskCommand) -> str:
    """Create a task with repetition rule."""
    return f"Created task: {command.name}"


# Also register a dict-based tool for comparison
@mcp.tool()
async def create_task_untyped(items: list[dict]) -> str:
    """Create a task (untyped)."""
    return f"Got: {items}"


# ============================================================
# 4. Test harness
# ============================================================


async def run_tests():
    print("=" * 60)
    print("SPIKE: FastMCP Middleware Validation Interception")
    print("=" * 60)

    async with Client(mcp) as client:

        # -------------------------------------------
        # Test A: Check inputSchema from tools/list
        # -------------------------------------------
        print("\n\n### TEST A: inputSchema comparison ###\n")
        tools = await client.list_tools()
        for tool in tools:
            print(f"Tool: {tool.name}")
            print(f"  inputSchema: {json.dumps(tool.inputSchema, indent=4)}")
            print()

        # -------------------------------------------
        # Test B: Valid call to typed tool
        # -------------------------------------------
        print("\n### TEST B: Valid call (should succeed) ###")
        try:
            result = await client.call_tool(
                "create_task",
                {
                    "command": {
                        "name": "Buy milk",
                        "schedule": "regularly",
                        "frequency": {"type": "daily", "interval": 2},
                    }
                },
            )
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  ERROR: {type(e).__name__}: {e}")

        # -------------------------------------------
        # Test C: Invalid enum value
        # -------------------------------------------
        print("\n### TEST C: Invalid enum value (bad schedule) ###")
        try:
            result = await client.call_tool(
                "create_task",
                {
                    "command": {
                        "name": "Buy milk",
                        "schedule": "never",
                        "frequency": {"type": "daily"},
                    }
                },
            )
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  CAUGHT BY CLIENT: {type(e).__name__}: {e}")

        # -------------------------------------------
        # Test D: Unknown field (extra="forbid")
        # -------------------------------------------
        print("\n### TEST D: Unknown field ###")
        try:
            result = await client.call_tool(
                "create_task",
                {
                    "command": {
                        "name": "Buy milk",
                        "schedule": "regularly",
                        "frequency": {"type": "daily"},
                        "bogusField": True,
                    }
                },
            )
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  CAUGHT BY CLIENT: {type(e).__name__}: {e}")

        # -------------------------------------------
        # Test E: Missing required field
        # -------------------------------------------
        print("\n### TEST E: Missing required field ###")
        try:
            result = await client.call_tool(
                "create_task",
                {
                    "command": {
                        "name": "Buy milk"
                        # missing schedule and frequency
                    }
                },
            )
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  CAUGHT BY CLIENT: {type(e).__name__}: {e}")

        # -------------------------------------------
        # Test F: Bad discriminator value
        # -------------------------------------------
        print("\n### TEST F: Bad frequency type (discriminator) ###")
        try:
            result = await client.call_tool(
                "create_task",
                {
                    "command": {
                        "name": "Buy milk",
                        "schedule": "regularly",
                        "frequency": {"type": "biweekly"},
                    }
                },
            )
            print(f"  Result: {result}")
        except Exception as e:
            print(f"  CAUGHT BY CLIENT: {type(e).__name__}: {e}")

    # -------------------------------------------
    # Summary
    # -------------------------------------------
    print("\n\n" + "=" * 60)
    print("SUMMARY")
    print("=" * 60)
    caught = caught_errors
    if caught:
        print(f"\nMiddleware caught {len(caught)} error(s):")
        for i, err in enumerate(caught, 1):
            print(f"  {i}. [{err['module']}.{err['type']}] {err['message'][:120]}")
        print("\n✅ MIDDLEWARE CAN INTERCEPT VALIDATION ERRORS")
        print("   -> Path 1 (typed params + middleware error formatting) is viable")
    else:
        print("\n❌ Middleware caught 0 errors")
        print("   -> Validation happens BEFORE middleware")
        print("   -> Need Path 2 (schema override) or Path 3 (model-level errors)")


if __name__ == "__main__":
    asyncio.run(run_tests())
