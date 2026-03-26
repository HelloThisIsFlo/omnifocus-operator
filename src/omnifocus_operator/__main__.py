"""Entry point for omnifocus-operator."""

from __future__ import annotations

import logging
import os


def main() -> None:
    """Run the OmniFocus Operator MCP server."""
    from omnifocus_operator.server import create_server

    server = create_server()

    # TODO(Phase 31): Redesign logging -- stderr is NOT hijacked (spike exp 03 proved
    # the misdiagnosis). Phase 31 should add dual-handler (StreamHandler + FileHandler),
    # proper namespace, the works. See CONTEXT.md deferred ideas.
    log_path = os.path.expanduser("~/Library/Logs/omnifocus-operator.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    log = logging.getLogger("omnifocus_operator")
    log.setLevel(os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO").upper())
    log.propagate = False
    handler = logging.FileHandler(log_path)
    handler.setFormatter(logging.Formatter("%(asctime)s [%(levelname)s] %(name)s: %(message)s"))
    log.addHandler(handler)

    log.warning("🚀🚀🚀 OMNIFOCUS-OPERATOR SERVER STARTING 🚀🚀🚀")

    server.run(transport="stdio")


if __name__ == "__main__":
    main()
