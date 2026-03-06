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
ConstantMtimeSource
    Always returns 0 -- no cache invalidation for InMemoryBridge usage.
"""

from __future__ import annotations

from omnifocus_operator.repository._repository import OmniFocusRepository
from omnifocus_operator.repository.mtime import (
    ConstantMtimeSource,
    FileMtimeSource,
    MtimeSource,
)

__all__ = [
    "ConstantMtimeSource",
    "FileMtimeSource",
    "MtimeSource",
    "OmniFocusRepository",
]
