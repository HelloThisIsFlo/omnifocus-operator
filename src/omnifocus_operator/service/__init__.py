"""Service layer -- primary API surface for the MCP server.

Public API
----------
OperatorService
    Thin passthrough to the repository layer; delegates ``get_all_data()``
    to ``OmniFocusRepository.get_snapshot()``.
"""

from __future__ import annotations

from omnifocus_operator.service._service import OperatorService

__all__ = ["OperatorService"]
