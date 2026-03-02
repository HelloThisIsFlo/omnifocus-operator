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

    from omnifocus_operator.server import create_server

    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
