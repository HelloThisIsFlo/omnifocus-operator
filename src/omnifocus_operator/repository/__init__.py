"""Repository module -- caching layer between service and bridge.

Public API
----------
OmniFocusRepository
    Caching repository: loads snapshots from the bridge, refreshes on
    mtime change, serves reads from memory.
MtimeSource
    Protocol for data-source freshness checks.
FileMtimeSource
    Production implementation backed by filesystem stat (st_mtime_ns).
"""

from __future__ import annotations

from omnifocus_operator.repository._mtime import FileMtimeSource, MtimeSource
from omnifocus_operator.repository._repository import OmniFocusRepository

__all__ = ["FileMtimeSource", "MtimeSource", "OmniFocusRepository"]
