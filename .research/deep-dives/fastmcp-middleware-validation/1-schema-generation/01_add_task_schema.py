"""What inputSchema does FastMCP generate when a tool uses AddTaskCommand as a typed parameter?

What to look for in the output:
- Does FastMCP inline the full model schema into inputSchema, or use $defs/$ref?
- Are camelCase aliases (from OmniFocusBaseModel) honored in the generated schema?
- Does the nested RepetitionRuleAddSpec (with its Frequency discriminated union) survive intact?
- How does the FastMCP-generated schema compare to Pydantic's own model_json_schema()?

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/1-schema-generation/01_add_task_schema.py
"""

from __future__ import annotations

import asyncio
import json

import fastmcp
from fastmcp import Client

from omnifocus_operator.contracts.use_cases.add_task import AddTaskCommand

mcp = fastmcp.FastMCP("schema-spike")


@mcp.tool()
def spike_add_task(command: AddTaskCommand) -> str:
    """Dummy tool that accepts an AddTaskCommand."""
    return f"received: {command.name}"


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

    assert len(tools) == 1, f"Expected 1 tool, got {len(tools)}"
    tool = tools[0]
    fastmcp_schema = tool.inputSchema

    pydantic_schema = AddTaskCommand.model_json_schema()

    print("=" * 72)
    print("FastMCP-generated inputSchema (from list_tools)")
    print("=" * 72)
    print(json.dumps(fastmcp_schema, indent=2))

    print()
    print("=" * 72)
    print("Pydantic model_json_schema (direct)")
    print("=" * 72)
    print(json.dumps(pydantic_schema, indent=2))


if __name__ == "__main__":
    asyncio.run(main())
