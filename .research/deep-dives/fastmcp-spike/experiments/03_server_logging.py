"""Experiment 03: Server-Side Logging — stderr, get_logger(), FileHandler

QUESTION: Is stderr still hijacked under stdio transport?
What's fastmcp.utilities.logging.get_logger()? Can we have dual logging?

CONTEXT:
  Our current workaround: FileHandler -> ~/Library/Logs/omnifocus-operator.log
  because stdio_server() hijacks stderr. The question is whether FastMCP v3
  changes this, and what the recommended server-side logging story is.

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/03_server_logging.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio

  Option B — Claude Code:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 03
    2. Restart Claude Code (or reload MCP servers)
    3. Ask Claude to call the tools
    4. When done: uv run python .../setup_mcp.py remove

GUIDED WALKTHROUGH:
  1. Call `test_dual_logging` — this writes to BOTH protocol and file.
     - Check /tmp/fastmcp-spike-server.log — is the file output there?
     - Check your client — did the ctx.info() messages arrive?
     - Both channels should work independently.

  2. Call `test_stderr_write` — attempts to write directly to stderr.
     - If stdio transport hijacks stderr, this might corrupt the protocol.
     - Or it might be silently swallowed.
     - Or FastMCP v3 might have fixed this.
     - What happened?

  3. Call `test_get_logger` — uses fastmcp.utilities.logging.get_logger().
     - Check /tmp/fastmcp-spike-server.log for output.
     - Is get_logger() just a wrapper around logging.getLogger()?
     - Does it add any special handling?

  4. After running all tools, check the log file:
     cat /tmp/fastmcp-spike-server.log
"""

from __future__ import annotations

import logging
import sys

from fastmcp import FastMCP, Context

# ── Set up file logging (like our current workaround) ────────────────

LOG_FILE = "/tmp/fastmcp-spike-server.log"

file_logger = logging.getLogger("spike_server")
file_logger.setLevel(logging.DEBUG)
file_logger.propagate = False
handler = logging.FileHandler(LOG_FILE, mode="w")  # overwrite each run
handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
file_logger.addHandler(handler)

file_logger.info("=== Server starting ===")
file_logger.info(f"Log file: {LOG_FILE}")
file_logger.info(f"stderr type at startup: {type(sys.stderr).__name__}")
file_logger.info(f"stderr is __stderr__: {sys.stderr is sys.__stderr__}")

# ── Try get_logger() ─────────────────────────────────────────────────

try:
    from fastmcp.utilities.logging import get_logger
    fm_logger = get_logger("spike_fastmcp")
    file_logger.info(f"get_logger() returned: {type(fm_logger).__name__}, name={fm_logger.name}")
    HAS_GET_LOGGER = True
except ImportError as e:
    file_logger.warning(f"get_logger() import failed: {e}")
    fm_logger = None
    HAS_GET_LOGGER = False


# ── Server ───────────────────────────────────────────────────────────

mcp = FastMCP("server-logging-spike")


@mcp.tool()
async def test_dual_logging(ctx: Context) -> dict[str, str]:
    """Writes to BOTH protocol (ctx.info) and file (FileHandler)."""

    # Protocol logging — goes to client
    await ctx.info("PROTOCOL: This message should appear in your client")
    await ctx.warning("PROTOCOL: This warning should also appear in your client")

    # File logging — goes to /tmp/fastmcp-spike-server.log
    file_logger.info("FILE: This message should appear in the log file")
    file_logger.warning("FILE: This warning should appear in the log file")

    return {
        "status": "dual logging executed",
        "log_file": LOG_FILE,
        "instruction": "Check both: your client for protocol messages, and the log file for file messages",
    }


@mcp.tool()
async def test_stderr_write(ctx: Context) -> dict[str, str]:
    """Attempts to write directly to stderr under stdio transport.

    This is the key question: does stdio transport still hijack stderr?
    """
    file_logger.info(f"stderr type during tool call: {type(sys.stderr).__name__}")
    file_logger.info(f"stderr is __stderr__: {sys.stderr is sys.__stderr__}")

    try:
        sys.stderr.write("STDERR: Direct write to stderr\n")
        sys.stderr.flush()
        result = "stderr write succeeded (no exception)"
    except Exception as e:
        result = f"stderr write failed: {type(e).__name__}: {e}"

    file_logger.info(f"stderr write result: {result}")

    await ctx.info(f"stderr type: {type(sys.stderr).__name__}")
    await ctx.info(f"stderr write result: {result}")

    return {
        "stderr_type": type(sys.stderr).__name__,
        "stderr_is_original": sys.stderr is sys.__stderr__,
        "write_result": result,
        "instruction": "If stderr is hijacked, the write might corrupt the MCP protocol stream",
    }


@mcp.tool()
async def test_get_logger(ctx: Context) -> dict[str, str]:
    """Tests fastmcp.utilities.logging.get_logger() behavior."""
    if not HAS_GET_LOGGER or fm_logger is None:
        return {"status": "get_logger() not available", "error": "import failed"}

    # Write through get_logger()
    fm_logger.info("GET_LOGGER: Info message from get_logger()")
    fm_logger.warning("GET_LOGGER: Warning message from get_logger()")
    fm_logger.debug("GET_LOGGER: Debug message from get_logger()")

    # Also log to file for comparison
    file_logger.info("FILE: Logged alongside get_logger() test")

    # Check get_logger() configuration
    info = {
        "status": "get_logger() available",
        "logger_name": fm_logger.name,
        "logger_level": logging.getLevelName(fm_logger.level),
        "logger_handlers": [type(h).__name__ for h in fm_logger.handlers],
        "logger_effective_level": logging.getLevelName(fm_logger.getEffectiveLevel()),
        "instruction": f"Check {LOG_FILE} for output from all loggers",
    }

    await ctx.info(f"get_logger() config: {fm_logger.name}, level={logging.getLevelName(fm_logger.level)}")

    return info


if __name__ == "__main__":
    file_logger.info("Starting MCP server on stdio transport...")
    mcp.run(transport="stdio")
