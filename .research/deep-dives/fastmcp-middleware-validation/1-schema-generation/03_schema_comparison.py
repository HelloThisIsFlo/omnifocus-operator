"""What's the difference between dict[str, Any] vs typed params vs model_json_schema()?

What do agents actually see in each case? This script registers 4 FastMCP tools --
two typed (using real Pydantic models) and two untyped (using list[dict[str, Any]]) --
then compares the schemas that agents receive via list_tools().

What to look for in the output:
- Typed tools should have rich schemas with properties, required fields, enums, and $defs.
- Untyped tools should have near-empty schemas -- agents get zero structural guidance.
- The "richness score" quantifies this gap: properties, required fields, enums, $ref count.
- Byte sizes show whether rich schemas risk hitting MCP client payload limits.

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/1-schema-generation/03_schema_comparison.py
"""

from __future__ import annotations

import asyncio
import json
from typing import Any

import fastmcp
from fastmcp import Client

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

mcp = fastmcp.FastMCP("schema-comparison-spike")


# --- Typed tools (real models) ---


@mcp.tool()
def add_typed(command: AddTaskCommand) -> str:
    """Create tasks using a fully typed AddTaskCommand model."""
    return f"received: {command.name}"


@mcp.tool()
def edit_typed(command: EditTaskCommand) -> str:
    """Edit tasks using a fully typed EditTaskCommand model."""
    return f"received: {command.id}"


# --- Untyped tools (dict-based) ---


@mcp.tool()
def add_untyped(items: list[dict[str, Any]]) -> str:
    """Create tasks using untyped dicts -- no schema guidance for agents."""
    return f"received {len(items)} items"


@mcp.tool()
def edit_untyped(items: list[dict[str, Any]]) -> str:
    """Edit tasks using untyped dicts -- no schema guidance for agents."""
    return f"received {len(items)} items"


# --- Schema analysis helpers ---


def count_recursive(schema: dict[str, Any], key: str) -> int:
    """Count occurrences of a key anywhere in the schema tree."""
    count = 0
    if key in schema:
        val = schema[key]
        if isinstance(val, list):
            count += len(val)
        elif isinstance(val, dict):
            count += len(val)
        else:
            count += 1
    for v in schema.values():
        if isinstance(v, dict):
            count += count_recursive(v, key)
        elif isinstance(v, list):
            for item in v:
                if isinstance(item, dict):
                    count += count_recursive(item, key)
    return count


def richness_score(schema: dict[str, Any]) -> dict[str, int]:
    """Calculate richness metrics for a schema."""
    return {
        "properties": count_recursive(schema, "properties"),
        "required": count_recursive(schema, "required"),
        "enum": count_recursive(schema, "enum"),
        "$defs": len(schema.get("$defs", {})),
    }


def byte_size(schema: dict[str, Any]) -> int:
    """JSON-serialized byte size of the schema."""
    return len(json.dumps(schema).encode("utf-8"))


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

    # Index tools by name
    tool_map = {t.name: t for t in tools}
    assert len(tool_map) == 4, f"Expected 4 tools, got {len(tool_map)}"

    tool_names = ["add_typed", "add_untyped", "edit_typed", "edit_untyped"]

    # --- Print full schemas ---
    for name in tool_names:
        schema = tool_map[name].inputSchema
        print("=" * 72)
        print(f"Tool: {name}")
        print(f"Description: {tool_map[name].description}")
        print("=" * 72)
        print(json.dumps(schema, indent=2))
        print()

    # --- Richness comparison table ---
    print("=" * 72)
    print("RICHNESS SCORE COMPARISON")
    print("=" * 72)
    header = f"{'Tool':<20} {'properties':>12} {'required':>10} {'enum':>8} {'$defs':>8} {'bytes':>10}"
    print(header)
    print("-" * len(header))
    for name in tool_names:
        schema = tool_map[name].inputSchema
        scores = richness_score(schema)
        size = byte_size(schema)
        print(
            f"{name:<20} {scores['properties']:>12} {scores['required']:>10} "
            f"{scores['enum']:>8} {scores['$defs']:>8} {size:>10}"
        )
    print()

    # --- model_json_schema() comparison (typed tools only) ---
    print("=" * 72)
    print("PYDANTIC model_json_schema() vs FASTMCP inputSchema")
    print("=" * 72)
    for model_cls, tool_name in [
        (AddTaskCommand, "add_typed"),
        (EditTaskCommand, "edit_typed"),
    ]:
        pydantic_schema = model_cls.model_json_schema()
        fastmcp_schema = tool_map[tool_name].inputSchema
        pydantic_bytes = byte_size(pydantic_schema)
        fastmcp_bytes = byte_size(fastmcp_schema)
        match = pydantic_schema == fastmcp_schema
        # FastMCP wraps the model schema inside a top-level properties object,
        # so check if the model schema appears nested under the parameter name
        nested_key = "command"
        fastmcp_inner = fastmcp_schema.get("properties", {}).get(nested_key, {})
        # Check if $defs are hoisted to top level
        has_defs_at_top = "$defs" in fastmcp_schema
        has_defs_in_pydantic = "$defs" in pydantic_schema

        print(f"\n--- {model_cls.__name__} ({tool_name}) ---")
        print(f"  Pydantic schema bytes:  {pydantic_bytes}")
        print(f"  FastMCP schema bytes:   {fastmcp_bytes}")
        print(f"  Exact match:            {match}")
        print(f"  $defs in Pydantic:      {has_defs_in_pydantic} ({len(pydantic_schema.get('$defs', {}))} defs)")
        print(f"  $defs in FastMCP:       {has_defs_at_top} ({len(fastmcp_schema.get('$defs', {}))} defs)")
        if fastmcp_inner and "$ref" in fastmcp_inner:
            print(f"  FastMCP wraps model as: properties.command.$ref = {fastmcp_inner['$ref']}")
        elif fastmcp_inner:
            print(f"  FastMCP inlines model under: properties.command (keys: {list(fastmcp_inner.keys())})")

    print()
    print("=" * 72)
    print("SUMMARY")
    print("=" * 72)
    for name in tool_names:
        schema = tool_map[name].inputSchema
        scores = richness_score(schema)
        total = sum(scores.values())
        size = byte_size(schema)
        print(f"  {name:<20}  richness={total:<6}  bytes={size}")
    print()
    print("Key takeaway: Compare the richness scores and byte sizes between")
    print("typed vs untyped tools to see what structural guidance agents lose")
    print("when schemas use dict[str, Any] instead of Pydantic models.")


if __name__ == "__main__":
    asyncio.run(main())
