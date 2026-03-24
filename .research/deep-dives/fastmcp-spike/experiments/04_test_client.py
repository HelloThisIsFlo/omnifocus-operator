"""Experiment 04: Test Client — Client(server) vs Stream Plumbing

QUESTION: Can `async with Client(server) as client:` replace our
60-line _ClientSessionProxy and 30-line run_with_client?

WHAT THIS PROVES:
  Run the script. The output shows side-by-side what each pattern looks like
  and whether Client(server) handles our test scenarios correctly.

  After running, the guide skill will walk you through comparing this
  to your actual test infrastructure in conftest.py:439-481 and
  test_server.py:51-82.

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/04_test_client.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP, Context, Client


# ── Test server (mimics conftest.py's server fixture) ────────────────

class FakeService:
    """Stands in for OperatorService in tests."""
    def __init__(self) -> None:
        self.tasks = [
            {"id": "task-1", "name": "Buy groceries"},
            {"id": "task-2", "name": "Review PR"},
        ]
        self.call_count = 0

    def get_tasks(self) -> list[dict[str, str]]:
        self.call_count += 1
        return list(self.tasks)

    def add_task(self, name: str) -> dict[str, str]:
        self.call_count += 1
        task = {"id": f"task-{len(self.tasks) + 1}", "name": name}
        self.tasks.append(task)
        return task


def build_test_server(service: FakeService) -> FastMCP:
    """Mirrors conftest.py's server fixture: patched lifespan + _register_tools."""

    @asynccontextmanager
    async def patched_lifespan(app: FastMCP):  # type: ignore[type-arg]
        yield {"service": service}

    srv = FastMCP("test-server", lifespan=patched_lifespan)

    @srv.tool()
    async def get_tasks(ctx: Context) -> list[dict[str, str]]:
        svc: FakeService = ctx.lifespan_context["service"]
        return svc.get_tasks()

    @srv.tool()
    async def add_task(name: str, ctx: Context) -> dict[str, str]:
        svc: FakeService = ctx.lifespan_context["service"]
        return svc.add_task(name)

    @srv.tool()
    async def get_call_count(ctx: Context) -> int:
        svc: FakeService = ctx.lifespan_context["service"]
        return svc.call_count

    @srv.tool()
    async def fail_loudly() -> str:
        raise RuntimeError("Simulated startup error (like ErrorOperatorService)")

    return srv


# ── Tests ────────────────────────────────────────────────────────────

async def main() -> None:
    print("=" * 64)
    print("  EXPERIMENT 04: Test Client Simplification")
    print("=" * 64)

    # ── Test 1: Basic usage ──
    print("\n── Test 1: Basic Client(server) ────────────────────────")
    service = FakeService()
    server = build_test_server(service)

    async with Client(server) as client:
        tools = await client.list_tools()
        tool_names = [t.name for t in tools]
        print(f"  list_tools():  {tool_names}")

        result = await client.call_tool("get_tasks", {})
        print(f"  call_tool():   {result.data}")
        print(f"  Return type:   {type(result).__name__} (use .data for extracted value)")

    # ── Test 2: State persistence across calls ──
    print("\n── Test 2: State Persistence ───────────────────────────")
    service2 = FakeService()
    server2 = build_test_server(service2)

    async with Client(server2) as client:
        r1 = await client.call_tool("get_tasks", {})
        print(f"  Initial tasks:   {r1.data}")

        r2 = await client.call_tool("add_task", {"name": "New task"})
        print(f"  Added task:      {r2.data}")

        r3 = await client.call_tool("get_tasks", {})
        print(f"  After add:       {r3.data}")

        count = await client.call_tool("get_call_count", {})
        print(f"  Call count:      {count.data}  (should be 3)")

    # ── Test 3: Error handling ──
    print("\n── Test 3: Error Handling ──────────────────────────────")
    service3 = FakeService()
    server3 = build_test_server(service3)

    async with Client(server3) as client:
        try:
            result = await client.call_tool("fail_loudly", {})
            # call_tool may return a result with is_error=True instead of raising
            if hasattr(result, "is_error") and result.is_error:
                print(f"  Error result:  is_error=True")
                print(f"  Error text:    {result.content[0].text if result.content else '?'}")
            else:
                print(f"  No exception!  Result: {result.data}")
        except Exception as e:
            print(f"  Exception:     {type(e).__name__}: {e}")

    # ── Test 4: Session isolation ──
    print("\n── Test 4: Session Isolation ───────────────────────────")
    service4 = FakeService()
    server4 = build_test_server(service4)

    async with Client(server4) as client:
        await client.call_tool("add_task", {"name": "Session 1 task"})
        count1 = await client.call_tool("get_call_count", {})
        print(f"  Session 1 calls: {count1.data}")

    # Note: FakeService is shared (passed to build_test_server), so state
    # persists between sessions. This is the same as our current test infra
    # where InMemoryBridge outlives the MCP connection.
    async with Client(server4) as client:
        count2 = await client.call_tool("get_call_count", {})
        print(f"  Session 2 calls: {count2.data}  (state shared via FakeService)")

    # ── Comparison ──
    print("\n── Side-by-Side Comparison ─────────────────────────────")
    print("""
  CURRENT conftest.py (lines 439-481, 40+ lines):
  ┌──────────────────────────────────────────────────────────┐
  │ class _ClientSessionProxy:                               │
  │     async def _with_session(self, method, args, kwargs): │
  │         s2c_send, s2c_recv = anyio.create_memory_...     │
  │         c2s_send, c2s_recv = anyio.create_memory_...     │
  │         async with anyio.create_task_group() as tg:      │
  │             tg.start_soon(_run_server)                   │
  │             async with ClientSession(...) as session:    │
  │                 await session.initialize()               │
  │                 result = await getattr(session, ...)     │
  │                 tg.cancel_scope.cancel()                 │
  │         return result                                    │
  │     async def call_tool(self, *args, **kwargs):          │
  │     async def list_tools(self, *args, **kwargs):         │
  └──────────────────────────────────────────────────────────┘

  FASTMCP v3 (3 lines):
  ┌──────────────────────────────────────────────────────────┐
  │ async with Client(server) as client:                     │
  │     result = await client.call_tool("tool", {})          │
  └──────────────────────────────────────────────────────────┘
""")

    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
