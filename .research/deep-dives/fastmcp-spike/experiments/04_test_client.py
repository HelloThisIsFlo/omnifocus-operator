"""Experiment 04: Test Client Simplification

QUESTION: Can `async with Client(server) as client:` replace our
60-line anyio stream plumbing in conftest.py?

CONTEXT:
  Our current test infra uses:
  - `_ClientSessionProxy` (conftest.py:439-481) — 40 lines
  - `run_with_client` (test_server.py:51-82) — 30 lines
  - Manual anyio memory streams, task groups, cancellation

  FastMCP's Client should collapse this to ~3 lines.

WHAT TO LOOK FOR:
- Does Client(server) run the lifespan?
- Does call_tool() return the same shape as ClientSession.call_tool()?
- Does list_tools() work?
- How are errors handled? (RuntimeError from ErrorOperatorService)
- Can we call multiple tools sequentially (state persists)?
- What about concurrent tool calls?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/04_test_client.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP, Context, Client


# --- Build a server that mimics our test setup ---
def build_test_server() -> FastMCP:
    """Mirrors how conftest.py builds a test server with patched lifespan."""

    # Fake service with mutable state (like InMemoryBridge)
    fake_service = {
        "tasks": [
            {"id": "task-1", "name": "Buy groceries"},
            {"id": "task-2", "name": "Review PR"},
        ],
        "call_count": 0,
    }

    @asynccontextmanager
    async def patched_lifespan(app: FastMCP):  # type: ignore[type-arg]
        print("  [lifespan] Starting (test mode)")
        yield {"service": fake_service}
        print("  [lifespan] Shutting down (test mode)")

    mcp = FastMCP("test-server", lifespan=patched_lifespan)

    @mcp.tool()
    async def get_tasks(ctx: Context) -> list[dict[str, str]]:
        svc = ctx.lifespan_context["service"]
        svc["call_count"] += 1
        return svc["tasks"]

    @mcp.tool()
    async def add_task(name: str, ctx: Context) -> dict[str, str]:
        svc = ctx.lifespan_context["service"]
        new_task = {"id": f"task-{len(svc['tasks']) + 1}", "name": name}
        svc["tasks"].append(new_task)
        svc["call_count"] += 1
        return new_task

    @mcp.tool()
    async def get_call_count(ctx: Context) -> int:
        svc = ctx.lifespan_context["service"]
        return svc["call_count"]

    @mcp.tool()
    async def fail_loudly() -> str:
        """Tool that raises — how does Client handle it?"""
        raise RuntimeError("Simulated startup error (like ErrorOperatorService)")

    return mcp


async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 04: Test Client Simplification")
    print("=" * 60)

    server = build_test_server()

    # Test 1: Basic Client usage
    print("\n--- Test 1: Basic Client(server) usage ---")
    async with Client(server) as client:
        tools = await client.list_tools()
        print(f"  Tools found: {[t.name for t in tools]}")

        result = await client.call_tool("get_tasks", {})
        print(f"  get_tasks result type: {type(result).__name__}")
        print(f"  get_tasks result: {result}")

    # Test 2: State persists across calls within same session
    print("\n--- Test 2: State persistence across calls ---")
    async with Client(server) as client:
        r1 = await client.call_tool("get_tasks", {})
        print(f"  Initial tasks: {r1}")

        r2 = await client.call_tool("add_task", {"name": "New task"})
        print(f"  Added: {r2}")

        r3 = await client.call_tool("get_tasks", {})
        print(f"  After add: {r3}")

        count = await client.call_tool("get_call_count", {})
        print(f"  Total calls in this session: {count}")

    # Test 3: Fresh session = fresh lifespan?
    print("\n--- Test 3: Does each Client session get a fresh lifespan? ---")
    async with Client(server) as client:
        result = await client.call_tool("get_call_count", {})
        print(f"  Call count in new session: {result}")
        print(f"  (If 0, lifespan resets per session — if >0, state leaks)")

    # Test 4: Error handling
    print("\n--- Test 4: Error handling (tool raises RuntimeError) ---")
    async with Client(server) as client:
        try:
            result = await client.call_tool("fail_loudly", {})
            print(f"  Result (no exception?): {result}")
        except Exception as e:
            print(f"  Exception type: {type(e).__name__}")
            print(f"  Exception message: {e}")

    # Test 5: Compare with what we'd REPLACE
    print("\n--- Test 5: Side-by-side comparison ---")
    print("""
  CURRENT (conftest.py, ~40 lines):
    s2c_send, s2c_recv = anyio.create_memory_object_stream[SessionMessage](0)
    c2s_send, c2s_recv = anyio.create_memory_object_stream[SessionMessage](0)
    async with anyio.create_task_group() as tg:
        tg.start_soon(lambda: server._mcp_server.run(...))
        async with ClientSession(s2c_recv, c2s_send) as session:
            await session.initialize()
            result = await session.call_tool(...)
            tg.cancel_scope.cancel()

  FASTMCP v3 (~3 lines):
    async with Client(server) as client:
        result = await client.call_tool(...)
    """)

    print("=" * 60)
    print("EXPERIMENT 04 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
