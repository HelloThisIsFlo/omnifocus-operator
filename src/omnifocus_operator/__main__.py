"""Entry point for omnifocus-operator."""

from __future__ import annotations

import logging
import os
import sys


def main() -> None:
    """Run the OmniFocus Operator MCP server."""
    logging.basicConfig(
        level=os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    logger = logging.getLogger("omnifocus_operator")

    # Validate .ofocus path before entering async context — errors inside
    # the MCP lifespan get swallowed by anyio's ExceptionGroup and cause
    # the process to hang instead of exiting cleanly.
    bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "real")
    if bridge_type == "real":
        from omnifocus_operator.bridge._real import DEFAULT_OFOCUS_PATH

        ofocus_path = os.environ.get("OMNIFOCUS_OFOCUS_PATH", str(DEFAULT_OFOCUS_PATH))
        if not os.path.exists(ofocus_path):
            logger.error(
                "OmniFocus database not found at: %s — "
                "set OMNIFOCUS_OFOCUS_PATH or verify OmniFocus 4 is installed.",
                ofocus_path,
            )
            sys.exit(1)

    from omnifocus_operator.server import create_server

    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
