"""Repository package -- protocol and implementations for OmniFocus data access.

Provides the ``Repository`` protocol abstraction, ``BridgeRepository`` (production
implementation wrapping Bridge + MtimeSource + adapter with caching), and
``InMemoryRepository`` (testing implementation returning pre-built snapshots).

MtimeSource classes are re-exported here for backward compatibility during
migration.  Canonical location: ``omnifocus_operator.bridge.mtime``.
"""

from omnifocus_operator.bridge.mtime import (
    ConstantMtimeSource,
    FileMtimeSource,
    MtimeSource,
)
from omnifocus_operator.repository.bridge import BridgeRepository
from omnifocus_operator.repository.in_memory import InMemoryRepository
from omnifocus_operator.repository.protocol import Repository

# Backward compatibility alias -- Plan 02 will update all import sites
OmniFocusRepository = BridgeRepository

__all__ = [
    "BridgeRepository",
    "ConstantMtimeSource",
    "FileMtimeSource",
    "InMemoryRepository",
    "MtimeSource",
    "OmniFocusRepository",
    "Repository",
]
