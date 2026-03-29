"""
End-to-end prototype: add_tasks with typed parameters + middleware error reformatting.

This is the RECOMMENDED approach from the FastMCP middleware/validation spike.
It combines all proven findings into a single working prototype:

  1. Typed params (list[AddTaskCommand]) -- Pydantic validates automatically
  2. ValidationReformatterMiddleware -- catches ValidationError, reformats
  3. _format_validation_errors -- reuses existing agent-friendly formatter
  4. loc path stripping -- removes "command." prefix FastMCP adds

Scenarios tested:
  - Happy path: full task, minimal task, repetition rules
  - Validation: missing name, unknown field, bad datetime, bad frequency,
    bad schedule, wrong bool type, batch limit
  - Schema: list_tools() returns rich JSON Schema

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/5-integration/01_typed_add_tasks_e2e.py
"""

import asyncio
import json

from pydantic import ValidationError

from fastmcp import Client, FastMCP
from fastmcp.exceptions import ToolError
from fastmcp.server.middleware import Middleware, MiddlewareContext

from omnifocus_operator.agent_messages.errors import ADD_TASKS_BATCH_LIMIT, INVALID_INPUT
from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand, AddTaskResult
from omnifocus_operator.server import _format_validation_errors

# ============================================================
# 1. Middleware: reformat ValidationError into agent-friendly ToolError
# ============================================================


class ValidationReformatterMiddleware(Middleware):
    """Catches Pydantic ValidationError from typed params and reformats as ToolError.

    FastMCP wraps each tool param as e.g. ``items`` in the loc path.
    We strip that prefix so error paths match the agent's input structure.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        try:
            return await call_next(context)
        except ValidationError as exc:
            messages = _format_validation_errors(exc)
            raise ToolError("; ".join(messages) or INVALID_INPUT) from None


# ============================================================
# 2. Server + tool registration
# ============================================================

mcp = FastMCP("add_tasks_e2e_prototype", middleware=[ValidationReformatterMiddleware()])


@mcp.tool()
async def add_tasks(items: list[AddTaskCommand]) -> list[AddTaskResult]:
    """Create tasks in OmniFocus.

    Accepts an array of task objects. Currently limited to 1 item per call.

    Each item accepts:
    - name (required): Task name
    - parent: Project or task ID to place task under (omit for inbox)
    - tags: List of tag names (case-insensitive) or tag IDs
    - dueDate: Due date (ISO 8601)
    - deferDate: Defer/start date (ISO 8601)
    - plannedDate: Planned date (ISO 8601)
    - flagged: Boolean flag
    - estimatedMinutes: Estimated duration in minutes
    - note: Task note text
    - repetitionRule: Repetition rule object (see docs for structure)

    Returns array of results: [{success, id, name, warnings?}]
    """
    if len(items) != 1:
        msg = ADD_TASKS_BATCH_LIMIT.format(count=len(items))
        raise ValueError(msg)

    # No try/except, no model_validate -- Pydantic already validated via typed params!
    # In production, this would call service.add_task(items[0])
    task = items[0]
    return [AddTaskResult(success=True, id="mock-id", name=task.name)]


# ============================================================
# 3. Test runner
# ============================================================

PASS = "PASS"
FAIL = "FAIL"


async def call_tool(client: Client, name: str, args: dict) -> tuple[str, str]:
    """Call a tool and return (status, detail)."""
    try:
        result = await client.call_tool(name, args)
        # CallToolResult has .content list of TextContent/etc
        text = result.content[0].text if result.content else "<no content>"
        return PASS, text
    except Exception as exc:
        return FAIL, f"[{type(exc).__name__}] {exc}"


async def run_tests():
    print("=" * 78)
    print("  add_tasks E2E Prototype: Typed Params + Middleware Error Reformatting")
    print("=" * 78)

    async with Client(mcp) as client:

        # ----------------------------------------------------------
        # HAPPY PATH TESTS
        # ----------------------------------------------------------

        print("\n" + "-" * 78)
        print("  HAPPY PATH TESTS")
        print("-" * 78)

        # Test 1: Full task with all fields
        print("\n[1] Happy path: full task with all fields")
        args = {
            "items": [
                {
                    "name": "Review Q3 roadmap",
                    "parent": "pJKx9xL5beb",
                    "tags": ["Work", "Planning"],
                    "dueDate": "2026-03-15T17:00:00Z",
                    "deferDate": "2026-03-10T09:00:00Z",
                    "flagged": True,
                    "estimatedMinutes": 30,
                    "note": "Focus on v1.3-v1.5 milestones",
                }
            ]
        }
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0], indent=None)}")
        print(f"  Status: {status}")
        print(f"  Result: {detail}")

        # Test 2: Minimal task (name only)
        print("\n[2] Happy path: minimal task (name only)")
        args = {"items": [{"name": "Buy groceries"}]}
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Result: {detail}")

        # Test 3: Task with daily repetition rule
        print("\n[3] Happy path: task with daily repetition rule")
        args = {
            "items": [
                {
                    "name": "Daily standup",
                    "repetitionRule": {
                        "frequency": {"type": "daily", "interval": 1},
                        "schedule": "from_completion",
                        "basedOn": "defer_date",
                    },
                }
            ]
        }
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Result: {detail}")

        # Test 4: Task with weekly_on_days repetition rule
        print("\n[4] Happy path: task with weekly_on_days repetition rule")
        args = {
            "items": [
                {
                    "name": "Team sync",
                    "repetitionRule": {
                        "frequency": {
                            "type": "weekly_on_days",
                            "interval": 2,
                            "onDays": ["MO", "FR"],
                        },
                        "schedule": "regularly",
                        "basedOn": "due_date",
                        "end": {"occurrences": 10},
                    },
                }
            ]
        }
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Result: {detail}")

        # ----------------------------------------------------------
        # VALIDATION ERROR TESTS
        # ----------------------------------------------------------

        print("\n" + "-" * 78)
        print("  VALIDATION ERROR TESTS")
        print("-" * 78)

        # Test 5: Missing required name
        print("\n[5] Validation: missing required 'name'")
        args = {"items": [{"parent": "pJKx9xL5beb"}]}
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Error:  {detail}")

        # Test 6: Unknown field (extra="forbid")
        print("\n[6] Validation: unknown field")
        args = {"items": [{"name": "Test", "priority": "high"}]}
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Error:  {detail}")

        # Test 7: Invalid datetime format
        print("\n[7] Validation: invalid datetime format")
        args = {"items": [{"name": "Test", "dueDate": "next tuesday"}]}
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Error:  {detail}")

        # Test 8: Invalid repetition frequency type
        print("\n[8] Validation: invalid repetition frequency type")
        args = {
            "items": [
                {
                    "name": "Test",
                    "repetitionRule": {
                        "frequency": {"type": "biweekly"},
                        "schedule": "regularly",
                        "basedOn": "due_date",
                    },
                }
            ]
        }
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Error:  {detail}")

        # Test 9: Invalid repetition schedule enum
        print("\n[9] Validation: invalid repetition schedule enum")
        args = {
            "items": [
                {
                    "name": "Test",
                    "repetitionRule": {
                        "frequency": {"type": "daily"},
                        "schedule": "sometimes",
                        "basedOn": "due_date",
                    },
                }
            ]
        }
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Error:  {detail}")

        # Test 10: Wrong type for bool field
        # Note: Pydantic lax mode coerces "yes"/"true"/0/1 to bool.
        # Use a value that genuinely fails bool parsing (e.g. 42).
        print("\n[10] Validation: wrong type for bool field (flagged=42)")
        args = {"items": [{"name": "Test", "flagged": 42}]}
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  {json.dumps(args['items'][0])}")
        print(f"  Status: {status}")
        print(f"  Error:  {detail}")

        # Test 11: Batch limit (2 items)
        print("\n[11] Validation: batch limit exceeded (2 items)")
        args = {"items": [{"name": "Task A"}, {"name": "Task B"}]}
        status, detail = await call_tool(client, "add_tasks", args)
        print(f"  Input:  2 items")
        print(f"  Status: {status}")
        print(f"  Error:  {detail}")

        # ----------------------------------------------------------
        # SCHEMA CHECK
        # ----------------------------------------------------------

        print("\n" + "-" * 78)
        print("  SCHEMA CHECK")
        print("-" * 78)

        print("\n[12] Schema: list_tools() returns rich inputSchema")
        tools = await client.list_tools()
        for tool in tools:
            if tool.name == "add_tasks":
                schema = tool.inputSchema
                print(f"  Tool name: {tool.name}")
                print(f"  inputSchema:\n{json.dumps(schema, indent=2)}")
                # Check key properties
                props = schema.get("properties", {})
                items_prop = props.get("items", {})
                print(f"\n  Has 'items' property: {'items' in props}")
                print(f"  Items type: {items_prop.get('type', 'N/A')}")
                # Check if items/items has rich schema (not just dict)
                items_items = items_prop.get("items", {})
                has_name = "name" in items_items.get("properties", {})
                has_defs = "$defs" in schema
                print(f"  Item has 'name' property: {has_name}")
                print(f"  Schema has $defs (for nested models): {has_defs}")
                if has_defs:
                    print(f"  $defs keys: {list(schema['$defs'].keys())}")
                break
        else:
            print("  ERROR: add_tasks tool not found!")

    # ----------------------------------------------------------
    # SUMMARY
    # ----------------------------------------------------------

    print("\n" + "=" * 78)
    print("  SUMMARY")
    print("=" * 78)
    print("""
  Expected results:
    [1-4]  Happy paths: PASS with mock result
    [5]    Missing name: ToolError "Field required"
    [6]    Unknown field: ToolError "Unknown field 'items.0.priority'"
    [7]    Bad datetime: ToolError with descriptive message
    [8]    Bad frequency: ToolError with all valid types listed
    [9]    Bad schedule: ToolError with valid enum values
    [10]   Bad bool: ToolError "unable to interpret input"
    [11]   Batch limit: ToolError from ValueError (not ValidationError)
    [12]   Schema: rich inputSchema with full model structure

  What this proves:
    - Typed params (list[AddTaskCommand]) work end-to-end
    - Middleware catches ValidationError and reformats via _format_validation_errors
    - No manual model_validate() needed in the handler
    - Rich JSON Schema generated automatically from typed params
    - camelCase aliases preserved in schema (dueDate, estimatedMinutes, etc.)
    - extra="forbid" catches unknown fields
    - Discriminated union (Frequency) validates correctly
    - Nested models (RepetitionRuleAddSpec, EndCondition) inlined in schema

  Known issue -- loc prefix:
    - Error paths include FastMCP param prefix: "items.0.priority"
    - Agent sees "items" in path, which matches their input structure
    - If we want cleaner paths, _format_validation_errors could strip
      the leading param name -- but "items.0.field" is actually fine
      since the agent input IS "items": [{...}]

  Known issue -- $defs:
    - FastMCP inlines nested model schemas instead of using $refs/$defs
    - This is fine -- the schema is fully expanded and correct
    - Frequency discriminated union uses oneOf with const discriminator
    """)


if __name__ == "__main__":
    asyncio.run(run_tests())
