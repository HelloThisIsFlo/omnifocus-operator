"""Minimal FastMCP reproducer for the 'unknown progressToken' / stdio disconnect bug.

Four tools designed to isolate what triggers the bug in Claude Code CLI:

  emit_intermediates(n, delay_ms)
      Emits n intermediate `report_progress` calls. No final progress=total.
      delay_ms controls sleep between each emission (and before returning).

  emit_with_final(n, delay_ms)
      Same as above, PLUS a final `report_progress(progress=n, total=n)`
      immediately before returning. Tests the 307136e7 "final races response"
      theory in isolation.

  emit_only_final()
      Emits ONLY progress=1, total=1 right before return. No intermediates.
      If this single notification is rejected, the bug is purely 'client
      never registers progressTokens it sends', regardless of timing.

  echo()
      No progress emissions. Baseline — confirms the server works at all.

Each emission logs a timestamped line to stderr so the caller can correlate
client-side rejections with server-side send times.
"""

from __future__ import annotations

import asyncio
import sys
from datetime import datetime

from fastmcp import Context, FastMCP

mcp = FastMCP("progress-repro")


def _log(msg: str) -> None:
    ts = datetime.now().isoformat(timespec="microseconds")
    print(f"[{ts}] {msg}", file=sys.stderr, flush=True)


@mcp.tool()
async def emit_intermediates(n: int, ctx: Context, delay_ms: int = 0) -> str:
    """Emit n intermediate progress notifications, no final. Return 'ok'."""
    token = (
        ctx.request_context.meta.progressToken
        if ctx.request_context and ctx.request_context.meta
        else None
    )
    _log(f"emit_intermediates start n={n} delay_ms={delay_ms} token={token!r}")
    for i in range(n):
        _log(f"  emit i={i}/{n}")
        await ctx.report_progress(progress=i, total=n)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)
    _log(f"emit_intermediates return n={n}")
    return "ok"


@mcp.tool()
async def emit_with_final(n: int, ctx: Context, delay_ms: int = 0) -> str:
    """Emit n intermediates + a final progress=n,total=n. Return 'ok'."""
    token = (
        ctx.request_context.meta.progressToken
        if ctx.request_context and ctx.request_context.meta
        else None
    )
    _log(f"emit_with_final start n={n} delay_ms={delay_ms} token={token!r}")
    for i in range(n):
        _log(f"  emit i={i}/{n}")
        await ctx.report_progress(progress=i, total=n)
        if delay_ms > 0:
            await asyncio.sleep(delay_ms / 1000.0)
    _log(f"  emit FINAL progress={n}/{n}")
    await ctx.report_progress(progress=n, total=n)
    _log(f"emit_with_final return n={n}")
    return "ok"


@mcp.tool()
async def emit_only_final(ctx: Context) -> str:
    """Emit a single progress=1,total=1 right before return."""
    token = (
        ctx.request_context.meta.progressToken
        if ctx.request_context and ctx.request_context.meta
        else None
    )
    _log(f"emit_only_final start token={token!r}")
    await ctx.report_progress(progress=1, total=1)
    _log("emit_only_final return")
    return "ok"


@mcp.tool()
async def echo(ctx: Context) -> str:
    """Baseline: no progress notifications. Confirms tool call itself works."""
    _log("echo call")
    return "ok"


if __name__ == "__main__":
    _log("server starting")
    mcp.run()
