"""Approach 2: Keep dict[str, Any] handler signature, inject typed schema via on_list_tools middleware.

HYBRID approach -- handler code stays exactly as-is (manual model_validate + _format_validation_errors),
but agents see a rich inputSchema because on_list_tools overrides it at list time.

Key questions:
- Does this decouple schema exposure from validation handling?
- Is there any client-side validation that might reject valid dict data?
- Does the handler still receive list[dict] even though the schema says list[AddTaskCommand]?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/3-approaches/02_on_list_tools_schema.py
"""

from __future__ import annotations

import asyncio
import json
from collections.abc import Sequence
from typing import Any

import mcp.types as mt
from fastmcp import Client, FastMCP
from fastmcp.server.middleware import CallNext, Middleware, MiddlewareContext
from fastmcp.utilities.json_schema import compress_schema
from pydantic import TypeAdapter, ValidationError

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

# ============================================================
# 1. Schema generation from real models
# ============================================================

# Generate JSON schemas for the items parameter using TypeAdapter
_add_items_schema = TypeAdapter(list[AddTaskCommand]).json_schema()
_edit_items_schema = TypeAdapter(list[EditTaskCommand]).json_schema()

# Build the full inputSchema (wrapping items in an object with properties)
SCHEMA_OVERRIDES: dict[str, dict[str, Any]] = {
    "add_tasks": {
        "type": "object",
        "properties": {
            "items": _add_items_schema,
        },
        "required": ["items"],
    },
    "edit_tasks": {
        "type": "object",
        "properties": {
            "items": _edit_items_schema,
        },
        "required": ["items"],
    },
}

# Apply FastMCP's schema compression (dereference $refs, prune unused $defs)
for name in SCHEMA_OVERRIDES:
    SCHEMA_OVERRIDES[name] = compress_schema(SCHEMA_OVERRIDES[name], dereference=True)


# ============================================================
# 2. SchemaInjectionMiddleware -- overrides on_list_tools
# ============================================================

# IMPORTANT DISCOVERY:
# on_list_tools middleware receives FastMCP's INTERNAL Tool objects
# (fastmcp.tools.tool.Tool), NOT mcp.types.Tool. The internal Tool
# uses `parameters` (dict[str, Any]) which later becomes `inputSchema`
# on the wire via Tool.to_mcp_tool(). So we must override `parameters`,
# not `inputSchema`.

# Import the internal Tool type for type clarity (the middleware actually
# receives these, despite the type hint saying mcp.types.Tool)
from fastmcp.tools.tool import Tool as FastMCPTool  # noqa: E402


class SchemaInjectionMiddleware(Middleware):
    """Override inputSchema at list time while leaving handler signatures untouched.

    After call_next() returns the tool list, iterate through and replace
    the `parameters` field for tools that have a schema override registered.

    NOTE: The middleware receives FastMCP's internal Tool objects where the
    schema field is called `parameters`. This gets converted to `inputSchema`
    on the wire via Tool.to_mcp_tool(). This is a key implementation detail.
    """

    async def on_list_tools(
        self,
        context: MiddlewareContext[mt.ListToolsRequest],
        call_next: CallNext[mt.ListToolsRequest, Sequence[FastMCPTool]],
    ) -> Sequence[FastMCPTool]:
        tools = await call_next(context)
        result: list[FastMCPTool] = []
        for tool in tools:
            override = SCHEMA_OVERRIDES.get(tool.name)
            if override:
                # MUST use `parameters` -- the internal field name.
                # This becomes `inputSchema` on the wire via to_mcp_tool().
                tool = tool.model_copy(update={"parameters": override})
            result.append(tool)
        return result


# ============================================================
# 3. Server with UNTYPED handlers (current production signature)
# ============================================================

mcp_server = FastMCP("approach-02-hybrid")
mcp_server.add_middleware(SchemaInjectionMiddleware())


@mcp_server.tool()
def add_tasks(items: list[dict[str, Any]]) -> str:
    """Create tasks in OmniFocus."""
    # Simulate current production pattern: manual validation inside handler
    validated = []
    errors = []
    for i, item in enumerate(items):
        try:
            cmd = AddTaskCommand.model_validate(item)
            validated.append(cmd)
        except ValidationError as e:
            errors.append(f"Item {i}: {e}")
    if errors:
        return "VALIDATION ERRORS:\n" + "\n".join(errors)
    return f"SUCCESS: created {len(validated)} tasks: {[c.name for c in validated]}"


@mcp_server.tool()
def edit_tasks(items: list[dict[str, Any]]) -> str:
    """Edit existing tasks using patch semantics."""
    validated = []
    errors = []
    for i, item in enumerate(items):
        try:
            cmd = EditTaskCommand.model_validate(item)
            validated.append(cmd)
        except ValidationError as e:
            errors.append(f"Item {i}: {e}")
    if errors:
        return "VALIDATION ERRORS:\n" + "\n".join(errors)
    return f"SUCCESS: edited {len(validated)} tasks: {[c.id for c in validated]}"


# ============================================================
# 4. Test harness
# ============================================================


def _print_section(title: str) -> None:
    print(f"\n{'=' * 70}")
    print(f"  {title}")
    print(f"{'=' * 70}")


def _extract_text(result: Any) -> str:
    """Extract text from a CallToolResult."""
    if hasattr(result, "__iter__") and not isinstance(result, str):
        return " ".join(c.text for c in result if hasattr(c, "text"))
    return str(result)


async def run_tests() -> None:
    print("=" * 70)
    print("  APPROACH 2: on_list_tools Schema Injection (Hybrid)")
    print("=" * 70)

    async with Client(mcp_server) as client:

        # --------------------------------------------------
        # Test 1: Verify schema is rich (not generic dict)
        # --------------------------------------------------
        _print_section("TEST 1: list_tools() -- Schema agents see")
        tools = await client.list_tools()
        for tool in tools:
            print(f"\n  Tool: {tool.name}")
            schema_str = json.dumps(tool.inputSchema, indent=4)
            print(f"  inputSchema:\n{_indent(schema_str, 4)}")
            # Check if schema is rich (may use $ref or inline properties)
            props = tool.inputSchema.get("properties", {})
            items_schema = props.get("items", {})
            defs = items_schema.get("$defs", {})
            if "items" in items_schema:
                nested = items_schema["items"]
                # Resolve $ref if present
                if "$ref" in nested:
                    ref_name = nested["$ref"].split("/")[-1]
                    resolved = defs.get(ref_name, {})
                    if "properties" in resolved:
                        print(f"\n  --> RICH schema (via $ref -> {ref_name}): {list(resolved['properties'].keys())}")
                        print(f"      required: {resolved.get('required', [])}")
                        print(f"      additionalProperties: {resolved.get('additionalProperties', 'not set')}")
                    else:
                        print(f"\n  --> $ref to {ref_name} but no properties found")
                elif "properties" in nested:
                    print(f"\n  --> RICH schema (inline): {list(nested['properties'].keys())}")
                else:
                    print(f"\n  --> GENERIC schema: items array lacks typed properties")
            else:
                print(f"\n  --> Unexpected schema shape")

        # --------------------------------------------------
        # Test 2: Valid call -- handler receives list[dict]
        # --------------------------------------------------
        _print_section("TEST 2: Valid add_tasks call -- handler receives list[dict]?")
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Buy milk", "flagged": True},
                    {"name": "Write tests", "dueDate": "2026-04-01T17:00:00Z"},
                ]
            },
        )
        print(f"  Result: {_extract_text(result)}")

        # --------------------------------------------------
        # Test 3: Invalid data -- handler's OWN validation catches it
        # --------------------------------------------------
        _print_section("TEST 3: Invalid data -- handler validation catches it?")
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"flagged": True},  # missing required 'name'
                ]
            },
        )
        print(f"  Result: {_extract_text(result)}")

        # --------------------------------------------------
        # Test 4: Unknown field -- extra="forbid" via manual validation
        # --------------------------------------------------
        _print_section("TEST 4: Unknown field -- extra='forbid' works via manual validation?")
        result = await client.call_tool(
            "add_tasks",
            {
                "items": [
                    {"name": "Buy milk", "bogusField": True},
                ]
            },
        )
        print(f"  Result: {_extract_text(result)}")

        # --------------------------------------------------
        # Test 5: Valid edit_tasks call
        # --------------------------------------------------
        _print_section("TEST 5: Valid edit_tasks call")
        result = await client.call_tool(
            "edit_tasks",
            {
                "items": [
                    {"id": "abc123", "name": "Updated name"},
                ]
            },
        )
        print(f"  Result: {_extract_text(result)}")

        # --------------------------------------------------
        # Test 6: Comparison -- schema vs runtime types
        # --------------------------------------------------
        _print_section("TEST 6: Schema agents see vs what handler receives")

        print("\n  SCHEMA AGENTS SEE (inputSchema from list_tools):")
        add_tool = next(t for t in tools if t.name == "add_tasks")
        items_prop = add_tool.inputSchema["properties"]["items"]
        defs = items_prop.get("$defs", {})
        # Resolve the item schema (may be $ref or inline)
        nested = items_prop.get("items", {})
        if "$ref" in nested:
            ref_name = nested["$ref"].split("/")[-1]
            resolved = defs.get(ref_name, {})
            print(f"    items[]: $ref -> {ref_name}")
            print(f"    items[].properties: {list(resolved.get('properties', {}).keys())}")
            print(f"    items[].required:   {resolved.get('required', [])}")
        elif "properties" in nested:
            print(f"    items[].properties: {list(nested['properties'].keys())}")
            print(f"    items[].required:   {nested.get('required', [])}")
        print(f"    Full items schema type: {items_prop.get('type', 'N/A')}")
        print(f"    $defs count: {len(defs)} (nested type definitions)")

        print("\n  WHAT THE HANDLER RECEIVES:")
        print("    Parameter type annotation: list[dict[str, Any]]")
        print("    FastMCP passes raw dicts -- NO pre-validation by framework")
        print("    Handler does its own AddTaskCommand.model_validate(item)")

        print("\n  KEY INSIGHT:")
        print("    Schema is DECOUPLED from validation.")
        print("    - Agents see rich schema -> better tool calls, fewer mistakes")
        print("    - Handler validates manually -> custom error formatting preserved")
        print("    - No client-side schema validation conflicts (handler gets raw dict)")

        # --------------------------------------------------
        # Test 7: Key question -- client-side validation risk?
        # --------------------------------------------------
        _print_section("TEST 7: Client-side validation risk assessment")
        print("""
  Q: Could a client reject valid dict data based on the rich inputSchema?

  A: The MCP protocol says inputSchema is INFORMATIONAL -- clients use it to
     generate UI or validate before sending, but the server is the authority.
     In practice:
     - Claude Desktop: uses inputSchema for tool-call generation, not rejection
     - Most MCP clients: same -- schema informs, doesn't gatekeep
     - The handler receives raw JSON regardless of inputSchema content

  Q: What if inputSchema has additionalProperties: false but handler is lenient?

  A: Not a problem here because:
     1. Our CommandModel has extra="forbid" (AddTaskCommand rejects unknowns)
     2. Schema and validation are aligned -- both forbid extras
     3. Even if a client did pre-validate, it would match our server behavior

  IMPLEMENTATION NOTE:
     on_list_tools middleware receives FastMCP's INTERNAL Tool objects
     (fastmcp.tools.tool.Tool / FunctionTool), NOT mcp.types.Tool.
     The schema field is `parameters` internally, which becomes `inputSchema`
     on the wire via Tool.to_mcp_tool(). Use model_copy(update={"parameters": ...}).
""")


def _indent(text: str, spaces: int) -> str:
    prefix = " " * spaces
    return "\n".join(prefix + line for line in text.split("\n"))


if __name__ == "__main__":
    asyncio.run(run_tests())
