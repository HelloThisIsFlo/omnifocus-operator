"""Repository package -- protocol and implementations for OmniFocus data access.

Provides the ``Repository`` protocol abstraction, ``BridgeRepository`` (production
implementation wrapping Bridge + MtimeSource + adapter with caching), and
``InMemoryRepository`` (testing implementation returning pre-built snapshots).

MtimeSource classes live in ``omnifocus_operator.bridge.mtime``.
"""

from omnifocus_operator.repository.bridge import BridgeRepository
from omnifocus_operator.repository.in_memory import InMemoryRepository
from omnifocus_operator.repository.protocol import Repository

__all__ = [
    "BridgeRepository",
    "InMemoryRepository",
    "Repository",
]
