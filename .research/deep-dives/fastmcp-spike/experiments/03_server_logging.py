"""Experiment 03: Server-Side Logging — get_logger(), stderr, FileHandler

QUESTION: What's the right server-side logging story?
Is stderr still hijacked? What's fastmcp.utilities.logging.get_logger()?

CONTEXT:
  Our current workaround: FileHandler → ~/Library/Logs/omnifocus-operator.log
  because stdio_server() hijacks stderr.

  FastMCP docs say:
    "For standard server-side logging (e.g., writing to files, console),
     use fastmcp.utilities.logging.get_logger() or Python's built-in
     logging module."

WHAT TO LOOK FOR:
- What does get_logger() return? How is it different from logging.getLogger()?
- Is stderr still hijacked under stdio transport?
- Can we use BOTH protocol logging (ctx.info) AND file logging simultaneously?
- What logger names does FastMCP use internally?
- When to use which: ctx.info vs get_logger vs FileHandler?

RUN: uv run python .research/deep-dives/fastmcp-spike/experiments/03_server_logging.py
"""

from __future__ import annotations

import asyncio
import logging
import sys
import tempfile
from pathlib import Path

from fastmcp import FastMCP, Context, Client


# --- Explore get_logger() ---
def explore_get_logger() -> None:
    print("--- Part A: Exploring get_logger() ---")

    try:
        from fastmcp.utilities.logging import get_logger
        logger = get_logger("spike_test")
        print(f"  get_logger() returned: {type(logger).__name__}")
        print(f"  Logger name: {logger.name}")
        print(f"  Logger level: {logger.level} ({logging.getLevelName(logger.level)})")
        print(f"  Logger handlers: {logger.handlers}")
        print(f"  Logger effective level: {logger.getEffectiveLevel()}")

        # Compare with standard logging
        std_logger = logging.getLogger("spike_test_std")
        print(f"\n  Standard logger type: {type(std_logger).__name__}")
        print(f"  Same type? {type(logger) == type(std_logger)}")

        # Try logging through it
        logger.info("Test message from get_logger()")
        print("  get_logger().info() called — check if it appeared above")

    except ImportError as e:
        print(f"  get_logger() import FAILED: {e}")
        print("  Trying alternative import paths...")
        # Maybe it's elsewhere?
        try:
            import fastmcp.utilities
            print(f"  fastmcp.utilities contents: {dir(fastmcp.utilities)}")
        except Exception as e2:
            print(f"  fastmcp.utilities also failed: {e2}")


# --- Test what happens to stderr ---
def explore_stderr() -> None:
    print("\n--- Part B: stderr behavior (outside MCP context) ---")
    print(f"  sys.stderr type: {type(sys.stderr).__name__}")
    print(f"  sys.stderr is sys.__stderr__: {sys.stderr is sys.__stderr__}")

    # Write directly to stderr
    try:
        sys.stderr.write("  [STDERR DIRECT] This is a test write to stderr\n")
        sys.stderr.flush()
        print("  Direct stderr write succeeded")
    except Exception as e:
        print(f"  Direct stderr write FAILED: {e}")


# --- Test file logging alongside protocol logging ---
async def explore_dual_logging() -> None:
    print("\n--- Part C: Dual logging (protocol + file) ---")

    log_file = Path(tempfile.mktemp(suffix=".log", prefix="fastmcp_spike_"))
    print(f"  Log file: {log_file}")

    # Set up file handler (like our current workaround)
    file_logger = logging.getLogger("spike_server")
    file_logger.setLevel(logging.DEBUG)
    file_logger.propagate = False
    handler = logging.FileHandler(str(log_file))
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    file_logger.addHandler(handler)

    mcp = FastMCP("dual-logging-spike")

    @mcp.tool()
    async def dual_log(ctx: Context) -> dict[str, str]:
        """Tool that logs to BOTH protocol and file."""
        # Protocol logging (client-facing)
        await ctx.info("Protocol: this goes to the client")
        await ctx.warning("Protocol: warning for the client")

        # File logging (server-side)
        file_logger.info("File: this goes to the log file")
        file_logger.warning("File: warning in the log file")

        return {"status": "dual logging executed"}

    received_logs: list[str] = []

    def log_handler(level: str, message: str, logger_name: str | None = None) -> None:
        received_logs.append(f"[{level}] {message}")

    async with Client(mcp, log_handler=log_handler) as client:
        result = await client.call_tool("dual_log", {})
        print(f"  Tool result: {result}")
        print(f"  Protocol logs received by client: {received_logs}")

    # Check file
    file_content = log_file.read_text()
    print(f"  File log content:\n{file_content}")
    print(f"  Both channels worked? Protocol={len(received_logs) > 0}, File={len(file_content) > 0}")

    # Cleanup
    file_logger.removeHandler(handler)
    handler.close()
    log_file.unlink(missing_ok=True)


# --- Explore FastMCP's internal loggers ---
def explore_fastmcp_loggers() -> None:
    print("\n--- Part D: FastMCP internal logger names ---")

    # Check what loggers FastMCP creates
    all_loggers = [name for name in logging.Logger.manager.loggerDict if "fastmcp" in name.lower()]
    print(f"  FastMCP-related loggers: {all_loggers}")

    # Check the root fastmcp logger
    fm_logger = logging.getLogger("fastmcp")
    print(f"  fastmcp logger level: {fm_logger.level} ({logging.getLevelName(fm_logger.level)})")
    print(f"  fastmcp logger handlers: {fm_logger.handlers}")


async def main() -> None:
    print("=" * 60)
    print("EXPERIMENT 03: Server-Side Logging")
    print("=" * 60)

    explore_get_logger()
    explore_stderr()
    await explore_dual_logging()
    explore_fastmcp_loggers()

    print("\n" + "=" * 60)
    print("LOGGING MATRIX — Fill in after running:")
    print("=" * 60)
    print("""
    | Method              | Goes where?        | When to use?              |
    |---------------------|--------------------|---------------------------|
    | ctx.info()          | MCP client         | ?                         |
    | ctx.warning()       | MCP client         | ?                         |
    | get_logger().info() | ???                | ?                         |
    | FileHandler         | Log file           | ?                         |
    | print()/stderr      | ???                | ?                         |
    """)
    print("EXPERIMENT 03 COMPLETE")
    print("=" * 60)


if __name__ == "__main__":
    asyncio.run(main())
