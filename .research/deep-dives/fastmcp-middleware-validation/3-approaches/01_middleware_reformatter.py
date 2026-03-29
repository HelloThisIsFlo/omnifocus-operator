"""
Approach 1: Middleware catches ValidationError, reformats, re-raises as ToolError.

PRIMARY candidate. The idea: tool handlers accept typed Pydantic params directly
(no try/except, no manual model_validate). FastMCP validates the params inside
call_next(). Middleware wraps call_next() in try/except, catches ValidationError,
runs it through _format_validation_errors(), and raises ToolError with the
agent-friendly message.

Key questions:
    - Does the middleware path produce the same agent-facing errors as today?
    - Is the ToolError surfaced correctly to the client?
    - Any edge cases or surprises?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/3-approaches/01_middleware_reformatter.py
"""

from __future__ import annotations

import asyncio
import json
import textwrap
from typing import Any

import pydantic
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand
from omnifocus_operator.server import _format_validation_errors

# ============================================================
# 1. ValidationReformatterMiddleware
# ============================================================


class ValidationReformatterMiddleware(Middleware):
    """Catch Pydantic ValidationError from typed params, reformat, re-raise as ToolError.

    FastMCP validates typed tool parameters inside FunctionTool.run(),
    which is inside call_next(). This middleware wraps call_next() to
    intercept validation failures and produce agent-friendly messages
    using the project's existing _format_validation_errors().
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        try:
            return await call_next(context)
        except pydantic.ValidationError as exc:
            messages = _format_validation_errors(exc)
            agent_msg = "; ".join(messages) or "Invalid input"
            raise ToolError(agent_msg) from exc
        except Exception as exc:
            # Also check for pydantic_core's ValidationError variant
            # (pydantic.ValidationError inherits from it, but just in case
            # FastMCP wraps or re-raises differently)
            exc_type_name = type(exc).__qualname__
            exc_module = type(exc).__module__ or ""
            if "ValidationError" in exc_type_name and "pydantic" in exc_module:
                # Attempt to format if it quacks like a Pydantic ValidationError
                try:
                    messages = _format_validation_errors(exc)  # type: ignore[arg-type]
                    agent_msg = "; ".join(messages) or "Invalid input"
                    raise ToolError(agent_msg) from exc
                except ToolError:
                    raise
                except Exception:
                    pass  # Fall through to re-raise original
            raise


# ============================================================
# 2. Server with SIMPLE typed tool handlers
# ============================================================

mcp = FastMCP("middleware-reformatter-spike")
mcp.add_middleware(ValidationReformatterMiddleware())


@mcp.tool()
async def add_task(command: AddTaskCommand) -> str:
    """Create a task. Accepts typed AddTaskCommand -- all validation is Pydantic + middleware."""
    return f"OK: created task '{command.name}'"


@mcp.tool()
async def edit_task(command: EditTaskCommand) -> str:
    """Edit a task. Accepts typed EditTaskCommand -- all validation is Pydantic + middleware."""
    return f"OK: edited task '{command.id}'"


# ============================================================
# 3. Test infrastructure
# ============================================================

# Collect results for final summary
test_results: list[dict[str, Any]] = []


async def call_and_report(
    client: Client,
    label: str,
    tool_name: str,
    arguments: dict[str, Any],
    *,
    expect_success: bool,
    current_handler_note: str,
) -> None:
    """Call a tool, print structured results, compare with current handler behavior."""
    separator = "-" * 70
    print(f"\n{separator}")
    print(f"  {label}")
    print(separator)
    print(f"  Tool:  {tool_name}")
    print(f"  Input: {json.dumps(arguments, indent=4, default=str)}")
    print()

    outcome: dict[str, Any] = {
        "label": label,
        "expected": "success" if expect_success else "error",
    }

    try:
        result = await client.call_tool(tool_name, arguments)
        print(f"  RESULT: {result}")
        outcome["actual"] = "success"
        outcome["message"] = str(result)
        outcome["match"] = expect_success
    except ToolError as e:
        msg = str(e)
        print(f"  ToolError: {msg}")
        outcome["actual"] = "ToolError"
        outcome["message"] = msg
        outcome["match"] = not expect_success
    except Exception as e:
        msg = f"{type(e).__name__}: {e}"
        print(f"  UNEXPECTED: {msg}")
        outcome["actual"] = "unexpected"
        outcome["message"] = msg
        outcome["match"] = False

    print()
    print(f"  Expected: {'success' if expect_success else 'error (ToolError)'}")
    print(f"  Actual:   {outcome['actual']}")
    print(f"  Match:    {'YES' if outcome['match'] else 'NO'}")
    print()
    print(f"  Current handler comparison:")
    for line in textwrap.wrap(current_handler_note, width=64):
        print(f"    {line}")

    test_results.append(outcome)


# ============================================================
# 4. Test scenarios
# ============================================================


async def run_tests() -> None:
    print("=" * 70)
    print("  APPROACH 1: ValidationReformatterMiddleware")
    print("  Middleware catches ValidationError, reformats, re-raises as ToolError")
    print("=" * 70)

    async with Client(mcp) as client:

        # --- Test 1: Valid add ---
        await call_and_report(
            client,
            "TEST 1: Valid add_task (happy path)",
            "add_task",
            {"command": {"name": "Buy groceries"}},
            expect_success=True,
            current_handler_note=(
                "Current handler: model_validate succeeds, service.add_task() "
                "runs. Middleware approach should produce the same 'OK' result."
            ),
        )

        # --- Test 2: Missing required 'name' on add ---
        await call_and_report(
            client,
            "TEST 2: add_task missing required 'name' field",
            "add_task",
            {"command": {"flagged": True}},
            expect_success=False,
            current_handler_note=(
                "Current handler: ValidationError caught, _format_validation_errors "
                "returns 'Field required'. Middleware should produce the same message."
            ),
        )

        # --- Test 3: Unknown field on add ---
        await call_and_report(
            client,
            "TEST 3: add_task with unknown field 'bogusField'",
            "add_task",
            {"command": {"name": "Buy groceries", "bogusField": "surprise!"}},
            expect_success=False,
            current_handler_note=(
                "Current handler: extra='forbid' triggers 'Unknown field "
                "'bogusField''. Middleware should produce the same "
                "UNKNOWN_FIELD message."
            ),
        )

        # --- Test 4: Valid edit with just 'id' ---
        await call_and_report(
            client,
            "TEST 4: Valid edit_task with just 'id' (no-op edit)",
            "edit_task",
            {"command": {"id": "abc123"}},
            expect_success=True,
            current_handler_note=(
                "Current handler: model_validate succeeds (all optional "
                "fields default to UNSET). Middleware should pass through."
            ),
        )

        # --- Test 5: Invalid lifecycle value ---
        await call_and_report(
            client,
            "TEST 5: edit_task with invalid lifecycle value 'delete'",
            "edit_task",
            {
                "command": {
                    "id": "abc123",
                    "actions": {"lifecycle": "delete"},
                }
            },
            expect_success=False,
            current_handler_note=(
                "Current handler: literal_error for lifecycle, "
                "_format_validation_errors returns \"Invalid lifecycle action "
                "'delete' -- must be 'complete' or 'drop'\". Middleware should "
                "produce the same message."
            ),
        )

        # --- Test 6: Invalid frequency type ---
        await call_and_report(
            client,
            "TEST 6: edit_task with invalid frequency type 'biweekly'",
            "edit_task",
            {
                "command": {
                    "id": "abc123",
                    "repetitionRule": {
                        "frequency": {"type": "biweekly"},
                    },
                }
            },
            expect_success=False,
            current_handler_note=(
                "Current handler: union_tag_invalid on frequency, "
                "_format_validation_errors returns \"Invalid frequency type "
                "'biweekly' -- valid types: ...\". Middleware should produce "
                "the same message."
            ),
        )

        # --- Test 7: Invalid datetime format on dueDate ---
        await call_and_report(
            client,
            "TEST 7: add_task with invalid datetime format on dueDate",
            "add_task",
            {
                "command": {
                    "name": "Deadline task",
                    "dueDate": "next-tuesday",
                }
            },
            expect_success=False,
            current_handler_note=(
                "Current handler: Pydantic datetime parsing fails, "
                "_format_validation_errors returns the raw Pydantic message "
                "(no special rewriting for date errors). Middleware should "
                "produce the same raw message."
            ),
        )

    # ============================================================
    # 5. Summary
    # ============================================================
    print("\n\n" + "=" * 70)
    print("  SUMMARY")
    print("=" * 70)

    passed = sum(1 for r in test_results if r["match"])
    total = len(test_results)
    print(f"\n  {passed}/{total} tests matched expectations\n")

    for i, r in enumerate(test_results, 1):
        status = "PASS" if r["match"] else "FAIL"
        print(f"  {i}. [{status}] {r['label']}")
        print(f"     Expected: {r['expected']}, Got: {r['actual']}")
        msg_preview = r["message"][:120]
        print(f"     Message:  {msg_preview}")
        print()

    # Key findings
    print("=" * 70)
    print("  KEY FINDINGS")
    print("=" * 70)

    all_passed = passed == total
    error_tests = [r for r in test_results if r["expected"] == "error"]
    all_errors_are_tool_errors = all(r["actual"] == "ToolError" for r in error_tests)

    print()
    if all_passed:
        print("  [OK] All test expectations met")
    else:
        print("  [!!] Some tests did NOT match expectations -- investigate")

    if all_errors_are_tool_errors:
        print("  [OK] All validation errors surfaced as ToolError to client")
    else:
        non_tool = [r for r in error_tests if r["actual"] != "ToolError"]
        print(f"  [!!] {len(non_tool)} error(s) NOT surfaced as ToolError:")
        for r in non_tool:
            print(f"       - {r['label']}: {r['actual']}")

    print()
    print("  Questions answered:")
    print("    1. Does middleware produce same agent-facing errors as today?")
    print(f"       -> {'YES (qualitatively)' if all_passed else 'PARTIALLY -- see failures above'}")
    print("    2. Is ToolError surfaced correctly to the client?")
    print(f"       -> {'YES' if all_errors_are_tool_errors else 'NO -- see above'}")
    print("    3. Any edge cases or surprises?")
    print("       -> Check individual test output above for unexpected messages")
    print()


if __name__ == "__main__":
    asyncio.run(run_tests())
