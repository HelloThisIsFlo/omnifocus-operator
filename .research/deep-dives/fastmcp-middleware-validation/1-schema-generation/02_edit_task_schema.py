"""What inputSchema does FastMCP generate when a tool uses EditTaskCommand (with UNSET/Patch fields)?

The UNSET complication:
    EditTaskCommand uses Patch[T] (= Union[T, _Unset]) and PatchOrClear[T] (= Union[T, None, _Unset])
    for patch semantics. The _Unset class uses `is_instance_schema` in __get_pydantic_core_schema__
    so Pydantic accepts it during validation but excludes it from JSON schema automatically.

What to look for:
    - UNSET/_Unset should NOT appear anywhere in the generated schema
    - Patch[str] should appear as just {"type": "string"} (not a union)
    - PatchOrClear[str] should appear as {"anyOf": [{"type": "string"}, {"type": "null"}]} or similar
    - Patch fields should NOT be required (they default to UNSET)
    - Only `id` should be required (no default)
    - Nested models (EditTaskActions, TagAction, MoveAction, RepetitionRuleEditSpec) should survive
    - camelCase aliases should be honored

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/1-schema-generation/02_edit_task_schema.py
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import fastmcp
from fastmcp import Client

from omnifocus_operator.contracts.use_cases.edit_task import EditTaskCommand

mcp = fastmcp.FastMCP("schema-spike")


@mcp.tool()
def spike_edit_task(command: EditTaskCommand) -> str:
    """Dummy tool that accepts an EditTaskCommand."""
    return f"received edit for: {command.id}"


async def main() -> None:
    async with Client(mcp) as client:
        tools = await client.list_tools()

    assert len(tools) == 1, f"Expected 1 tool, got {len(tools)}"
    tool = tools[0]
    fastmcp_schema = tool.inputSchema

    pydantic_schema = EditTaskCommand.model_json_schema()

    print("=" * 72)
    print("FastMCP-generated inputSchema (from list_tools)")
    print("=" * 72)
    print(json.dumps(fastmcp_schema, indent=2))

    print()
    print("=" * 72)
    print("Pydantic model_json_schema (direct)")
    print("=" * 72)
    print(json.dumps(pydantic_schema, indent=2))

    # --- UNSET artifact check ---
    # We check two things:
    #   1. Does _Unset/UNSET appear as a *type* in the schema structure?
    #      (e.g., in anyOf/oneOf branches, $defs, type fields) -- this would be a bug.
    #   2. Does the word "UNSET" appear in description strings?
    #      That's fine -- it's just docstring prose, not a schema type.
    print()
    print("=" * 72)
    print("UNSET artifact check")
    print("=" * 72)

    def check_unset_in_schema(schema: dict[str, Any], label: str) -> None:
        schema_str = json.dumps(schema)

        # Check for _Unset as a type reference (the actual bug we care about)
        type_pattern = re.compile(r"_[Uu]nset")
        type_matches = type_pattern.findall(schema_str)

        # Check for UNSET anywhere (includes descriptions)
        all_pattern = re.compile(r"UNSET|_Unset")
        all_matches = all_pattern.findall(schema_str)

        # Filter: find UNSET only in non-description contexts
        # Strip all "description" values and re-check
        def strip_descriptions(obj: Any) -> Any:
            if isinstance(obj, dict):
                return {k: strip_descriptions(v) for k, v in obj.items() if k != "description"}
            if isinstance(obj, list):
                return [strip_descriptions(item) for item in obj]
            return obj

        stripped = strip_descriptions(schema)
        stripped_str = json.dumps(stripped)
        structural_matches = re.findall(r"UNSET|_Unset|unset", stripped_str, re.IGNORECASE)

        if type_matches:
            print(f"  BUG: {label} has _Unset type references: {type_matches}")
        elif structural_matches:
            print(f"  WARNING: {label} has UNSET in non-description fields: {structural_matches}")
        elif all_matches:
            print(
                f"  OK: {label} mentions UNSET only in descriptions (prose, not schema type) "
                f"-- {len(all_matches)} occurrence(s)"
            )
        else:
            print(f"  OK: {label} has no UNSET references at all")

    check_unset_in_schema(fastmcp_schema, "FastMCP schema")
    check_unset_in_schema(pydantic_schema, "Pydantic schema")

    # --- Required fields check ---
    print()
    print("=" * 72)
    print("Required fields check")
    print("=" * 72)

    # Check in the command sub-schema (FastMCP wraps in properties.command)
    if "properties" in fastmcp_schema and "command" in fastmcp_schema["properties"]:
        command_ref = fastmcp_schema["properties"]["command"]
        # Might be a $ref or inline -- check $defs too
        print(f"FastMCP command property: {json.dumps(command_ref, indent=2)}")

    pydantic_required = pydantic_schema.get("required", [])
    print(f"Pydantic required fields: {pydantic_required}")
    if pydantic_required == ["id"]:
        print("OK: Only 'id' is required (all Patch/PatchOrClear fields have UNSET defaults)")
    else:
        print(f"NOTE: Required fields differ from expected ['id']: {pydantic_required}")

    # --- Schema equality check ---
    print()
    print("=" * 72)
    print("Schema comparison")
    print("=" * 72)

    # FastMCP wraps the model in {properties: {command: ...}, required: ["command"]}
    # Extract just the command part for comparison
    if "$defs" in fastmcp_schema:
        # FastMCP might put EditTaskCommand in $defs
        fastmcp_defs = fastmcp_schema.get("$defs", {})
        pydantic_defs = pydantic_schema.get("$defs", {})
        if "EditTaskCommand" in fastmcp_defs and "EditTaskCommand" not in pydantic_defs:
            print("FastMCP moved EditTaskCommand to $defs (Pydantic has it inline)")
        elif fastmcp_defs == pydantic_defs:
            print("$defs match between FastMCP and Pydantic")
        else:
            fastmcp_def_keys = sorted(fastmcp_defs.keys())
            pydantic_def_keys = sorted(pydantic_defs.keys())
            print(f"FastMCP $defs keys: {fastmcp_def_keys}")
            print(f"Pydantic $defs keys: {pydantic_def_keys}")
            if fastmcp_def_keys == pydantic_def_keys:
                print("Same $defs keys -- checking content equality...")
                for key in fastmcp_def_keys:
                    if fastmcp_defs[key] == pydantic_defs[key]:
                        print(f"  {key}: MATCH")
                    else:
                        print(f"  {key}: DIFFER")
            else:
                print("Different $defs keys")
    else:
        print("No $defs in FastMCP schema")


if __name__ == "__main__":
    asyncio.run(main())
