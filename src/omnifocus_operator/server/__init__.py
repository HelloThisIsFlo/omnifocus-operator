"""Server package -- FastMCP server for OmniFocus Operator.

Public API
----------
create_server
    Factory function returning a configured ``FastMCP`` instance.
"""

from __future__ import annotations

from omnifocus_operator.server._server import create_server

__all__ = ["create_server"]
