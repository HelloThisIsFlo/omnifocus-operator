"""Experiment 01: Server & Context — Basic Migration + Context Access

QUESTION: Does our migration pattern work? What's available on the Context object?

WHAT THIS PROVES:
  Run the script and check the output. The guide skill will walk you through
  the code and connect it to the real codebase (server.py, conftest.py).

  Part A: Do the FastMCP v3 imports work? Does our lifespan pattern survive?
  Part B: Which context access path works? (old vs new)
  Part C: What's available on the Context object beyond lifespan?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/01_server_and_context.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

# --- THE key import change ---
from fastmcp import FastMCP, Context, Client
from mcp.types import ToolAnnotations


# ── Lifespan: mirrors our real app_lifespan() ────────────────────────

@asynccontextmanager
async def app_lifespan(app: FastMCP):  # type: ignore[type-arg]
    fake_service = {"name": "FakeOperatorService", "status": "ready"}
    yield {"service": fake_service}


# ── Server: mirrors our create_server() ──────────────────────────────

mcp = FastMCP("spike-server", lifespan=app_lifespan)


@mcp.tool(annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True))
async def inspect_context(ctx: Context) -> dict[str, Any]:
    """Inspects the full Context object and tests both access patterns."""
    results: dict[str, Any] = {}

    # --- Access pattern: current code (old) ---
    try:
        old = ctx.request_context.lifespan_context["service"]  # type: ignore[attr-defined]
        results["old_path_works"] = True
        results["old_path_value"] = old
    except Exception as e:
        results["old_path_works"] = False
        results["old_path_error"] = str(e)

    # --- Access pattern: FastMCP v3 (new) ---
    try:
        new = ctx.lifespan_context["service"]
        results["new_path_works"] = True
        results["new_path_value"] = new
    except Exception as e:
        results["new_path_works"] = False
        results["new_path_error"] = str(e)

    # --- Full Context attribute inventory ---
    for attr in ["request_id", "client_id", "session_id", "fastmcp", "session", "transport"]:
        try:
            val = getattr(ctx, attr, "NOT_FOUND")
            if val == "NOT_FOUND":
                results[f"ctx.{attr}"] = "not found"
            else:
                results[f"ctx.{attr}"] = str(val)[:100]  # truncate long values
        except Exception as e:
            results[f"ctx.{attr}"] = f"error: {e}"

    # All available attributes
    results["all_attributes"] = sorted(a for a in dir(ctx) if not a.startswith("_"))

    return results


# ── Run ──────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 64)
    print("  EXPERIMENT 01: Server & Context")
    print("=" * 64)

    # Part A: Do imports and server creation work?
    print("\n── Part A: Migration Shape ──────────────────────────────")
    print(f"  FastMCP import:       from fastmcp import FastMCP, Context")
    print(f"  ToolAnnotations:      from mcp.types import ToolAnnotations")
    print(f"  Server created:       {mcp.name}")
    print(f"  Lifespan attached:    {mcp._lifespan is not None}")
    tools = await mcp.list_tools()  # type: ignore[call-arg]
    print(f"  Tools registered:     {[t.name for t in tools]}")
    print(f"  ToolAnnotations:      {tools[0].annotations}")

    # Part B + C: Context access and inventory
    print("\n── Part B: Context Access Patterns ─────────────────────")
    async with Client(mcp) as client:
        result = await client.call_tool("inspect_context", {})

    # Client.call_tool() returns CallToolResult — extract via .data or .content
    if hasattr(result, "data") and isinstance(result.data, dict):
        data = result.data
    elif hasattr(result, "structured_content") and isinstance(result.structured_content, dict):
        data = result.structured_content
    elif hasattr(result, "content"):
        import json
        for block in result.content:
            if hasattr(block, "text"):
                data = json.loads(block.text)
                break
        else:
            data = {"raw": str(result)}
    elif isinstance(result, dict):
        data = result
    else:
        data = {"raw": str(result)}

    old_ok = data.get("old_path_works", "?")
    new_ok = data.get("new_path_works", "?")
    print(f"  ctx.request_context.lifespan_context:  {'WORKS' if old_ok else 'BROKEN'}")
    print(f"  ctx.lifespan_context:                  {'WORKS' if new_ok else 'BROKEN'}")

    if old_ok and new_ok:
        print(f"  -> Both work. Migrate at your pace.")
    elif new_ok:
        print(f"  -> Only new path works. Must update all 6 tools.")
    elif old_ok:
        print(f"  -> Only old path works. No tool changes needed.")
    else:
        print(f"  -> NEITHER works. Investigate!")

    # Part C: What else is on Context?
    print("\n── Part C: Context Attribute Inventory ─────────────────")
    for key in ["ctx.request_id", "ctx.client_id", "ctx.session_id",
                "ctx.fastmcp", "ctx.session", "ctx.transport"]:
        val = data.get(key, "not checked")
        print(f"  {key:30s}  {val}")

    attrs = data.get("all_attributes", [])
    print(f"\n  All {len(attrs)} attributes:")
    for attr in attrs:
        print(f"    - {attr}")

    # Verdict
    print("\n── Verdict ─────────────────────────────────────────────")
    print("  Compare with your real codebase:")
    print("    server.py:16  -> from mcp.server.fastmcp import Context, FastMCP")
    print("    server.py:17  -> from mcp.types import ToolAnnotations")
    print("    server.py:115 -> ctx.request_context.lifespan_context['service']")
    print()
    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
