"""Experiment 05: Middleware — What's Possible?

QUESTION: What middleware exists? What could we realistically use?

CONTEXT:
  We currently have _log_tool_call() in server.py that manually logs
  tool invocations with their arguments. Could middleware replace this?

  FastMCP v3 middleware hooks (general → specific):
  1. on_message — all MCP traffic
  2. on_request / on_notification — type-level
  3. on_call_tool, on_read_resource, etc. — operation-level

WHAT TO LOOK FOR:
- What built-in middleware exists?
- Can we write a timing middleware that replaces _log_tool_call()?
- Can middleware catch exceptions and return agent-friendly errors?
- How does middleware compose with lifespan?
- Performance overhead?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/05_middleware.py
"""

from __future__ import annotations

import asyncio
import time
from typing import Any

from fastmcp import FastMCP, Context, Client
from fastmcp.server.middleware import Middleware, MiddlewareContext


# ============================================================
# Custom Middleware: Tool Call Timer (replacement for _log_tool_call)
# ============================================================
class ToolTimingMiddleware(Middleware):
    """Logs every tool call with its arguments and duration.

    This is what we'd use to replace the manual _log_tool_call()
    in server.py.
    """

    def __init__(self) -> None:
        self.call_log: list[dict[str, Any]] = []

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        start = time.monotonic()
        tool_name = context.params.get("name", "unknown") if hasattr(context, "params") and isinstance(context.params, dict) else "unknown"
        print(f"  [MIDDLEWARE] >>> Tool call: {tool_name}")
        print(f"  [MIDDLEWARE]     Params: {context.params}")

        try:
            result = await call_next(context)
            elapsed = (time.monotonic() - start) * 1000
            print(f"  [MIDDLEWARE] <<< Tool call: {tool_name} ({elapsed:.1f}ms)")
            self.call_log.append({
                "tool": tool_name,
                "elapsed_ms": round(elapsed, 1),
                "success": True,
            })
            return result
        except Exception as e:
            elapsed = (time.monotonic() - start) * 1000
            print(f"  [MIDDLEWARE] !!! Tool call FAILED: {tool_name} ({elapsed:.1f}ms) — {e}")
            self.call_log.append({
                "tool": tool_name,
                "elapsed_ms": round(elapsed, 1),
                "success": False,
                "error": str(e),
            })
            raise


# ============================================================
# Custom Middleware: Error Handler (agent-friendly errors)
# ============================================================
class AgentFriendlyErrorMiddleware(Middleware):
    """Catches exceptions and returns structured error responses
    instead of raw tracebacks.

    Could replace per-tool try/except patterns.
    """

    async def on_call_tool(self, context: MiddlewareContext, call_next: Any) -> Any:
        try:
            return await call_next(context)
        except ValueError as e:
            print(f"  [ERROR MW] Caught ValueError, returning friendly message")
            # Can we return a modified result here? Let's see...
            raise  # For now, re-raise and see what happens


# ============================================================
# Server with middleware
# ============================================================
def create_server() -> tuple[FastMCP, ToolTimingMiddleware]:
    mcp = FastMCP("middleware-spike")

    timing = ToolTimingMiddleware()
    mcp.add_middleware(timing)

    @mcp.tool()
    async def fast_tool() -> str:
        """Returns immediately."""
        return "fast!"

    @mcp.tool()
    async def slow_tool() -> str:
        """Simulates a slow operation."""
        await asyncio.sleep(0.1)
        return "slow but done!"

    @mcp.tool()
    async def failing_tool() -> str:
        """Raises an error."""
        raise ValueError("Something went wrong")

    return mcp, timing


async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 05: Middleware")
    print("=" * 60)

    # Test 1: Timing middleware
    print("\n--- Test 1: Tool timing middleware ---")
    server, timing = create_server()
    async with Client(server) as client:
        await client.call_tool("fast_tool", {})
        await client.call_tool("slow_tool", {})

    print(f"\n  Call log: {timing.call_log}")

    # Test 2: Error in middleware context
    print("\n--- Test 2: Error handling through middleware ---")
    server2, timing2 = create_server()
    async with Client(server2) as client:
        try:
            await client.call_tool("failing_tool", {})
        except Exception as e:
            print(f"  Client received: {type(e).__name__}: {e}")
    print(f"  Call log: {timing2.call_log}")

    # Test 3: Explore built-in middleware
    print("\n--- Test 3: Exploring available built-in middleware ---")
    try:
        from fastmcp.server import middleware as mw_module
        available = [name for name in dir(mw_module) if not name.startswith("_")]
        print(f"  Available in fastmcp.server.middleware: {available}")
    except Exception as e:
        print(f"  Could not inspect middleware module: {e}")

    # Try to import specific built-in middleware mentioned in docs
    for name in ["TimingMiddleware", "LoggingMiddleware", "CachingMiddleware",
                 "RateLimitMiddleware", "ErrorHandlerMiddleware"]:
        try:
            cls = getattr(mw_module, name, None)
            if cls:
                print(f"  Found: {name}")
            else:
                print(f"  Not found: {name}")
        except Exception:
            print(f"  Error checking: {name}")

    # Test 4: MiddlewareContext inspection
    print("\n--- Test 4: What's in MiddlewareContext? ---")
    print(f"  MiddlewareContext attributes: {[a for a in dir(MiddlewareContext) if not a.startswith('_')]}")

    print("\n" + "=" * 60)
    print("EXPERIMENT 05 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
