"""Experiment 08: Dependency Injection — Depends() vs Lifespan

QUESTION: Could Depends() replace our lifespan-based service injection?

CONTEXT:
  Current pattern (every tool):
    service = ctx.request_context.lifespan_context["service"]

  Alternative with Depends():
    async def get_service(ctx: Context) -> OperatorService:
        return ctx.lifespan_context["service"]

    @mcp.tool()
    async def get_all(service: OperatorService = Depends(get_service)):
        ...

  The question is: is this cleaner? More testable? Worth the change?

WHAT TO LOOK FOR:
- Does Depends() work with lifespan context?
- Can the dependency function access Context?
- How does it affect testing? (Can you override dependencies?)
- Is it just syntactic sugar, or does it enable new patterns?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/08_dependency_injection.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP, Context, Client


# --- Try to import Depends ---
try:
    from fastmcp.dependencies import Depends
    HAS_DEPENDS = True
except ImportError:
    try:
        from fastmcp import Depends
        HAS_DEPENDS = True
    except ImportError:
        HAS_DEPENDS = False


# --- Fake service ---
class FakeService:
    def __init__(self, name: str) -> None:
        self.name = name
        self.call_count = 0

    def get_tasks(self) -> list[dict[str, str]]:
        self.call_count += 1
        return [{"id": "1", "name": "Task A"}, {"id": "2", "name": "Task B"}]


@asynccontextmanager
async def lifespan(app: FastMCP):  # type: ignore[type-arg]
    yield {"service": FakeService("from-lifespan")}


def create_server_with_depends() -> FastMCP | None:
    """Server using Depends() pattern."""
    if not HAS_DEPENDS:
        return None

    mcp = FastMCP("depends-spike", lifespan=lifespan)

    # Dependency provider — extracts service from lifespan context
    def get_service(ctx: Context) -> FakeService:
        return ctx.lifespan_context["service"]

    @mcp.tool()
    async def get_tasks_v1(ctx: Context) -> list[dict[str, str]]:
        """OLD pattern: manual extraction."""
        service = ctx.lifespan_context["service"]
        return service.get_tasks()

    @mcp.tool()
    async def get_tasks_v2(service: FakeService = Depends(get_service)) -> list[dict[str, str]]:
        """NEW pattern: dependency injection."""
        return service.get_tasks()

    @mcp.tool()
    async def get_call_count(service: FakeService = Depends(get_service)) -> int:
        """Both tools share the same service instance?"""
        return service.call_count

    return mcp


def create_server_without_depends() -> FastMCP:
    """Fallback if Depends() isn't available."""
    mcp = FastMCP("no-depends-spike", lifespan=lifespan)

    @mcp.tool()
    async def get_tasks(ctx: Context) -> list[dict[str, str]]:
        service: FakeService = ctx.lifespan_context["service"]
        return service.get_tasks()

    return mcp


async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 08: Dependency Injection")
    print("=" * 60)

    print(f"\n  Depends() available: {HAS_DEPENDS}")

    if HAS_DEPENDS:
        server = create_server_with_depends()
        assert server is not None

        async with Client(server) as client:
            # Test 1: Old pattern
            print("\n--- Test 1: Old pattern (ctx.lifespan_context) ---")
            result = await client.call_tool("get_tasks_v1", {})
            print(f"  Result: {result}")

            # Test 2: New pattern (Depends)
            print("\n--- Test 2: New pattern (Depends) ---")
            result = await client.call_tool("get_tasks_v2", {})
            print(f"  Result: {result}")

            # Test 3: Shared instance?
            print("\n--- Test 3: Do both patterns share the same service? ---")
            count = await client.call_tool("get_call_count", {})
            print(f"  Call count after 2 tool calls: {count}")
            print(f"  (Should be 2 if shared, 1 if separate instances)")

        # Test 4: Testing implications
        print("\n--- Test 4: Testing with Depends ---")
        print("""
  With Depends(), testing could look like:

    # Override the dependency for testing:
    fake_service = FakeService("test-override")
    # ... but how? Need to check if FastMCP supports dependency overrides.
        """)

    else:
        print("\n  Depends() not available — falling back")
        server = create_server_without_depends()
        async with Client(server) as client:
            result = await client.call_tool("get_tasks", {})
            print(f"  Result: {result}")

    # Ergonomics comparison
    print("\n" + "=" * 60)
    print("ERGONOMICS COMPARISON")
    print("=" * 60)
    print("""
  CURRENT (every tool, 1 line each):
    service: OperatorService = ctx.request_context.lifespan_context["service"]

  DEPENDS (if it works):
    # Define once:
    def get_service(ctx: Context) -> OperatorService:
        return ctx.lifespan_context["service"]

    # Then each tool:
    async def get_all(service: OperatorService = Depends(get_service)):
        ...  # No ctx needed unless logging!

  VERDICT: Is the indirection worth it?
  - Pro: Tools don't need to know about lifespan context
  - Pro: Dependency is typed (IDE autocomplete on service)
  - Con: One more abstraction layer
  - Con: How do you test/override?
    """)

    print("EXPERIMENT 08 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
