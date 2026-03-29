"""
Spike: Can FastMCP's built-in ErrorHandlingMiddleware replace a custom middleware?

Approach:
    Use ErrorHandlingMiddleware (from fastmcp.server.middleware.error_handling)
    with transform_errors=True and a custom error_callback to handle Pydantic
    validation errors on write tools.

Questions:
    1. What error messages does the client see for validation failures?
       - Missing required field
       - Unknown field (extra="forbid")
       - Invalid type
    2. How do those compare to our clean _format_validation_errors() output?
    3. Can error_callback MODIFY the error, or is it read-only/fire-and-forget?
    4. Does on_message catch everything (including read tools), or can we scope
       it to write tools only?

Key findings from reading the source (error_handling.py):
    - _transform_error maps ValueError/TypeError -> McpError(-32602, "Invalid params: ...")
    - ValidationError is NOT in any mapping -> falls to else -> McpError(-32603, "Internal error: ...")
    - error_callback return value is IGNORED (fire-and-forget)
    - on_message wraps ALL methods, not just tools/call

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/3-approaches/05_error_handling_middleware.py
"""

import asyncio
import inspect
import json
from typing import Any

from fastmcp import Client, FastMCP
from fastmcp.server.middleware.error_handling import ErrorHandlingMiddleware
from pydantic import ValidationError

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

# ============================================================
# 1. Track what error_callback receives
# ============================================================

callback_log: list[dict[str, Any]] = []


def my_error_callback(error: Exception, context) -> str:
    """Custom error_callback. Returns a string to test if return value is used."""
    entry = {
        "error_type": type(error).__name__,
        "error_module": type(error).__module__,
        "method": context.method,
        "message_preview": str(error)[:200],
    }
    callback_log.append(entry)
    # Return something to test if the middleware uses our return value
    return "CALLBACK_SAYS_USE_THIS_MESSAGE_INSTEAD"


# ============================================================
# 2. Server with ErrorHandlingMiddleware
# ============================================================

mcp = FastMCP("error-handling-middleware-spike")
mcp.add_middleware(
    ErrorHandlingMiddleware(
        transform_errors=True,
        error_callback=my_error_callback,
        include_traceback=False,
    )
)


@mcp.tool()
async def add_task(command: AddTaskCommand) -> str:
    """Create a task (uses real AddTaskCommand model)."""
    return f"Created task: {command.name}"


@mcp.tool()
async def edit_task(command: EditTaskCommand) -> str:
    """Edit a task (uses real EditTaskCommand model)."""
    return f"Edited task: {command.id}"


@mcp.tool()
async def get_something(name: str) -> str:
    """A read tool -- should NOT have validation intercepted."""
    return f"Got: {name}"


# ============================================================
# 3. Reference: what _format_validation_errors would produce
# ============================================================

def format_reference(model: type, data: dict) -> str:
    """Show what our custom formatter would produce for the same input."""
    from omnifocus_operator.server import _format_validation_errors

    try:
        model.model_validate(data)
        return "(valid -- no error)"
    except ValidationError as exc:
        messages = _format_validation_errors(exc)
        return "; ".join(messages) if messages else "(all errors suppressed)"


# ============================================================
# 4. Test runner
# ============================================================

SEPARATOR = "=" * 70


async def call_and_compare(
    client: Client,
    label: str,
    tool_name: str,
    arguments: dict,
    model: type | None = None,
    model_data: dict | None = None,
) -> dict[str, Any]:
    """Call tool, capture client-side error, compare to reference formatter."""
    print(f"\n\n{'#' * 3} {label} {'#' * 3}")
    print(f"  Tool: {tool_name}")
    print(f"  Args: {json.dumps(arguments, indent=4, default=str)}")

    callback_before = len(callback_log)
    result_info: dict[str, Any] = {"label": label, "tool": tool_name}

    try:
        result = await client.call_tool(tool_name, arguments)
        print(f"  RESULT: {result}")
        result_info["outcome"] = "success"
        result_info["client_error"] = None
    except Exception as e:
        error_text = str(e)
        print(f"  CLIENT ERROR: {type(e).__name__}")
        print(f"    message: {error_text[:400]}")
        result_info["outcome"] = "error"
        result_info["client_error"] = error_text

    # Did our callback fire?
    new_callbacks = callback_log[callback_before:]
    if new_callbacks:
        cb = new_callbacks[-1]
        print(f"  CALLBACK fired: YES")
        print(f"    error_type: {cb['error_module']}.{cb['error_type']}")
        print(f"    method: {cb['method']}")
        result_info["callback_fired"] = True
        result_info["callback_error_type"] = f"{cb['error_module']}.{cb['error_type']}"
    else:
        print(f"  CALLBACK fired: NO")
        result_info["callback_fired"] = False

    # Reference comparison
    if model and model_data is not None:
        ref = format_reference(model, model_data)
        print(f"  REFERENCE (our formatter): {ref}")
        result_info["reference"] = ref

    return result_info


async def run_tests():
    print(SEPARATOR)
    print("SPIKE: ErrorHandlingMiddleware as validation handler")
    print(SEPARATOR)

    # --------------------------------------------------------
    # Part A: Verify error_callback source -- is return used?
    # --------------------------------------------------------
    print(f"\n{'=' * 50}")
    print("PART A: Inspect error_callback usage in source")
    print(f"{'=' * 50}")

    source = inspect.getsource(ErrorHandlingMiddleware._log_error)
    uses_return = "return" in source.split("self.error_callback")[1].split("\n")[0]
    print(f"  _log_error source around callback:")
    for line in source.split("\n"):
        if "error_callback" in line or "callback" in line:
            print(f"    {line.strip()}")
    print(f"  Callback return value used? {'YES' if uses_return else 'NO'}")
    print(f"  -> error_callback is fire-and-forget (read-only observation)")

    # --------------------------------------------------------
    # Part B: Check _transform_error mapping for ValidationError
    # --------------------------------------------------------
    print(f"\n{'=' * 50}")
    print("PART B: What does _transform_error do with ValidationError?")
    print(f"{'=' * 50}")

    source_transform = inspect.getsource(ErrorHandlingMiddleware._transform_error)
    print(f"  Mapped exception types:")
    for line in source_transform.split("\n"):
        stripped = line.strip()
        if stripped.startswith("if error_type in") or stripped.startswith("elif error_type"):
            print(f"    {stripped}")
    print(f"  ValidationError: NOT in any mapping -> falls to else branch")
    print(f"  -> McpError(-32603, 'Internal error: <raw pydantic error string>')")

    # --------------------------------------------------------
    # Part C: Scope check -- on_message catches everything
    # --------------------------------------------------------
    print(f"\n{'=' * 50}")
    print("PART C: What hook does ErrorHandlingMiddleware override?")
    print(f"{'=' * 50}")

    overridden = []
    for name in ["on_message", "on_call_tool", "on_request"]:
        method = getattr(ErrorHandlingMiddleware, name, None)
        if method and method is not getattr(ErrorHandlingMiddleware.__bases__[0], name, None):
            overridden.append(name)
    print(f"  Overridden hooks: {overridden}")
    print(f"  -> on_message wraps ALL methods (tools, resources, prompts, etc.)")
    print(f"  -> We can't scope to write tools only without subclassing")

    # --------------------------------------------------------
    # Part D: Actual tool calls
    # --------------------------------------------------------
    print(f"\n\n{'=' * 50}")
    print("PART D: Actual tool call tests")
    print(f"{'=' * 50}")

    results = []

    async with Client(mcp) as client:
        # Test 1: Valid input
        results.append(await call_and_compare(
            client,
            "TEST 1: Valid AddTaskCommand (should succeed)",
            "add_task",
            {"command": {"name": "Buy groceries"}},
            AddTaskCommand,
            {"name": "Buy groceries"},
        ))

        # Test 2: Missing required field
        results.append(await call_and_compare(
            client,
            "TEST 2: Missing required field (name)",
            "add_task",
            {"command": {"flagged": True}},
            AddTaskCommand,
            {"flagged": True},
        ))

        # Test 3: Unknown field (extra="forbid")
        results.append(await call_and_compare(
            client,
            "TEST 3: Unknown field (bogusField)",
            "add_task",
            {"command": {"name": "Buy groceries", "bogusField": "surprise!"}},
            AddTaskCommand,
            {"name": "Buy groceries", "bogusField": "surprise!"},
        ))

        # Test 4: Invalid type (flagged: "yes" instead of bool)
        results.append(await call_and_compare(
            client,
            "TEST 4: Invalid type (flagged: 'yes')",
            "add_task",
            {"command": {"name": "test", "flagged": "yes"}},
            AddTaskCommand,
            {"name": "test", "flagged": "yes"},
        ))

        # Test 5: Invalid discriminator (frequency type)
        results.append(await call_and_compare(
            client,
            "TEST 5: Invalid frequency discriminator",
            "add_task",
            {"command": {
                "name": "test",
                "repetitionRule": {
                    "frequency": {"type": "biweekly"},
                    "schedule": "regularly",
                    "basedOn": "due_date",
                },
            }},
            AddTaskCommand,
            {
                "name": "test",
                "repetitionRule": {
                    "frequency": {"type": "biweekly"},
                    "schedule": "regularly",
                    "basedOn": "due_date",
                },
            },
        ))

        # Test 6: EditTaskCommand -- invalid lifecycle
        results.append(await call_and_compare(
            client,
            "TEST 6: Invalid lifecycle value on EditTaskCommand",
            "edit_task",
            {"command": {"id": "abc123", "actions": {"lifecycle": "delete"}}},
            EditTaskCommand,
            {"id": "abc123", "actions": {"lifecycle": "delete"}},
        ))

        # Test 7: Read tool -- does ErrorHandlingMiddleware interfere?
        results.append(await call_and_compare(
            client,
            "TEST 7: Valid read tool (should pass through cleanly)",
            "get_something",
            {"name": "hello"},
        ))

        # Test 8: Read tool -- with bad input (missing required)
        results.append(await call_and_compare(
            client,
            "TEST 8: Read tool with missing arg (shows over-broad catch)",
            "get_something",
            {},
        ))

    # --------------------------------------------------------
    # Part E: Summary and verdict
    # --------------------------------------------------------
    print(f"\n\n{SEPARATOR}")
    print("PART E: SUMMARY & COMPARISON")
    print(SEPARATOR)

    print("\n--- Error callback stats ---")
    print(f"  Total callback invocations: {len(callback_log)}")
    for i, cb in enumerate(callback_log, 1):
        print(f"  {i}. method={cb['method']} type={cb['error_type']}")
        print(f"     preview: {cb['message_preview'][:120]}")

    print("\n--- Side-by-side: ErrorHandlingMiddleware vs our formatter ---")
    for r in results:
        if r["outcome"] == "error":
            print(f"\n  [{r['label']}]")
            client_err = r.get("client_error", "")
            ref = r.get("reference", "n/a")
            # Truncate for readability
            print(f"    ErrorHandlingMiddleware: {client_err[:200]}")
            print(f"    Our formatter:           {ref[:200]}")

    print(f"\n\n{SEPARATOR}")
    print("VERDICT")
    print(SEPARATOR)

    print("""
    ErrorHandlingMiddleware is NOT suitable as a replacement for custom middleware.

    1. RAW ERROR STRINGS: It passes str(error) directly into McpError messages.
       For Pydantic ValidationError, that's the full multi-line raw error dump
       with _Unset noise, unhelpful location paths, and no educational guidance.
       Our custom formatter rewrites these into clean, agent-friendly messages.

    2. WRONG ERROR CODE: ValidationError -> McpError(-32603, "Internal error: ...")
       This is misleading. Validation failures are client errors (-32602), not
       internal server errors. The middleware only maps ValueError/TypeError to
       -32602, and Pydantic's ValidationError is neither.

    3. error_callback IS READ-ONLY: The return value is ignored. The callback
       cannot modify, replace, or suppress errors. It's purely for logging and
       monitoring. To change the error, you'd need to subclass and override
       _transform_error -- at which point you've written a custom middleware anyway.

    4. OVER-BROAD SCOPE: on_message catches ALL methods (tools, resources, prompts).
       We only want to intercept validation errors on write tools (add_tasks,
       edit_tasks). Read tool errors should pass through normally. There's no
       built-in way to scope it.

    5. NO TOOL-NAME ACCESS: _transform_error receives (error, context) but the
       context at on_message level is the raw MCP message. You'd need to parse
       context.message to extract the tool name for tool-specific behavior.

    What we'd lose vs custom middleware:
       - Clean, educational error messages (UNKNOWN_FIELD, LIFECYCLE_INVALID_VALUE, etc.)
       - _Unset noise suppression
       - Write-tool-only scoping
       - Correct MCP error codes (-32602 for validation)
       - Tool-name-aware reformatting

    Bottom line: ErrorHandlingMiddleware is useful for generic error logging and
    monitoring, but it's not designed for domain-specific validation reformatting.
    A custom middleware (or subclass with on_call_tool) is the right approach.
    """)


if __name__ == "__main__":
    asyncio.run(run_tests())
