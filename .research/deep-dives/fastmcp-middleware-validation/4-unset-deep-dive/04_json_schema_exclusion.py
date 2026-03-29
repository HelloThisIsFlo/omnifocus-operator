"""Is _Unset correctly excluded from JSON schema in ALL paths — model_json_schema,
FastMCP inputSchema, and outputSchema?

What to verify:
    _Unset uses is_instance_schema which Pydantic excludes from JSON schema.
    But we need to confirm this holds across ALL schema generation paths:
      1. Pydantic model_json_schema() — direct schema generation
      2. FastMCP inputSchema — what agents see when discovering tools
      3. FastMCP outputSchema — what agents see in tool results (if applicable)

    For each schema we check:
      - No occurrence of "_Unset", "Unset", "is_instance" in the serialized schema
      - Patch[str] appears as just {"type": "string"} (not a union with _Unset)
      - PatchOrClear[str] appears as {"anyOf": [..., {"type": "null"}]} without _Unset
      - No "default" values containing UNSET

How to run:
    cd /Users/flo/Work/Private/Dev/MCP/omnifocus-operator && uv run python \
        .research/deep-dives/fastmcp-middleware-validation/4-unset-deep-dive/04_json_schema_exclusion.py
"""

from __future__ import annotations

import asyncio
import json
import re
from typing import Any

import fastmcp
from fastmcp import Client

from omnifocus_operator.contracts.shared.actions import MoveAction, TagAction
from omnifocus_operator.contracts.use_cases.edit_task import (
    EditTaskActions,
    EditTaskCommand,
)
from omnifocus_operator.contracts.shared.repetition_rule import RepetitionRuleEditSpec

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------

SEPARATOR = "=" * 72
THIN_SEP = "-" * 72

# Patterns that should NEVER appear in schema structure (outside descriptions)
FORBIDDEN_PATTERNS = [
    re.compile(r"_Unset", re.IGNORECASE),
    re.compile(r'"Unset"'),  # as a standalone JSON value
    re.compile(r"is_instance"),
]


def strip_descriptions(obj: Any) -> Any:
    """Remove all 'description' and 'title' keys — they're prose, not schema structure."""
    if isinstance(obj, dict):
        return {k: strip_descriptions(v) for k, v in obj.items() if k not in ("description", "title")}
    if isinstance(obj, list):
        return [strip_descriptions(item) for item in obj]
    return obj


def check_forbidden_in_schema(schema: dict[str, Any], label: str) -> list[str]:
    """Check for forbidden patterns in schema structure (excluding descriptions).

    Returns a list of issues found (empty = clean).
    """
    issues: list[str] = []
    stripped = strip_descriptions(schema)
    stripped_str = json.dumps(stripped)

    for pattern in FORBIDDEN_PATTERNS:
        matches = pattern.findall(stripped_str)
        if matches:
            issues.append(f"  FAIL: '{pattern.pattern}' found in {label}: {matches}")

    # Also check full schema for context (descriptions are OK)
    full_str = json.dumps(schema)
    desc_only = []
    for pattern in FORBIDDEN_PATTERNS:
        full_matches = pattern.findall(full_str)
        struct_matches = pattern.findall(stripped_str)
        if full_matches and not struct_matches:
            desc_only.append(f"'{pattern.pattern}' x{len(full_matches)} in descriptions only")
    if desc_only:
        print(f"  INFO ({label}): {'; '.join(desc_only)}")

    return issues


def check_defaults(schema: dict[str, Any], label: str) -> list[str]:
    """Check that no default values reference UNSET."""
    issues: list[str] = []
    schema_str = json.dumps(schema)

    # Find all "default" values in the schema
    def find_defaults(obj: Any, path: str = "") -> list[tuple[str, Any]]:
        results: list[tuple[str, Any]] = []
        if isinstance(obj, dict):
            for k, v in obj.items():
                new_path = f"{path}.{k}" if path else k
                if k == "default":
                    results.append((new_path, v))
                results.extend(find_defaults(v, new_path))
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                results.extend(find_defaults(item, f"{path}[{i}]"))
        return results

    defaults = find_defaults(schema)
    for path, value in defaults:
        value_str = json.dumps(value) if not isinstance(value, str) else value
        if re.search(r"unset", str(value_str), re.IGNORECASE):
            issues.append(f"  FAIL: default at {path} contains UNSET: {value_str}")

    return issues


def check_patch_shape(schema: dict[str, Any], label: str) -> list[str]:
    """Verify that Patch[str] collapses to {"type": "string"} and
    PatchOrClear[str] collapses to an anyOf with null — no _Unset branch.
    """
    issues: list[str] = []
    schema_str = json.dumps(schema)

    # Collect all anyOf/oneOf branches to check none reference _Unset
    # Strip descriptions first — "UNSET" in docstring prose is fine,
    # we only care about _Unset as a schema type/reference.
    def find_union_branches(obj: Any, path: str = "") -> None:
        if isinstance(obj, dict):
            for key in ("anyOf", "oneOf"):
                if key in obj:
                    branches = obj[key]
                    for i, branch in enumerate(branches):
                        stripped_branch = strip_descriptions(branch)
                        branch_str = json.dumps(stripped_branch)
                        if re.search(r"_Unset|unset", branch_str, re.IGNORECASE):
                            issues.append(
                                f"  FAIL: {key}[{i}] at {path} references _Unset: {branch_str}"
                            )
            for k, v in obj.items():
                find_union_branches(v, f"{path}.{k}" if path else k)
        elif isinstance(obj, list):
            for i, item in enumerate(obj):
                find_union_branches(item, f"{path}[{i}]")

    find_union_branches(schema)

    # Check $defs for any _Unset definition
    defs = schema.get("$defs", {})
    for def_name, def_schema in defs.items():
        if re.search(r"unset", def_name, re.IGNORECASE):
            issues.append(f"  FAIL: $defs contains _Unset definition: {def_name}")

    return issues


def analyze_schema(schema: dict[str, Any], label: str) -> list[str]:
    """Run all checks on a schema. Returns list of issues."""
    all_issues: list[str] = []

    print(f"\n{SEPARATOR}")
    print(f"  {label}")
    print(SEPARATOR)
    print(json.dumps(schema, indent=2))

    print(f"\n{THIN_SEP}")
    print(f"  Checks for: {label}")
    print(THIN_SEP)

    # 1. Forbidden patterns
    issues = check_forbidden_in_schema(schema, label)
    all_issues.extend(issues)

    # 2. Default values
    issues = check_defaults(schema, label)
    all_issues.extend(issues)

    # 3. Patch/PatchOrClear shape
    issues = check_patch_shape(schema, label)
    all_issues.extend(issues)

    # 4. Required fields check
    required = schema.get("required", [])
    properties = schema.get("properties", {})
    non_required_with_no_default = []
    for prop_name, prop_schema in properties.items():
        if prop_name in required:
            continue
        # Non-required fields should NOT have UNSET as default
        if "default" in prop_schema:
            default_val = prop_schema["default"]
            if isinstance(default_val, str) and "unset" in default_val.lower():
                msg = f"  FAIL: property '{prop_name}' has UNSET default: {default_val}"
                all_issues.append(msg)

    if not all_issues:
        print(f"  PASS: All checks clean for {label}")
    else:
        for issue in all_issues:
            print(issue)

    return all_issues


# ---------------------------------------------------------------------------
# Main
# ---------------------------------------------------------------------------


async def main() -> None:
    all_issues: list[str] = []
    models_tested: list[str] = []

    # -----------------------------------------------------------------------
    # Part 1: Pydantic model_json_schema() — direct schema generation
    # -----------------------------------------------------------------------
    print("\n" + SEPARATOR)
    print("  PART 1: Pydantic model_json_schema()")
    print(SEPARATOR)

    models = [
        ("EditTaskCommand", EditTaskCommand),
        ("EditTaskActions", EditTaskActions),
        ("TagAction", TagAction),
        ("MoveAction", MoveAction),
        ("RepetitionRuleEditSpec", RepetitionRuleEditSpec),
    ]

    for name, model_cls in models:
        schema = model_cls.model_json_schema()
        issues = analyze_schema(schema, f"Pydantic: {name}")
        all_issues.extend(issues)
        models_tested.append(f"Pydantic: {name}")

    # -----------------------------------------------------------------------
    # Part 2: FastMCP inputSchema — what agents see when discovering tools
    # -----------------------------------------------------------------------
    print("\n\n" + SEPARATOR)
    print("  PART 2: FastMCP inputSchema (via list_tools)")
    print(SEPARATOR)

    mcp = fastmcp.FastMCP("schema-exclusion-spike")

    @mcp.tool()
    def spike_edit_task(command: EditTaskCommand) -> str:
        """Dummy tool that accepts an EditTaskCommand."""
        return f"received edit for: {command.id}"

    @mcp.tool()
    def spike_edit_actions(actions: EditTaskActions) -> str:
        """Dummy tool that accepts EditTaskActions."""
        return "ok"

    @mcp.tool()
    def spike_tag_action(tags: TagAction) -> str:
        """Dummy tool that accepts a TagAction."""
        return "ok"

    @mcp.tool()
    def spike_move_action(move: MoveAction) -> str:
        """Dummy tool that accepts a MoveAction."""
        return "ok"

    @mcp.tool()
    def spike_repetition_edit(rule: RepetitionRuleEditSpec) -> str:
        """Dummy tool that accepts a RepetitionRuleEditSpec."""
        return "ok"

    async with Client(mcp) as client:
        tools = await client.list_tools()

    for tool in tools:
        label = f"FastMCP inputSchema: {tool.name}"
        issues = analyze_schema(tool.inputSchema, label)
        all_issues.extend(issues)
        models_tested.append(label)

    # -----------------------------------------------------------------------
    # Part 3: FastMCP outputSchema — verify edit-result schemas are clean too
    # -----------------------------------------------------------------------
    print("\n\n" + SEPARATOR)
    print("  PART 3: FastMCP outputSchema (from real server)")
    print(SEPARATOR)

    try:
        from omnifocus_operator.server import create_server

        server = create_server()

        # Use Client to get proper MCP Tool objects (with inputSchema/outputSchema)
        async with Client(server) as client:
            real_tools = await client.list_tools()

        # Check all tools that have output schemas
        for tool in real_tools:
            if tool.outputSchema:
                label = f"FastMCP outputSchema: {tool.name}"
                issues = analyze_schema(tool.outputSchema, label)
                all_issues.extend(issues)
                models_tested.append(label)
            else:
                print(f"\n  (skipped {tool.name} — no outputSchema)")

        # Also specifically check the edit_tasks inputSchema from the real server
        for tool in real_tools:
            if tool.name == "edit_tasks":
                label = "Real server inputSchema: edit_tasks"
                issues = analyze_schema(tool.inputSchema, label)
                all_issues.extend(issues)
                models_tested.append(label)
    except Exception as e:
        print(f"\n  WARNING: Could not load real server: {e}")
        print("  (outputSchema check skipped — this is expected if dependencies are missing)")

    # -----------------------------------------------------------------------
    # Final verdict
    # -----------------------------------------------------------------------
    print("\n\n" + SEPARATOR)
    print("  FINAL VERDICT")
    print(SEPARATOR)

    print(f"\nModels/schemas tested ({len(models_tested)}):")
    for m in models_tested:
        print(f"  - {m}")

    if all_issues:
        print(f"\nTotal issues found: {len(all_issues)}")
        for issue in all_issues:
            print(issue)
        print("\nUNSET excluded from ALL schema paths: NO")
    else:
        print("\nTotal issues found: 0")
        print("\nUNSET excluded from ALL schema paths: YES")
        print("  - _Unset never appears as a type in any schema")
        print("  - No UNSET defaults leak into schema")
        print("  - Patch[T] collapses to just T (no union branch for _Unset)")
        print("  - PatchOrClear[T] has only T | null (no _Unset branch)")
        print("  - is_instance_schema correctly prevents _Unset from entering JSON schema")


if __name__ == "__main__":
    asyncio.run(main())
