"""Entry point for omnifocus-operator."""

from __future__ import annotations

import sys


def main() -> None:
    """Run the OmniFocus Operator MCP server.

    Redirects stdout to stderr (TOOL-04: stdout is reserved for MCP
    protocol traffic), configures logging, then starts the server on
    the stdio transport.
    """
    # TOOL-04: stdout is reserved for MCP protocol traffic
    sys.stdout = sys.stderr

    import logging
    import os

    level = os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO").upper()
    logging.basicConfig(
        level=level,
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )

    from omnifocus_operator.server import create_server

    server = create_server()
    server.run(transport="stdio")


if __name__ == "__main__":
    main()
