"""Experiment 01: Minimal Server — Basic Migration Shape

QUESTION: Does our exact pattern (lifespan → service injection → tool
registration → ToolAnnotations) work with FastMCP v3?

WHAT TO LOOK FOR:
- Does `from fastmcp import FastMCP, Context` work?
- Does `@asynccontextmanager` lifespan still work?
- Does `ToolAnnotations` from `mcp.types` still work?
- Does `server.run(transport="stdio")` work?
- Can tools access the lifespan context?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/01_minimal_server.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

# --- The key import change ---
from fastmcp import FastMCP, Context

# ToolAnnotations still comes from mcp.types (fastmcp includes mcp transitively)
from mcp.types import ToolAnnotations


# --- Lifespan: mirrors our real app_lifespan() ---
@asynccontextmanager
async def app_lifespan(app: FastMCP):  # type: ignore[type-arg]
    """Simulates our real lifespan that yields {"service": ...}."""
    print("[lifespan] Starting up...")
    fake_service = {"name": "FakeOperatorService", "status": "ready"}
    yield {"service": fake_service}
    print("[lifespan] Shutting down...")


# --- Server creation: mirrors our create_server() ---
def create_server() -> FastMCP:
    mcp = FastMCP("spike-server", lifespan=app_lifespan)

    @mcp.tool(
        annotations=ToolAnnotations(readOnlyHint=True, idempotentHint=True),
    )
    async def get_status(ctx: Context) -> dict[str, Any]:
        """Return the fake service status — tests lifespan context access."""
        # THIS is the critical line — does it still work in v3?
        # Current code uses: ctx.request_context.lifespan_context["service"]
        # v3 might use:      ctx.lifespan_context["service"]
        #
        # Try BOTH and see which works:
        service = None
        try:
            service = ctx.request_context.lifespan_context["service"]
            print(f"[OLD PATH] ctx.request_context.lifespan_context works: {service}")
        except Exception as e:
            print(f"[OLD PATH] ctx.request_context.lifespan_context FAILED: {e}")

        try:
            service = ctx.lifespan_context["service"]
            print(f"[NEW PATH] ctx.lifespan_context works: {service}")
        except Exception as e:
            print(f"[NEW PATH] ctx.lifespan_context FAILED: {e}")

        return {"service": service, "message": "Experiment 01 passed!"}

    @mcp.tool()
    async def echo(message: str) -> str:
        """Simple tool without context — tests basic registration."""
        return f"Echo: {message}"

    return mcp


# --- In-process test using FastMCP's Client ---
async def main() -> None:
    from fastmcp import Client

    server = create_server()

    print("=" * 60)
    print("EXPERIMENT 01: Minimal Server")
    print("=" * 60)

    async with Client(server) as client:
        # Test 1: List tools
        print("\n--- Test 1: List tools ---")
        tools = await client.list_tools()
        for tool in tools:
            print(f"  Tool: {tool.name} (annotations: {tool.annotations})")

        # Test 2: Call echo (no context)
        print("\n--- Test 2: Call echo ---")
        result = await client.call_tool("echo", {"message": "hello fastmcp"})
        print(f"  Result: {result}")

        # Test 3: Call get_status (uses lifespan context)
        print("\n--- Test 3: Call get_status (lifespan context access) ---")
        result = await client.call_tool("get_status", {})
        print(f"  Result: {result}")

    print("\n" + "=" * 60)
    print("EXPERIMENT 01 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
