"""
Approach 3: model_validator(mode='wrap') on Command models.

Idea:
    Add a @model_validator(mode="wrap") to AddTaskCommand/EditTaskCommand that
    catches ValidationError from the inner validation pass and reformats it,
    potentially eliminating the need for server-level error handling.

    We subclass to avoid modifying production models -- tests the concept
    without side effects.

Key questions:
    1. Does the model_validator catch errors from field-level validation?
    2. Does the ValidationError inside model_validator have the same structure
       as the one we catch in server.py today?
    3. Is the reformatted ValueError surfaced to the client?
    4. Does this affect JSON schema generation? (model_validator shouldn't change schema)
    5. What about errors in nested models (RepetitionRule, TagAction)?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python .research/deep-dives/fastmcp-middleware-validation/3-approaches/03_model_validator_wrap.py
"""

from __future__ import annotations

import asyncio
import json
import traceback

from fastmcp import Client, FastMCP
from pydantic import ValidationError, model_validator

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand
from omnifocus_operator.server import _format_validation_errors

# ============================================================
# 1. Subclasses with model_validator(mode="wrap")
# ============================================================


class AddTaskCommandWithReformat(AddTaskCommand):
    """AddTaskCommand that reformats validation errors at the model level."""

    @model_validator(mode="wrap")
    @classmethod
    def reformat_errors(cls, data, handler):
        try:
            return handler(data)
        except ValidationError as exc:
            messages = _format_validation_errors(exc)
            raise ValueError("; ".join(messages) or "Invalid input") from None


class EditTaskCommandWithReformat(EditTaskCommand):
    """EditTaskCommand that reformats validation errors at the model level."""

    @model_validator(mode="wrap")
    @classmethod
    def reformat_errors(cls, data, handler):
        try:
            return handler(data)
        except ValidationError as exc:
            messages = _format_validation_errors(exc)
            raise ValueError("; ".join(messages) or "Invalid input") from None


# ============================================================
# 2. FastMCP server with subclassed models as typed params
# ============================================================

mcp = FastMCP("model-validator-wrap-spike")


@mcp.tool()
async def add_task(command: AddTaskCommandWithReformat) -> str:
    """Create a task (uses subclassed AddTaskCommand with wrap validator)."""
    return f"Created task: {command.name}"


@mcp.tool()
async def edit_task(command: EditTaskCommandWithReformat) -> str:
    """Edit a task (uses subclassed EditTaskCommand with wrap validator)."""
    return f"Edited task: {command.id}"


# ============================================================
# 3. Helper: call tool and report
# ============================================================


async def call_and_report(
    client: Client,
    label: str,
    tool_name: str,
    arguments: dict,
) -> dict:
    """Call a tool and print structured results. Returns result dict."""
    print(f"\n\n{'=' * 70}")
    print(f"### {label} ###")
    print(f"  Tool: {tool_name}")
    print(f"  Sent: {json.dumps(arguments, indent=4, default=str)}")

    result_info = {"label": label, "success": False, "error": None, "result": None}

    try:
        result = await client.call_tool(tool_name, arguments)
        # result is a CallToolResult; content items are in .content
        content = result.content if hasattr(result, "content") else result
        if isinstance(content, list):
            text_parts = [c.text for c in content if hasattr(c, "text")]
        else:
            text_parts = [str(content)]
        result_text = " | ".join(text_parts)
        print(f"  RESULT: {result_text}")
        result_info["success"] = True
        result_info["result"] = result_text
    except Exception as e:
        error_text = str(e)
        print(f"  CLIENT EXCEPTION: {type(e).__name__}: {error_text[:500]}")
        result_info["error"] = error_text

    return result_info


# ============================================================
# 4. Schema comparison
# ============================================================


def compare_schemas():
    """Check if subclassing + model_validator(mode='wrap') changes the JSON schema."""
    print("\n" + "=" * 70)
    print("SCHEMA COMPARISON")
    print("=" * 70)

    add_orig = AddTaskCommand.model_json_schema()
    add_wrap = AddTaskCommandWithReformat.model_json_schema()

    edit_orig = EditTaskCommand.model_json_schema()
    edit_wrap = EditTaskCommandWithReformat.model_json_schema()

    add_match = add_orig == add_wrap
    edit_match = edit_orig == edit_wrap

    print(f"\n  AddTaskCommand schema matches subclass:  {add_match}")
    if not add_match:
        print(f"    ORIG keys: {sorted(add_orig.get('properties', {}).keys())}")
        print(f"    WRAP keys: {sorted(add_wrap.get('properties', {}).keys())}")
        # Find specific differences
        for key in set(list(add_orig.keys()) + list(add_wrap.keys())):
            if add_orig.get(key) != add_wrap.get(key):
                print(f"    DIFF in '{key}':")
                orig_val = json.dumps(add_orig.get(key), indent=2) if key in add_orig else "(missing)"
                wrap_val = json.dumps(add_wrap.get(key), indent=2) if key in add_wrap else "(missing)"
                print(f"      ORIG: {orig_val[:200]}")
                print(f"      WRAP: {wrap_val[:200]}")

    print(f"  EditTaskCommand schema matches subclass: {edit_match}")
    if not edit_match:
        print(f"    ORIG keys: {sorted(edit_orig.get('properties', {}).keys())}")
        print(f"    WRAP keys: {sorted(edit_wrap.get('properties', {}).keys())}")
        for key in set(list(edit_orig.keys()) + list(edit_wrap.keys())):
            if edit_orig.get(key) != edit_wrap.get(key):
                print(f"    DIFF in '{key}':")
                orig_val = json.dumps(edit_orig.get(key), indent=2) if key in edit_orig else "(missing)"
                wrap_val = json.dumps(edit_wrap.get(key), indent=2) if key in edit_wrap else "(missing)"
                print(f"      ORIG: {orig_val[:200]}")
                print(f"      WRAP: {wrap_val[:200]}")

    # Also check: ignoring title, do they match?
    add_orig_no_title = {k: v for k, v in add_orig.items() if k != "title"}
    add_wrap_no_title = {k: v for k, v in add_wrap.items() if k != "title"}
    edit_orig_no_title = {k: v for k, v in edit_orig.items() if k != "title"}
    edit_wrap_no_title = {k: v for k, v in edit_wrap.items() if k != "title"}

    add_match_no_title = add_orig_no_title == add_wrap_no_title
    edit_match_no_title = edit_orig_no_title == edit_wrap_no_title

    print(f"\n  Ignoring 'title' field:")
    print(f"    AddTaskCommand schema matches:  {add_match_no_title}")
    print(f"    EditTaskCommand schema matches: {edit_match_no_title}")

    return add_match_no_title, edit_match_no_title


# ============================================================
# 5. Direct model validation (no FastMCP) -- isolate behavior
# ============================================================


def test_direct_validation():
    """Test model_validator(mode='wrap') directly, without FastMCP layer."""
    print("\n" + "=" * 70)
    print("DIRECT MODEL VALIDATION (no FastMCP)")
    print("  Does model_validator(mode='wrap') catch field-level errors?")
    print("=" * 70)

    test_cases = [
        ("Valid AddTask", AddTaskCommandWithReformat, {"name": "Buy groceries"}),
        ("Missing required 'name'", AddTaskCommandWithReformat, {"flagged": True}),
        (
            "Unknown field (extra=forbid)",
            AddTaskCommandWithReformat,
            {"name": "Test", "bogusField": "oops"},
        ),
        (
            "Bad frequency type in repetition rule (nested model)",
            AddTaskCommandWithReformat,
            {
                "name": "Test",
                "repetitionRule": {
                    "frequency": {"type": "biweekly"},
                    "schedule": "regularly",
                    "basedOn": "due_date",
                },
            },
        ),
        ("Valid EditTask", EditTaskCommandWithReformat, {"id": "abc123"}),
        (
            "EditTask: bad lifecycle in actions (nested model)",
            EditTaskCommandWithReformat,
            {"id": "abc123", "actions": {"lifecycle": "delete"}},
        ),
        (
            "EditTask: tag action with replace + add (model_validator in nested TagAction)",
            EditTaskCommandWithReformat,
            {
                "id": "abc123",
                "actions": {
                    "tags": {"replace": ["Work"], "add": ["Home"]},
                },
            },
        ),
    ]

    for label, model_cls, data in test_cases:
        print(f"\n  --- {label} ---")
        print(f"      Model: {model_cls.__name__}")
        print(f"      Data:  {json.dumps(data, default=str)}")
        try:
            obj = model_cls.model_validate(data)
            print(f"      RESULT: OK -> {obj!r}"[:200])
        except ValueError as ve:
            print(f"      CAUGHT ValueError: {ve}")
        except ValidationError as ve:
            # This means the wrap validator did NOT catch it
            print(f"      CAUGHT ValidationError (NOT caught by wrap!): {ve}")
        except Exception as e:
            print(f"      CAUGHT {type(e).__name__}: {e}")

    # Also check: what exception type does Pydantic raise when
    # model_validator(mode='wrap') raises ValueError?
    print("\n\n  --- Exception type investigation ---")
    print("  When model_validator raises ValueError, what does Pydantic surface?")
    try:
        AddTaskCommandWithReformat.model_validate({"flagged": True})
    except Exception as e:
        print(f"      Type:    {type(e).__module__}.{type(e).__name__}")
        print(f"      Message: {e}")
        if isinstance(e, ValidationError):
            print(f"      Errors:  {e.errors()}")


# ============================================================
# 6. FastMCP integration tests
# ============================================================


async def run_fastmcp_tests():
    """Run the same test cases through FastMCP Client."""
    print("\n\n" + "=" * 70)
    print("FASTMCP INTEGRATION TESTS")
    print("  Do reformatted errors reach the client through FastMCP?")
    print("=" * 70)

    results = []

    async with Client(mcp) as client:

        # Test 1: Valid AddTask
        results.append(
            await call_and_report(
                client,
                "TEST 1: Valid AddTaskCommand (should succeed)",
                "add_task",
                {"command": {"name": "Buy groceries"}},
            )
        )

        # Test 2: Missing required field
        results.append(
            await call_and_report(
                client,
                "TEST 2: AddTaskCommand missing required 'name'",
                "add_task",
                {"command": {"flagged": True}},
            )
        )

        # Test 3: Unknown field (extra=forbid)
        results.append(
            await call_and_report(
                client,
                "TEST 3: AddTaskCommand with unknown 'bogusField'",
                "add_task",
                {"command": {"name": "Test", "bogusField": "surprise!"}},
            )
        )

        # Test 4: Valid EditTask
        results.append(
            await call_and_report(
                client,
                "TEST 4: Valid EditTaskCommand (should succeed)",
                "edit_task",
                {"command": {"id": "abc123"}},
            )
        )

        # Test 5: Invalid lifecycle
        results.append(
            await call_and_report(
                client,
                "TEST 5: EditTask with invalid lifecycle 'delete'",
                "edit_task",
                {"command": {"id": "abc123", "actions": {"lifecycle": "delete"}}},
            )
        )

        # Test 6: Bad frequency discriminator
        results.append(
            await call_and_report(
                client,
                "TEST 6: EditTask with bad frequency type 'biweekly'",
                "edit_task",
                {
                    "command": {
                        "id": "abc123",
                        "repetitionRule": {
                            "frequency": {"type": "biweekly"},
                        },
                    }
                },
            )
        )

        # Test 7: Nested model validator error (TagAction replace + add)
        results.append(
            await call_and_report(
                client,
                "TEST 7: EditTask with conflicting tag action (replace + add)",
                "edit_task",
                {
                    "command": {
                        "id": "abc123",
                        "actions": {
                            "tags": {"replace": ["Work"], "add": ["Home"]},
                        },
                    }
                },
            )
        )

    return results


# ============================================================
# 7. Compare with middleware approach (inline)
# ============================================================


def compare_with_server_approach():
    """Show how the same errors look with server.py's current approach."""
    print("\n\n" + "=" * 70)
    print("COMPARISON: model_validator(wrap) vs server.py try/except")
    print("=" * 70)

    bad_inputs = [
        ("Missing 'name'", AddTaskCommand, {"flagged": True}),
        ("Unknown field", AddTaskCommand, {"name": "Test", "bogusField": "oops"}),
        (
            "Bad frequency type",
            AddTaskCommand,
            {
                "name": "Test",
                "repetitionRule": {
                    "frequency": {"type": "biweekly"},
                    "schedule": "regularly",
                    "basedOn": "due_date",
                },
            },
        ),
        (
            "Invalid lifecycle",
            EditTaskCommand,
            {"id": "abc123", "actions": {"lifecycle": "delete"}},
        ),
    ]

    for label, model_cls, data in bad_inputs:
        print(f"\n  --- {label} ---")

        # Server.py approach: catch ValidationError, format, raise ValueError
        try:
            model_cls.model_validate(data)
            server_msg = "(no error)"
        except ValidationError as exc:
            messages = _format_validation_errors(exc)
            server_msg = "; ".join(messages) or "Invalid input"

        # model_validator(wrap) approach: same data through subclass
        wrap_cls = (
            AddTaskCommandWithReformat
            if model_cls is AddTaskCommand
            else EditTaskCommandWithReformat
        )
        try:
            wrap_cls.model_validate(data)
            wrap_msg = "(no error)"
        except ValueError as ve:
            wrap_msg = str(ve)
        except ValidationError as ve:
            wrap_msg = f"[UNCAUGHT ValidationError] {ve}"

        match = server_msg == wrap_msg
        print(f"    Server approach: {server_msg}")
        print(f"    Wrap approach:   {wrap_msg}")
        print(f"    Match: {match}")


# ============================================================
# 8. Main
# ============================================================


async def main():
    print("=" * 70)
    print("SPIKE: model_validator(mode='wrap') for validation error reformatting")
    print("=" * 70)

    # Phase 1: Schema comparison (sync)
    add_match, edit_match = compare_schemas()

    # Phase 2: Direct model validation (sync)
    test_direct_validation()

    # Phase 3: FastMCP integration (async)
    fastmcp_results = await run_fastmcp_tests()

    # Phase 4: Comparison with server.py approach (sync)
    compare_with_server_approach()

    # ============================================================
    # SUMMARY
    # ============================================================
    print("\n\n" + "=" * 70)
    print("SUMMARY & ANSWERS TO KEY QUESTIONS")
    print("=" * 70)

    print(f"""
  1. Schema preservation:
     - AddTaskCommand schema matches subclass:  {add_match}
     - EditTaskCommand schema matches subclass: {edit_match}

  2. FastMCP integration results:""")

    for r in fastmcp_results:
        status = "OK" if r["success"] else f"ERROR: {r['error'][:120] if r['error'] else '?'}"
        print(f"     - {r['label']}: {status}")

    print("""
  Key observations (fill in after running):
  - Does model_validator(mode='wrap') catch field-level errors?
  - Does it catch nested model errors (RepetitionRule, TagAction)?
  - Is ValueError surfaced to FastMCP client as ToolError?
  - Are error messages identical to the server.py approach?
  - Any gotchas or caveats?
""")


if __name__ == "__main__":
    asyncio.run(main())
