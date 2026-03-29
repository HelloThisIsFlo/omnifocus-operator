"""Entry point for omnifocus-operator."""

from __future__ import annotations

import logging
import os
import sys
from logging.handlers import RotatingFileHandler


def _configure_logging() -> None:
    """Configure root omnifocus_operator logger with dual handlers.

    Handler 1: StreamHandler(stderr) -- visible in Claude Desktop log page.
    Handler 2: RotatingFileHandler -- persistent fallback for Claude Code
    where stderr is swallowed during tool execution.

    See: https://github.com/anthropics/claude-code/issues/29035
    The file handler may become redundant when that issue is resolved.
    """
    level = os.environ.get("OPERATOR_LOG_LEVEL", "INFO").upper()
    root = logging.getLogger("omnifocus_operator")
    root.setLevel(level)
    root.propagate = False  # Don't leak to Python root logger

    fmt = "%(asctime)s %(levelname)-8s [%(name)s] %(message)s"

    # Handler 1: stderr (Claude Desktop log page)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(fmt, datefmt="%H:%M:%S"))
    root.addHandler(stderr_handler)

    # Handler 2: rotating file (persistent; fallback for Claude Code)
    # Claude Code swallows stderr during tool execution:
    # https://github.com/anthropics/claude-code/issues/29035
    # This handler may become redundant when that issue is resolved.
    log_path = os.path.expanduser("~/Library/Logs/omnifocus-operator.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path,
        maxBytes=5_000_000,
        backupCount=3,
    )
    file_handler.setFormatter(logging.Formatter(fmt))
    root.addHandler(file_handler)


def main() -> None:
    """Run the OmniFocus Operator MCP server."""
    _configure_logging()

    from omnifocus_operator.server import create_server

    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
