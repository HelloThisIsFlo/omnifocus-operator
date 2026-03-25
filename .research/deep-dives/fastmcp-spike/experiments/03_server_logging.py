"""Experiment 03: stderr Hijacking — Is stderr safe under stdio transport?

QUESTION: Does stdio transport hijack sys.stderr?
Our __main__.py comment says "stdio_server() hijacks stderr" — is that true?
Test with BOTH the old mcp SDK and FastMCP v3 to compare.

USAGE:
  # FastMCP v3
  uv run python experiments/03_server_logging.py new

  # Old mcp SDK (what our current server uses)
  uv run python experiments/03_server_logging.py old

  Then connect via MCP Inspector or setup_mcp.py.

GUIDED WALKTHROUGH:
  1. Start with "old", connect, call both tools. Note results.
  2. Restart with "new", connect, call both tools. Compare.
  3. If both show stderr is safe, the __main__.py comment was wrong all along.
"""

from __future__ import annotations

import logging
import sys

# ── SDK selection based on CLI arg ───────────────────────────────────

sdk_arg = sys.argv[1] if len(sys.argv) > 1 else "new"

if sdk_arg == "old":
    from mcp.server.fastmcp import Context, FastMCP
    SDK_LABEL = "old mcp SDK (mcp.server.fastmcp)"
elif sdk_arg == "new":
    from fastmcp import FastMCP, Context
    SDK_LABEL = "FastMCP v3 (fastmcp)"
else:
    print(f"Usage: {sys.argv[0]} [old|new]")
    print("  old = mcp.server.fastmcp (current project)")
    print("  new = fastmcp (FastMCP v3)")
    sys.exit(1)

# ── Server ───────────────────────────────────────────────────────────

mcp = FastMCP(f"stderr-spike-{sdk_arg}")


@mcp.tool()
async def check_stderr(ctx: Context) -> dict[str, str]:  # type: ignore[type-arg]
    """Check if stderr is the original or hijacked during a live tool call."""
    is_original = sys.stderr is sys.__stderr__

    try:
        sys.stderr.write(f"STDERR TEST: direct write during tool call ({SDK_LABEL})\n")
        sys.stderr.flush()
        write_result = "succeeded"
    except Exception as e:
        write_result = f"failed: {type(e).__name__}: {e}"

    return {
        "sdk": SDK_LABEL,
        "stderr_type": type(sys.stderr).__name__,
        "stderr_is_original": str(is_original),
        "stderr_repr": repr(sys.stderr)[:200],
        "__stderr___repr": repr(sys.__stderr__)[:200],
        "direct_write": write_result,
        "verdict": "stderr is SAFE — not hijacked" if is_original else "stderr is HIJACKED",
    }


@mcp.tool()
async def check_stderr_with_logging(ctx: Context) -> dict[str, str]:  # type: ignore[type-arg]
    """Test StreamHandler(stderr) in a real tool call — the production pattern.

    Uses our chosen format: time + padded level + bracketed name + message.
    """
    test_logger = logging.getLogger(f"omnifocus_operator.test_{sdk_arg}")
    test_logger.setLevel(logging.DEBUG)
    test_logger.propagate = False

    handler = logging.StreamHandler(sys.stderr)
    handler.setFormatter(
        logging.Formatter(
            "%(asctime)s %(levelname)-8s [%(name)s] %(message)s", datefmt="%H:%M:%S"
        )
    )
    test_logger.addHandler(handler)

    test_logger.debug(f"Debug: tag cache miss for 'Work' ({SDK_LABEL})")
    test_logger.info(f"Info: OperatorService.add_task processing ({SDK_LABEL})")
    test_logger.warning(f"Warning: task is completed, editing anyway ({SDK_LABEL})")
    test_logger.error(f"Error: bridge timeout, retrying ({SDK_LABEL})")

    test_logger.removeHandler(handler)

    return {
        "sdk": SDK_LABEL,
        "status": "all 4 log levels written to stderr via StreamHandler",
        "verdict": "if you see this response, stderr logging did NOT corrupt the protocol",
        "check": "look at your client log page — do the 4 messages appear?",
    }


if __name__ == "__main__":
    mcp.run(transport="stdio")
