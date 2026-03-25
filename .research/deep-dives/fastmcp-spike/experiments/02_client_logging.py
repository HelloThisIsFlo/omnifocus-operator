"""Experiment 02: Client vs Server Logging — Where Does Each One Show Up?

QUESTION: What's the best way to get diagnostic logs visible on the Claude Desktop
log page? How do ctx.info(), get_logger(), and plain StreamHandler(stderr) compare?

CONTEXT:
  Three logging paths tested:
  - ctx.info() / ctx.warning() — MCP protocol notifications (turns out no client renders these)
  - get_logger() — FastMCP's server-side logger (Rich formatting, no logger name shown)
  - StreamHandler(stderr) — plain Python logging to stderr (full control, shows on Claude Desktop)

  Result: StreamHandler(stderr) is the winner. ctx.info() is useless. See FINDINGS.md.

HOW TO CONNECT:
  Option A — MCP Inspector:
    1. Start: uv run python .research/deep-dives/fastmcp-spike/experiments/02_client_logging.py
    2. In another terminal: npx @modelcontextprotocol/inspector
    3. Connect via stdio

  Option B — Claude Code / Desktop:
    1. Run: uv run python .research/deep-dives/fastmcp-spike/experiments/setup_mcp.py add 02
    2. Restart client
    3. Call the tools

GUIDED WALKTHROUGH:
  1. Call `compare_ctx_vs_logger` — same message sent via 3 paths (ctx, get_logger, file).
     - Which ones appear on the Claude Desktop log page?
     - Which ones appear in /tmp/fastmcp-spike-02.log?

  2. Call `explore_server_loggers` — compares get_logger() vs named get_logger() vs plain stderr.
     - Does get_logger() show the logger name? Does plain stderr?
     - Which levels come through for each?

  3. Call `format_showcase` — 11 formatter patterns side by side, plus child logger hierarchy.
     - Scan the log page and pick the format you like best.

  4. Call `ctx_with_structured_data` — tests the extra parameter on ctx.info().
     - Does structured data appear? (Mostly academic — ctx is not our path.)

  5. Call `all_ctx_levels` / `rapid_fire` — level filtering and ordering tests.
"""

from __future__ import annotations

import logging

from fastmcp import FastMCP, Context
from fastmcp.utilities.logging import get_logger

# ── File logger (our current pattern) ────────────────────────────────
LOG_FILE = "/tmp/fastmcp-spike-02.log"

file_logger = logging.getLogger("spike_file")
file_logger.setLevel(logging.DEBUG)
file_logger.propagate = False
file_handler = logging.FileHandler(LOG_FILE, mode="w")
file_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
file_logger.addHandler(file_handler)

# ── FastMCP get_logger (server-side logging) ─────────────────────────
server_logger = get_logger("spike_server")

# ── get_logger with explicit name= kwarg (like the docs show) ────────
named_logger = get_logger(name="spike_named")
named_logger.setLevel(logging.DEBUG)

# ── Plain stderr logger (standard Python, no FastMCP) ────────────────
stderr_logger = logging.getLogger("spike_stderr")
stderr_logger.setLevel(logging.DEBUG)
stderr_handler = logging.StreamHandler()  # defaults to stderr
stderr_handler.setFormatter(
    logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s")
)
stderr_logger.addHandler(stderr_handler)
stderr_logger.propagate = False

# ── Server ───────────────────────────────────────────────────────────
mcp = FastMCP("logging-spike")


@mcp.tool()
async def compare_ctx_vs_logger(ctx: Context) -> dict[str, str]:
    """Sends the same message via 3 different logging paths.

    After calling, check:
    1. Claude Desktop log page — which messages appear?
    2. /tmp/fastmcp-spike-02.log — which messages appear?
    3. Your terminal stderr — which messages appear?
    """
    msg = "Processing batch of 3 tasks"

    # Path 1: ctx.info() — MCP protocol notification
    await ctx.info(f"[CTX] {msg}")

    # Path 2: get_logger() — FastMCP's server-side logger
    server_logger.info(f"[GET_LOGGER] {msg}")

    # Path 3: file logger — our current pattern
    file_logger.info(f"[FILE_LOGGER] {msg}")

    return {
        "paths_used": "ctx.info, get_logger().info, file_logger.info",
        "log_file": LOG_FILE,
        "instruction": "Compare: which paths show up on the client log page vs the file?",
    }


@mcp.tool()
async def explore_server_loggers(ctx: Context) -> dict[str, str]:
    """Compares get_logger() vs plain Python stderr logger.

    Questions:
    - Does get_logger() show the logger name? Does plain stderr?
    - How does the formatting differ?
    - Which levels come through?
    - What does get_logger() actually configure? (handlers, formatters)
    """
    # get_logger() — positional arg
    server_logger.debug("[GET_LOGGER] debug: tag cache miss for 'Work'")
    server_logger.info("[GET_LOGGER] info: resolving parent 'pJKx9xL5beb'")
    server_logger.warning("[GET_LOGGER] warning: slow query 230ms")

    # get_logger(name=) — explicit kwarg, with setLevel(DEBUG)
    named_logger.debug("[NAMED] debug: tag cache miss for 'Work'")
    named_logger.info("[NAMED] info: resolving parent 'pJKx9xL5beb'")
    named_logger.warning("[NAMED] warning: slow query 230ms")

    # Plain Python stderr — standard formatter with logger name
    stderr_logger.debug("[STDERR] debug: tag cache miss for 'Work'")
    stderr_logger.info("[STDERR] info: resolving parent 'pJKx9xL5beb'")
    stderr_logger.warning("[STDERR] warning: slow query 230ms")

    # Inspect all loggers
    return {
        "get_logger_name": server_logger.name,
        "get_logger_effective_level": logging.getLevelName(server_logger.getEffectiveLevel()),
        "get_logger_handlers": str([type(h).__name__ for h in server_logger.handlers]),
        "named_logger_name": named_logger.name,
        "named_logger_level": logging.getLevelName(named_logger.level),
        "named_logger_effective_level": logging.getLevelName(named_logger.getEffectiveLevel()),
        "named_logger_handlers": str([type(h).__name__ for h in named_logger.handlers]),
        "named_logger_propagate": str(named_logger.propagate),
        "instruction": "Compare: does name= kwarg change prefix or debug visibility?",
    }


@mcp.tool()
async def format_showcase(ctx: Context) -> str:
    """Prints the same log messages with many different formatter configurations.

    Call once, then scan the log page to find the format you like best.
    """
    import sys

    # Realistic messages to test with
    short_msg = "Cache hit for tag 'Work'"
    medium_msg = "OperatorService.add_task: name=Review Q3, parent=pJKx9xL5beb, tags=['Work']"
    long_msg = (
        "HybridRepository.get_all: SQLite read 847 tasks, 42 projects, "
        "15 tags, 3 folders in 46ms — cache age 12s, threshold 30s"
    )
    warning_msg = "Task 'oRx3bL' is completed — editing anyway per user request"
    error_msg = "Bridge timeout after 5000ms on add_task — retrying (attempt 2/3)"

    formats = {
        # --- Minimal ---
        "minimal": "%(levelname)s %(message)s",
        "minimal+name": "%(levelname)s %(name)s: %(message)s",

        # --- With timestamp ---
        "time+level+msg": "%(asctime)s %(levelname)s %(message)s",
        "time+level+name+msg": "%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        "time+level+name+func": "%(asctime)s [%(levelname)s] %(name)s.%(funcName)s: %(message)s",

        # --- With source location ---
        "level+file+msg": "%(levelname)s %(filename)s:%(lineno)d %(message)s",
        "level+name+file+msg": "%(levelname)s %(name)s (%(filename)s:%(lineno)d): %(message)s",

        # --- Compact timestamps ---
        "short-time+level+name": "%(asctime)s %(levelname).1s %(name)s: %(message)s",

        # --- Padded level (aligned) ---
        "padded-level+name": "%(levelname)-8s %(name)s: %(message)s",
        "padded-level+time+name": "%(asctime)s %(levelname)-8s %(name)s: %(message)s",

        # --- Name hierarchy ---
        "dotted-name": "%(levelname)-8s [%(name)s] %(message)s",
    }

    test_logger = logging.getLogger("omnifocus_operator.service")
    test_logger.setLevel(logging.DEBUG)
    test_logger.propagate = False

    handler = logging.StreamHandler(sys.stderr)
    test_logger.addHandler(handler)

    output_lines = []

    for label, fmt in formats.items():
        handler.setFormatter(logging.Formatter(fmt))

        # Separator
        sys.stderr.write(f"\n{'─' * 60}\n")
        sys.stderr.write(f"  FORMAT: {label}\n")
        sys.stderr.write(f"  Pattern: {fmt}\n")
        sys.stderr.write(f"{'─' * 60}\n")
        sys.stderr.flush()

        test_logger.debug(short_msg)
        test_logger.info(medium_msg)
        test_logger.warning(warning_msg)
        test_logger.info(long_msg)
        test_logger.error(error_msg)

        output_lines.append(f"{label}: {fmt}")

    # Also test with a child logger to see hierarchy
    child_logger = logging.getLogger("omnifocus_operator.service.add_tasks")
    child_logger.setLevel(logging.DEBUG)
    # child propagates to parent, which has the handler

    handler.setFormatter(logging.Formatter("%(levelname)-8s [%(name)s] %(message)s"))
    sys.stderr.write(f"\n{'─' * 60}\n")
    sys.stderr.write(f"  BONUS: Child logger hierarchy\n")
    sys.stderr.write(f"{'─' * 60}\n")
    sys.stderr.flush()

    test_logger.info("Parent: OperatorService dispatching")
    child_logger.info("Child: Processing item 1/3")
    child_logger.warning("Child: Tag 'Urgnt' not found")
    child_logger.debug("Child: Resolved to 'Urgent' via fuzzy match")

    # Cleanup
    test_logger.removeHandler(handler)

    return f"Printed {len(formats)} format variations + child logger demo. Check the log page!"


@mcp.tool()
async def ctx_with_structured_data(ctx: Context) -> dict[str, str]:
    """Tests ctx.info() with the extra parameter for structured data.

    The docs say all ctx methods accept extra={} for structured data.
    Question: does it show up on the log page? How?
    """
    # Plain message
    await ctx.info("Resolving tag 'Work' to ID")

    # Message with structured extra data
    await ctx.info(
        "Tag resolved successfully",
        extra={
            "tag_name": "Work",
            "tag_id": "tkAbc123",
            "resolution_ms": 12,
        },
    )

    # Warning with extra
    await ctx.warning(
        "Tag 'Urgnt' not found — did you mean 'Urgent'?",
        extra={
            "requested": "Urgnt",
            "suggestion": "Urgent",
            "distance": 1,
        },
    )

    return {
        "instruction": "Check log page: does structured data appear? Or just the message string?",
    }


@mcp.tool()
async def all_ctx_levels(ctx: Context) -> str:
    """Emits one message at each log level — which ones show up?"""
    await ctx.debug("DEBUG: Detailed diagnostic — tag cache hit ratio 0.87")
    await ctx.info("INFO: Processing add_tasks request, 3 items")
    await ctx.warning("WARNING: Task 'oRx3bL' is already completed — editing anyway")
    await ctx.error("ERROR: Bridge timeout after 5s — retrying with backoff")
    return "Logged at debug/info/warning/error. Which appeared on the log page?"


@mcp.tool()
async def rapid_fire(ctx: Context) -> str:
    """Sends 10 messages quickly — do they all arrive? In order?"""
    for i in range(1, 11):
        await ctx.info(f"Step {i}/10: processing item")
    return "Sent 10 messages. Did they all arrive on the log page? In order?"


if __name__ == "__main__":
    mcp.run(transport="stdio")
