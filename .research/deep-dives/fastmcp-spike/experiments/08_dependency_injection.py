"""Experiment 08: Dependency Injection — Depends() vs Lifespan Pattern

QUESTION: Could Depends() replace our lifespan-based service injection?
Is it cleaner? More testable?

WHAT THIS PROVES:
  Run the script. It shows both patterns working side by side and compares
  ergonomics. The guide skill will walk you through whether this is worth
  adopting.

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/08_dependency_injection.py
"""

from __future__ import annotations

import asyncio
from contextlib import asynccontextmanager
from typing import Any

from fastmcp import FastMCP, Context, Client


# ── Fake service ─────────────────────────────────────────────────────

class FakeService:
    def __init__(self, name: str) -> None:
        self.name = name
        self.call_count = 0

    def get_tasks(self) -> list[dict[str, str]]:
        self.call_count += 1
        return [{"id": "1", "name": "Task A"}, {"id": "2", "name": "Task B"}]


# ── Try importing Depends ────────────────────────────────────────────

HAS_DEPENDS = False
Depends: Any = None
try:
    from fastmcp.dependencies import Depends as _Depends
    Depends = _Depends
    HAS_DEPENDS = True
except ImportError:
    try:
        from fastmcp import Depends as _Depends
        Depends = _Depends
        HAS_DEPENDS = True
    except ImportError:
        pass


# ── Build servers ────────────────────────────────────────────────────

@asynccontextmanager
async def lifespan(app: FastMCP):  # type: ignore[type-arg]
    yield {"service": FakeService("from-lifespan")}


async def main() -> None:
    print("=" * 64)
    print("  EXPERIMENT 08: Dependency Injection")
    print("=" * 64)

    print(f"\n  Depends() available: {HAS_DEPENDS}")

    if not HAS_DEPENDS:
        print("  Cannot test — Depends() not found in fastmcp")
        print("  This means the lifespan pattern is the only option.")
        print("=" * 64)
        return

    # ── Pattern A: Current (lifespan extraction) ──
    print("\n── Pattern A: Lifespan Extraction (current) ────────────")

    mcp_a = FastMCP("pattern-a", lifespan=lifespan)

    @mcp_a.tool()
    async def get_tasks_lifespan(ctx: Context) -> list[dict[str, str]]:
        service: FakeService = ctx.lifespan_context["service"]
        return service.get_tasks()

    async with Client(mcp_a) as client:
        result = await client.call_tool("get_tasks_lifespan", {})
        print(f"  Result: {result.data}")

    # ── Pattern B: Depends() with ctx parameter ──
    print("\n── Pattern B: Depends(get_service) where get_service takes ctx ──")

    mcp_b = FastMCP("pattern-b", lifespan=lifespan)

    def get_service_with_ctx(ctx: Context) -> FakeService:
        """Dependency that needs Context — does Depends() inject it?"""
        return ctx.lifespan_context["service"]

    @mcp_b.tool()
    async def get_tasks_depends_ctx(service: FakeService = Depends(get_service_with_ctx)) -> list[dict[str, str]]:
        return service.get_tasks()

    async with Client(mcp_b) as client:
        try:
            result = await client.call_tool("get_tasks_depends_ctx", {})
            print(f"  Result: {result.data}")
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")
            print(f"  -> Depends() does NOT auto-inject Context into dependency functions!")

    # ── Pattern C: Depends() without ctx (parameterless factory) ──
    print("\n── Pattern C: Depends() with parameterless factory ─────")

    # This is the pattern from the docs — no ctx in the dependency
    shared_service = FakeService("shared-instance")

    mcp_c = FastMCP("pattern-c")

    def get_shared_service() -> FakeService:
        """Dependency without ctx — uses closure instead."""
        return shared_service

    @mcp_c.tool()
    async def get_tasks_depends_closure(service: FakeService = Depends(get_shared_service)) -> list[dict[str, str]]:
        return service.get_tasks()

    async with Client(mcp_c) as client:
        try:
            result = await client.call_tool("get_tasks_depends_closure", {})
            print(f"  Result: {result.data}")
            print(f"  -> Parameterless Depends() works, but requires a closure/global")
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    # ── Pattern D: ctx + Depends() together ──
    print("\n── Pattern D: Can a tool use BOTH ctx and Depends()? ───")

    mcp_d = FastMCP("pattern-d")

    @mcp_d.tool()
    async def mixed(ctx: Context, service: FakeService = Depends(get_shared_service)) -> str:
        await ctx.info(f"Using service: {service.name}")
        tasks = service.get_tasks()
        return f"Got {len(tasks)} tasks via Depends + logged via ctx"

    async with Client(mcp_d) as client:
        try:
            result = await client.call_tool("mixed", {})
            print(f"  Result: {result.data}")
        except Exception as e:
            print(f"  FAILED: {type(e).__name__}: {e}")

    # ── Ergonomics comparison ──
    print("\n── Ergonomics Comparison ───────────────────────────────")
    print("""
  Pattern A — Lifespan extraction (current, 1 line per tool):
  ┌──────────────────────────────────────────────────────────┐
  │ @mcp.tool()                                              │
  │ async def get_all(ctx: Context) -> AllEntities:          │
  │     service = ctx.lifespan_context["service"]            │
  │     return await service.get_all()                       │
  └──────────────────────────────────────────────────────────┘

  Pattern C — Depends() with closure (no ctx in dependency):
  ┌──────────────────────────────────────────────────────────┐
  │ # Requires closure or global — can't access lifespan!    │
  │ def get_service() -> OperatorService:                    │
  │     return _global_service  # or closure capture         │
  │                                                          │
  │ @mcp.tool()                                              │
  │ async def get_all(                                       │
  │     svc: OperatorService = Depends(get_service),         │
  │ ) -> AllEntities:                                        │
  │     return await svc.get_all()                           │
  └──────────────────────────────────────────────────────────┘

  Key finding: Depends() does NOT auto-inject Context.
  So you can't use Depends() to wrap lifespan access —
  you'd need a global/closure, which defeats the purpose.

  Verdict: Lifespan extraction (Pattern A) is actually simpler
  for our use case. Depends() is better for stateless dependencies
  (config, HTTP clients) than for lifespan-scoped services.
""")

    print("=" * 64)


if __name__ == "__main__":
    asyncio.run(main())
