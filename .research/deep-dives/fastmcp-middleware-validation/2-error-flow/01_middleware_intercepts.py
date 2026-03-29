"""
Spike: Can middleware catch validation errors from REAL typed parameters?

Question:
    The toy-model spike (middleware_validation_spike.py) proved middleware can
    intercept Pydantic validation errors via call_next(). Does this hold when
    using the actual project models (AddTaskCommand, EditTaskCommand) with their
    camelCase aliases, extra="forbid", UNSET sentinels, and discriminated unions?

What to look for:
    - Every invalid test case should show "MIDDLEWARE: CAUGHT ..." output
    - Exception types should be pydantic ValidationError (or pydantic_core)
    - The middleware should be able to wrap each error as a ToolError
    - Valid cases should pass through cleanly

Key insight from FastMCP source:
    In FunctionTool.run(), validation happens via type_adapter.validate_python(arguments)
    INSIDE the tool execution, which is INSIDE call_next(). So middleware SHOULD catch it.

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/2-error-flow/01_middleware_intercepts.py
"""

import asyncio
import json
import traceback

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

# ============================================================
# 1. Middleware: catch ALL exceptions from call_next()
# ============================================================

caught_errors: list[dict] = []


class ErrorInterceptMiddleware(Middleware):
    """Catches all exceptions from call_next() and logs details."""

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        args = context.message.arguments

        print(f"\n{'=' * 70}")
        print(f"MIDDLEWARE: on_call_tool for '{tool_name}'")
        print(f"MIDDLEWARE: arguments = {json.dumps(args, indent=2, default=str)}")

        try:
            result = await call_next(context)
            print("MIDDLEWARE: call_next() succeeded")
            return result
        except Exception as exc:
            error_type = type(exc).__name__
            error_module = type(exc).__module__
            error_msg = str(exc)

            print(f"MIDDLEWARE: CAUGHT {error_module}.{error_type}")
            print(f"MIDDLEWARE: message = {error_msg[:500]}")

            is_reformattable = True
            try:
                raise ToolError(f"[REFORMATTED] {error_msg[:200]}") from exc
            except ToolError:
                pass
            except Exception:
                is_reformattable = False

            caught_errors.append(
                {
                    "type": error_type,
                    "module": error_module,
                    "message": error_msg,
                    "reformattable": is_reformattable,
                }
            )

            # Re-raise as ToolError so the client gets a structured error
            raise ToolError(f"[REFORMATTED] {error_msg[:300]}") from exc


# ============================================================
# 2. Server with real-model tools
# ============================================================

mcp = FastMCP("real-model-spike")
mcp.add_middleware(ErrorInterceptMiddleware())


@mcp.tool()
async def add_task(command: AddTaskCommand) -> str:
    """Create a task (uses real AddTaskCommand model)."""
    return f"Created task: {command.name}"


@mcp.tool()
async def edit_task(command: EditTaskCommand) -> str:
    """Edit a task (uses real EditTaskCommand model)."""
    return f"Edited task: {command.id}"


# ============================================================
# 3. Test cases
# ============================================================


async def call_and_report(
    client: Client,
    label: str,
    tool_name: str,
    arguments: dict,
) -> None:
    """Call a tool and print structured results."""
    print(f"\n\n### {label} ###")
    print(f"  Tool: {tool_name}")
    print(f"  Sent: {json.dumps(arguments, indent=4, default=str)}")

    try:
        result = await client.call_tool(tool_name, arguments)
        print(f"  RESULT: {result}")
        print(f"  Middleware caught exception: NO")
    except Exception as e:
        print(f"  CLIENT EXCEPTION: {type(e).__name__}: {str(e)[:300]}")
        # Check if the most recent caught_error corresponds to this call
        if caught_errors:
            last = caught_errors[-1]
            print(f"  Middleware caught exception: YES")
            print(f"    Exception type: {last['module']}.{last['type']}")
            print(f"    Reformattable as ToolError: {last['reformattable']}")
        else:
            print(f"  Middleware caught exception: NO (error happened outside middleware)")


async def run_tests():
    print("=" * 70)
    print("SPIKE: Middleware interception with REAL project models")
    print("       (AddTaskCommand, EditTaskCommand)")
    print("=" * 70)

    async with Client(mcp) as client:

        # --------------------------------------------------
        # Test 1: Valid AddTaskCommand
        # --------------------------------------------------
        await call_and_report(
            client,
            "TEST 1: Valid AddTaskCommand (should succeed)",
            "add_task",
            {
                "command": {
                    "name": "Buy groceries",
                }
            },
        )

        # --------------------------------------------------
        # Test 2: AddTaskCommand missing required 'name' field
        # --------------------------------------------------
        await call_and_report(
            client,
            "TEST 2: AddTaskCommand missing required 'name' field",
            "add_task",
            {
                "command": {
                    "flagged": True,
                }
            },
        )

        # --------------------------------------------------
        # Test 3: AddTaskCommand with unknown field (extra="forbid")
        # --------------------------------------------------
        await call_and_report(
            client,
            "TEST 3: AddTaskCommand with unknown field 'bogusField'",
            "add_task",
            {
                "command": {
                    "name": "Buy groceries",
                    "bogusField": "surprise!",
                }
            },
        )

        # --------------------------------------------------
        # Test 4: Valid EditTaskCommand with just 'id'
        # --------------------------------------------------
        await call_and_report(
            client,
            "TEST 4: Valid EditTaskCommand with just 'id' (should succeed)",
            "edit_task",
            {
                "command": {
                    "id": "abc123",
                }
            },
        )

        # --------------------------------------------------
        # Test 5: EditTaskCommand with invalid lifecycle value
        # --------------------------------------------------
        await call_and_report(
            client,
            "TEST 5: EditTaskCommand with invalid lifecycle value",
            "edit_task",
            {
                "command": {
                    "id": "abc123",
                    "actions": {
                        "lifecycle": "delete",  # invalid: must be "complete" or "drop"
                    },
                }
            },
        )

        # --------------------------------------------------
        # Test 6: EditTaskCommand with bad frequency type in repetition rule
        # --------------------------------------------------
        await call_and_report(
            client,
            "TEST 6: EditTaskCommand with bad frequency type in repetition rule",
            "edit_task",
            {
                "command": {
                    "id": "abc123",
                    "repetitionRule": {
                        "frequency": {
                            "type": "biweekly",  # invalid discriminator value
                        },
                    },
                }
            },
        )

    # --------------------------------------------------
    # Summary
    # --------------------------------------------------
    print("\n\n" + "=" * 70)
    print("SUMMARY")
    print("=" * 70)

    error_count = len(caught_errors)
    if error_count:
        print(f"\nMiddleware caught {error_count} error(s):")
        for i, err in enumerate(caught_errors, 1):
            print(f"  {i}. [{err['module']}.{err['type']}]")
            print(f"     Reformattable as ToolError: {err['reformattable']}")
            print(f"     Message (first 150 chars): {err['message'][:150]}")
            print()

        # Verdict
        all_reformattable = all(e["reformattable"] for e in caught_errors)
        print("VERDICT: Middleware CAN intercept validation errors from real project models")
        if all_reformattable:
            print("         ALL errors are reformattable as ToolError")
        else:
            print("         WARNING: Some errors could NOT be reformatted as ToolError")
    else:
        print("\nMiddleware caught 0 errors")
        print("VERDICT: Validation happens BEFORE middleware -- approach not viable")


if __name__ == "__main__":
    asyncio.run(run_tests())
