"""Repository package -- protocol and implementations for OmniFocus data access.

Provides the ``Repository`` protocol abstraction, ``BridgeRepository`` (production
implementation wrapping Bridge + MtimeSource + adapter with caching), and
``HybridRepository`` (SQLite-based reader for fast ~46ms reads).

MtimeSource classes live in ``omnifocus_operator.bridge.mtime``.
"""

from omnifocus_operator.repository.bridge import BridgeRepository
from omnifocus_operator.repository.factory import create_repository
from omnifocus_operator.repository.hybrid import HybridRepository
from omnifocus_operator.repository.protocol import Repository

__all__ = [
    "BridgeRepository",
    "HybridRepository",
    "Repository",
    "create_repository",
]
