"""How does FastMCP handle `list[Model]` parameters?

Questions:
- Does the schema properly reflect the list wrapper (type: array + items: {object schema})?
- Does validation work on each item in the list?
- If we change `items: list[dict[str, Any]]` to `items: list[AddTaskCommand]`,
  does FastMCP generate proper array-of-object schema with all fields?

What to look for in the output:
- Schema for single_model: should show AddTaskCommand fields at top level
- Schema for list_model: should show type=array with items containing AddTaskCommand schema
- Schema for list_dict: should show type=array with items as generic dict/object
- Validation: valid list should succeed, invalid data should fail, empty list should succeed

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/1-schema-generation/04_list_wrapper_behavior.py
"""

from __future__ import annotations

import asyncio
import json
import traceback
from typing import Any

import fastmcp
from fastmcp import Client

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

mcp = fastmcp.FastMCP("list-wrapper-spike")


@mcp.tool()
def single_model(command: AddTaskCommand) -> str:
    """Accepts a single AddTaskCommand."""
    return f"single: {command.name}"


@mcp.tool()
def list_model(items: list[AddTaskCommand]) -> str:
    """Accepts a list of AddTaskCommand."""
    return f"list_model: {[item.name for item in items]}"


@mcp.tool()
def list_dict(items: list[dict[str, Any]]) -> str:
    """Accepts a list of plain dicts."""
    return f"list_dict: {items}"


def print_section(title: str) -> None:
    print()
    print("=" * 72)
    print(title)
    print("=" * 72)


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

        # ── Part 1: Print all schemas ────────────────────────────────
        tools_by_name = {t.name: t for t in tools}

        for name in ("single_model", "list_model", "list_dict"):
            tool = tools_by_name[name]
            print_section(f"Schema: {name}")
            print(json.dumps(tool.inputSchema, indent=2))

        # ── Part 2: Validation behavior ──────────────────────────────

        # 2a: Valid list with 1 item
        print_section("Call list_model — valid list of 1 item")
        try:
            result = await client.call_tool(
                "list_model",
                {"items": [{"name": "Buy milk"}]},
            )
            print(f"SUCCESS: {result}")
        except Exception:
            print(f"FAILED:\n{traceback.format_exc()}")

        # 2b: Invalid data in list (missing required 'name' field)
        print_section("Call list_model — invalid item (missing 'name')")
        try:
            result = await client.call_tool(
                "list_model",
                {"items": [{"flagged": True}]},
            )
            print(f"SUCCESS (unexpected): {result}")
        except Exception:
            print(f"VALIDATION ERROR (expected):\n{traceback.format_exc()}")

        # 2c: Invalid data in list (extra field, CommandModel has extra=forbid)
        print_section("Call list_model — invalid item (unknown field)")
        try:
            result = await client.call_tool(
                "list_model",
                {"items": [{"name": "Test", "bogusField": "oops"}]},
            )
            print(f"SUCCESS (unexpected): {result}")
        except Exception:
            print(f"VALIDATION ERROR (expected):\n{traceback.format_exc()}")

        # 2d: Empty list
        print_section("Call list_model — empty list")
        try:
            result = await client.call_tool(
                "list_model",
                {"items": []},
            )
            print(f"SUCCESS: {result}")
        except Exception:
            print(f"FAILED:\n{traceback.format_exc()}")

        # 2e: Valid list with 2 items (one with many fields)
        print_section("Call list_model — valid list of 2 items")
        try:
            result = await client.call_tool(
                "list_model",
                {
                    "items": [
                        {"name": "Task A", "flagged": True},
                        {
                            "name": "Task B",
                            "estimatedMinutes": 30,
                            "note": "Details here",
                        },
                    ],
                },
            )
            print(f"SUCCESS: {result}")
        except Exception:
            print(f"FAILED:\n{traceback.format_exc()}")

        # 2f: Compare list_dict with same payload
        print_section("Call list_dict — same payload (no model validation)")
        try:
            result = await client.call_tool(
                "list_dict",
                {"items": [{"flagged": True}]},
            )
            print(f"SUCCESS (no model validation): {result}")
        except Exception:
            print(f"FAILED:\n{traceback.format_exc()}")


if __name__ == "__main__":
    asyncio.run(main())
