"""Experiment 06: Context Access Pattern — Breaking Change Detection

QUESTION: What's the exact v3 API for accessing lifespan context?

CONTEXT:
  All 6 tools in server.py use this exact pattern:
    service: OperatorService = ctx.request_context.lifespan_context["service"]

  FastMCP v3 docs suggest:
    ctx.lifespan_context["service"]

  We need to know which works, both, or neither.

CRITICAL: This is the #1 breaking change risk. If neither path works,
every tool in the codebase breaks.

WHAT TO LOOK FOR:
- Which access pattern works?
- What other attributes does Context have?
- Is there a better pattern? (e.g., Depends() — see experiment 08)
- What about ctx.fastmcp, ctx.session, ctx.request_id?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/06_context_access.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP, Context, Client


@asynccontextmanager
async def lifespan(app: FastMCP):  # type: ignore[type-arg]
    yield {"service": {"name": "TestService"}, "version": "1.0"}


mcp = FastMCP("context-spike", lifespan=lifespan)


@mcp.tool()
async def inspect_context(ctx: Context) -> dict[str, Any]:
    """Inspect every attribute of the Context object."""
    results: dict[str, Any] = {}

    # --- Access pattern 1: current code (old) ---
    try:
        old = ctx.request_context.lifespan_context["service"]  # type: ignore[attr-defined]
        results["old_path"] = {"works": True, "value": old}
    except AttributeError as e:
        results["old_path"] = {"works": False, "error": str(e)}
    except Exception as e:
        results["old_path"] = {"works": False, "error": f"{type(e).__name__}: {e}"}

    # --- Access pattern 2: suspected v3 path ---
    try:
        new = ctx.lifespan_context["service"]
        results["new_path"] = {"works": True, "value": new}
    except AttributeError as e:
        results["new_path"] = {"works": False, "error": str(e)}
    except Exception as e:
        results["new_path"] = {"works": False, "error": f"{type(e).__name__}: {e}"}

    # --- All Context attributes ---
    ctx_attrs = [a for a in dir(ctx) if not a.startswith("_")]
    results["context_attributes"] = ctx_attrs

    # --- Explore specific useful attributes ---
    for attr in ["request_id", "client_id", "session_id", "fastmcp", "session", "transport"]:
        try:
            val = getattr(ctx, attr, "NOT FOUND")
            results[f"ctx.{attr}"] = str(val) if val != "NOT FOUND" else "NOT FOUND"
        except Exception as e:
            results[f"ctx.{attr}"] = f"ERROR: {e}"

    # --- Check if lifespan_context has ALL keys ---
    try:
        lc = ctx.lifespan_context
        results["lifespan_keys"] = list(lc.keys()) if hasattr(lc, "keys") else str(type(lc))
    except Exception as e:
        results["lifespan_keys"] = f"ERROR: {e}"

    return results


async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 06: Context Access Pattern")
    print("=" * 60)

    async with Client(mcp) as client:
        result = await client.call_tool("inspect_context", {})
        print(f"\n  Result type: {type(result).__name__}")

        # Pretty print results
        if isinstance(result, dict):
            for key, value in result.items():
                if key == "context_attributes":
                    print(f"\n  {key}:")
                    for attr in value:
                        print(f"    - {attr}")
                else:
                    print(f"\n  {key}: {value}")
        else:
            print(f"\n  Raw result: {result}")

    print("\n" + "=" * 60)
    print("VERDICT: Which access pattern to use?")
    print("=" * 60)
    print("""
  If old_path works:  Migration is a simple import swap, no tool changes needed.
  If new_path works:  Need to update all 6 tools (mechanical, but touching every tool).
  If BOTH work:       FastMCP v3 is backwards-compatible — migrate at your pace.
  If NEITHER works:   Something else changed — investigate ctx attributes.
    """)
    print("EXPERIMENT 06 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
