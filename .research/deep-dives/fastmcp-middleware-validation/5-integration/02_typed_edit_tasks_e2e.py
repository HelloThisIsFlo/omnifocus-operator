"""Full end-to-end prototype: edit_tasks with typed parameters + middleware error reformatting.

EditTaskCommand is the HARD case because of UNSET/Patch/PatchOrClear semantics.
This script validates that:
    - Three-way semantics work correctly (omitted = UNSET, null = clear, value = set)
    - Middleware catches all validation errors and reformats them
    - UNSET noise is filtered from error messages
    - Happy paths work for all field types including actions and repetition rules
    - Batch limit enforcement works from inside the handler

Research findings confirmed here:
    - UNSET excluded from JSON schema (all paths)
    - UNSET noise in validation errors: 19 of 49 errors are `is_instance_of` with `_Unset` (must filter)
    - Patch[str] -> {"type": "string"} in schema (clean)
    - PatchOrClear[str] -> {"anyOf": [string, null]} in schema (clean)
    - Only `id` is required in schema (correct)
    - Middleware catches all validation errors (confirmed)

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/5-integration/02_typed_edit_tasks_e2e.py
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import pydantic
from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from omnifocus_operator.agent_messages.errors import EDIT_TASKS_BATCH_LIMIT
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand, EditTaskResult
from omnifocus_operator.server import _format_validation_errors

# ============================================================
# 1. ValidationReformatterMiddleware (same as approach 01)
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
            exc_type_name = type(exc).__qualname__
            exc_module = type(exc).__module__ or ""
            if "ValidationError" in exc_type_name and "pydantic" in exc_module:
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
# 2. Server with typed edit_tasks handler
# ============================================================

mcp = FastMCP("edit-tasks-e2e-spike")
mcp.add_middleware(ValidationReformatterMiddleware())


@mcp.tool()
async def edit_tasks(items: list[EditTaskCommand]) -> list[EditTaskResult]:
    """Edit existing tasks using patch semantics. Typed params -- Pydantic validates."""
    if len(items) != 1:
        raise ValueError(EDIT_TASKS_BATCH_LIMIT.format(count=len(items)))
    command = items[0]
    # Handler is simple -- validation already done by Pydantic
    return [EditTaskResult(success=True, id=command.id, name="mock-name")]


# ============================================================
# 3. Test infrastructure
# ============================================================

test_results: list[dict[str, Any]] = []

SEPARATOR = "-" * 72
SECTION = "=" * 72


async def call_and_report(
    client: Client,
    label: str,
    arguments: dict[str, Any],
    *,
    expect_success: bool,
) -> None:
    """Call edit_tasks, print structured results."""
    print(f"\n{SEPARATOR}")
    print(f"  {label}")
    print(SEPARATOR)
    print(f"  Input: {json.dumps(arguments, indent=4, default=str)}")
    print()

    outcome: dict[str, Any] = {
        "label": label,
        "expected": "success" if expect_success else "error",
    }

    try:
        result = await client.call_tool("edit_tasks", arguments)
        text = str(result)
        # Truncate long results
        if len(text) > 300:
            text = text[:300] + "..."
        print(f"  RESULT: {text}")
        outcome["actual"] = "success"
        outcome["message"] = text
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

    test_results.append(outcome)


# ============================================================
# 4. Three-way semantics verification
# ============================================================


async def verify_three_way_semantics() -> None:
    """KEY QUESTION: does the three-way semantics work correctly?

    - {"id": "x"} -> all fields UNSET (no changes)
    - {"id": "x", "dueDate": null} -> dueDate is None (clear it)
    - {"id": "x", "dueDate": "2026-01-01T00:00:00Z"} -> dueDate is set
    """
    print(f"\n\n{SECTION}")
    print("  THREE-WAY SEMANTICS VERIFICATION")
    print(f"{SECTION}")

    from omnifocus_operator.contracts.base import UNSET, is_set

    cases = [
        ("Omitted (UNSET)", {"id": "x"}),
        ("Null (clear)", {"id": "x", "dueDate": None}),
        ("Value (set)", {"id": "x", "dueDate": "2026-01-01T00:00:00Z"}),
    ]

    for label, data in cases:
        cmd = EditTaskCommand.model_validate(data)
        due = cmd.due_date
        print(f"\n  {label}:")
        print(f"    Input:        {json.dumps(data, default=str)}")
        print(f"    due_date:     {due!r}")
        print(f"    is_set():     {is_set(due)}")
        print(f"    is None:      {due is None}")
        print(f"    is UNSET:     {due is UNSET}")

    # Also verify a Patch[str] field (name -- cannot be null)
    print(f"\n  Patch[str] (name -- non-clearable):")
    cmd_no_name = EditTaskCommand.model_validate({"id": "x"})
    cmd_with_name = EditTaskCommand.model_validate({"id": "x", "name": "updated"})
    print(f"    Omitted:  name={cmd_no_name.name!r}, is_set={is_set(cmd_no_name.name)}")
    print(f"    Set:      name={cmd_with_name.name!r}, is_set={is_set(cmd_with_name.name)}")


# ============================================================
# 5. Test scenarios
# ============================================================


async def run_tests() -> None:
    print(SECTION)
    print("  EDIT_TASKS END-TO-END: Typed params + middleware error reformatting")
    print(SECTION)

    # ----- Three-way semantics first -----
    await verify_three_way_semantics()

    # ----- Schema inspection -----
    print(f"\n\n{SECTION}")
    print("  INPUT SCHEMA")
    print(SECTION)

    async with Client(mcp) as client:
        tools = await client.list_tools()
        for tool in tools:
            if tool.name == "edit_tasks":
                schema = tool.inputSchema
                print(f"\n{json.dumps(schema, indent=2)}")
                break

    # ----- Tool call tests -----
    print(f"\n\n{SECTION}")
    print("  HAPPY PATH TESTS")
    print(SECTION)

    async with Client(mcp) as client:

        # Happy 1: Minimal edit (just id)
        await call_and_report(
            client,
            "HAPPY 1: Minimal edit (just id -- no changes)",
            {"items": [{"id": "task-001"}]},
            expect_success=True,
        )

        # Happy 2: Edit with name + note + flagged
        await call_and_report(
            client,
            "HAPPY 2: Edit with name + note + flagged",
            {"items": [{"id": "task-001", "name": "Updated name", "note": "New note", "flagged": True}]},
            expect_success=True,
        )

        # Happy 3: Clear a field (dueDate: null)
        await call_and_report(
            client,
            "HAPPY 3: Clear a field (dueDate: null)",
            {"items": [{"id": "task-001", "dueDate": None}]},
            expect_success=True,
        )

        # Happy 4: Edit with actions.lifecycle: "complete"
        await call_and_report(
            client,
            "HAPPY 4: Lifecycle action (complete)",
            {"items": [{"id": "task-001", "actions": {"lifecycle": "complete"}}]},
            expect_success=True,
        )

        # Happy 5: Tag operations (add + remove)
        await call_and_report(
            client,
            "HAPPY 5: Tag operations (add + remove)",
            {"items": [{"id": "task-001", "actions": {"tags": {"add": ["tag1"], "remove": ["tag2"]}}}]},
            expect_success=True,
        )

        # Happy 6: Move action (ending)
        await call_and_report(
            client,
            "HAPPY 6: Move action (ending: parent-id)",
            {"items": [{"id": "task-001", "actions": {"move": {"ending": "parent-id"}}}]},
            expect_success=True,
        )

        # Happy 7: Repetition rule update
        await call_and_report(
            client,
            "HAPPY 7: Repetition rule update (weekly, interval 2)",
            {"items": [{
                "id": "task-001",
                "repetitionRule": {
                    "frequency": {"type": "weekly", "interval": 2},
                    "schedule": "regularly",
                    "basedOn": "due_date",
                },
            }]},
            expect_success=True,
        )

        # ----- Validation error tests -----
        print(f"\n\n{SECTION}")
        print("  VALIDATION ERROR TESTS")
        print(SECTION)

        # Error 1: Missing required id
        await call_and_report(
            client,
            "ERROR 1: Missing required id",
            {"items": [{"name": "No id provided"}]},
            expect_success=False,
        )

        # Error 2: Invalid lifecycle value
        await call_and_report(
            client,
            "ERROR 2: Invalid lifecycle value 'delete'",
            {"items": [{"id": "task-001", "actions": {"lifecycle": "delete"}}]},
            expect_success=False,
        )

        # Error 3: Invalid frequency type
        await call_and_report(
            client,
            "ERROR 3: Invalid frequency type 'biweekly'",
            {"items": [{
                "id": "task-001",
                "repetitionRule": {"frequency": {"type": "biweekly"}},
            }]},
            expect_success=False,
        )

        # Error 4: Unknown field
        await call_and_report(
            client,
            "ERROR 4: Unknown field 'bogusField'",
            {"items": [{"id": "task-001", "bogusField": "surprise!"}]},
            expect_success=False,
        )

        # Error 5: Invalid tag action (replace + add together)
        await call_and_report(
            client,
            "ERROR 5: Invalid tag action (replace + add together)",
            {"items": [{"id": "task-001", "actions": {"tags": {"replace": ["tag1"], "add": ["tag2"]}}}]},
            expect_success=False,
        )

        # Error 6: Invalid move action (multiple keys)
        await call_and_report(
            client,
            "ERROR 6: Invalid move action (beginning + ending together)",
            {"items": [{"id": "task-001", "actions": {"move": {"beginning": "p1", "ending": "p2"}}}]},
            expect_success=False,
        )

        # Error 7: Bad datetime format
        await call_and_report(
            client,
            "ERROR 7: Bad datetime format on dueDate",
            {"items": [{"id": "task-001", "dueDate": "next-tuesday"}]},
            expect_success=False,
        )

        # Error 8: Batch limit (2 items)
        await call_and_report(
            client,
            "ERROR 8: Batch limit exceeded (2 items)",
            {"items": [{"id": "task-001"}, {"id": "task-002"}]},
            expect_success=False,
        )

    # ============================================================
    # 6. Summary
    # ============================================================
    print(f"\n\n{SECTION}")
    print("  SUMMARY")
    print(SECTION)

    passed = sum(1 for r in test_results if r["match"])
    total = len(test_results)
    print(f"\n  {passed}/{total} tests matched expectations\n")

    for i, r in enumerate(test_results, 1):
        status = "PASS" if r["match"] else "FAIL"
        print(f"  {i}. [{status}] {r['label']}")
        print(f"     Expected: {r['expected']}, Got: {r['actual']}")
        msg_preview = r["message"][:160]
        print(f"     Message:  {msg_preview}")
        print()

    # ============================================================
    # 7. Key findings
    # ============================================================
    print(SECTION)
    print("  KEY FINDINGS")
    print(SECTION)

    all_passed = passed == total
    error_tests = [r for r in test_results if r["expected"] == "error"]
    all_errors_are_tool_errors = all(r["actual"] == "ToolError" for r in error_tests)
    happy_tests = [r for r in test_results if r["expected"] == "success"]
    all_happy_success = all(r["actual"] == "success" for r in happy_tests)

    print()
    if all_passed:
        print("  [OK] All test expectations met")
    else:
        fails = [r for r in test_results if not r["match"]]
        print(f"  [!!] {len(fails)} test(s) did NOT match expectations:")
        for r in fails:
            print(f"       - {r['label']}: expected {r['expected']}, got {r['actual']}")

    if all_errors_are_tool_errors:
        print("  [OK] All validation errors surfaced as ToolError (agent-friendly)")
    else:
        non_tool = [r for r in error_tests if r["actual"] != "ToolError"]
        print(f"  [!!] {len(non_tool)} error(s) NOT surfaced as ToolError:")
        for r in non_tool:
            print(f"       - {r['label']}: {r['actual']}")

    if all_happy_success:
        print("  [OK] All happy paths passed through handler successfully")
    else:
        fails = [r for r in happy_tests if r["actual"] != "success"]
        print(f"  [!!] {len(fails)} happy path(s) failed:")
        for r in fails:
            print(f"       - {r['label']}: {r['actual']} -- {r['message'][:120]}")

    # Check for UNSET noise in error messages
    unset_in_errors = [r for r in error_tests if "_Unset" in r.get("message", "") or "Unset" in r.get("message", "")]
    print()
    if unset_in_errors:
        print(f"  [!!] UNSET noise found in {len(unset_in_errors)} error message(s):")
        for r in unset_in_errors:
            print(f"       - {r['label']}")
    else:
        print("  [OK] No UNSET noise in any error message (filter working)")

    print()
    print("  Three-way semantics: see verification section above")
    print("  Schema: see inputSchema section above")
    print()


if __name__ == "__main__":
    asyncio.run(run_tests())
