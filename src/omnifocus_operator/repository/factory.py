"""Repository factory -- creates the appropriate repository implementation.

The ``create_repository`` function selects a repository based on a string type
identifier (typically from the ``OMNIFOCUS_REPOSITORY`` environment variable).
"""

from __future__ import annotations

import logging
import os
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.repository.protocol import Repository

__all__ = ["create_repository"]

logger = logging.getLogger("omnifocus_operator")

# Default OmniFocus SQLite database path (duplicated from hybrid.py to avoid
# coupling to a private constant).
_DEFAULT_DB_PATH = os.path.expanduser(
    "~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus"
    "/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel"
    "/OmniFocusDatabase.db"
)


def create_repository(repo_type: str | None = None) -> Repository:
    """Create a repository instance for the given *repo_type*.

    Parameters
    ----------
    repo_type:
        One of ``"hybrid"`` or ``"bridge-only"``.
        If *None*, reads ``OMNIFOCUS_REPOSITORY`` env var (default ``"hybrid"``).

    Returns
    -------
    Repository
        A repository implementation matching the requested type.

    Raises
    ------
    ValueError
        For unknown repository type strings.
    FileNotFoundError
        When hybrid mode is selected but the database file is missing.
    """
    if repo_type is None:
        repo_type = os.environ.get("OMNIFOCUS_REPOSITORY", "hybrid")

    match repo_type:
        case "hybrid":
            return _create_hybrid_repository()
        case "bridge-only":
            return _create_bridge_repository()
        case _:
            msg = f"Unknown repository type: {repo_type!r}. Use: hybrid, bridge-only"
            raise ValueError(msg)


def _create_hybrid_repository() -> Repository:
    """Create a HybridRepository with path validation."""
    from omnifocus_operator.repository.hybrid import HybridRepository

    db_path = os.environ.get("OMNIFOCUS_SQLITE_PATH", _DEFAULT_DB_PATH)

    if not os.path.exists(db_path):
        msg = (
            f"OmniFocus SQLite database not found at:\n"
            f"  {db_path}\n"
            f"\n"
            f"To fix this:\n"
            f"  Set OMNIFOCUS_SQLITE_PATH to the correct database location.\n"
            f"\n"
            f"As a temporary workaround:\n"
            f"  Set OMNIFOCUS_REPOSITORY=bridge-only to use the OmniJS bridge\n"
            f"  (slower, no 'blocked' availability)."
        )
        raise FileNotFoundError(msg)

    return HybridRepository(db_path=Path(db_path))


def _create_bridge_repository() -> Repository:
    """Create a BridgeRepository with appropriate MtimeSource."""
    from omnifocus_operator.bridge import create_bridge
    from omnifocus_operator.bridge.mtime import ConstantMtimeSource, MtimeSource
    from omnifocus_operator.repository.bridge import BridgeRepository

    bridge_type = os.environ.get("OMNIFOCUS_BRIDGE", "real")
    bridge = create_bridge(bridge_type)

    mtime_source: MtimeSource
    if bridge_type in ("inmemory", "simulator"):
        mtime_source = ConstantMtimeSource()
    else:  # pragma: no cover — SAFE-01: real bridge path, tested via UAT
        from omnifocus_operator.bridge.mtime import FileMtimeSource
        from omnifocus_operator.bridge.real import DEFAULT_OFOCUS_PATH

        ofocus_path = os.environ.get("OMNIFOCUS_OFOCUS_PATH", str(DEFAULT_OFOCUS_PATH))
        if not os.path.exists(ofocus_path):
            logger.error(
                "OmniFocus .ofocus bundle not found at: %s — "
                "set OMNIFOCUS_OFOCUS_PATH or verify OmniFocus 4 is installed.",
                ofocus_path,
            )
            raise FileNotFoundError(f"OmniFocus .ofocus bundle not found: {ofocus_path}")
        mtime_source = FileMtimeSource(path=ofocus_path)

    logger.warning(
        "Running in bridge mode — 'blocked' availability is not available, "
        "and reads are slower (~500ms vs ~50ms). "
        "Set OMNIFOCUS_REPOSITORY=hybrid for full functionality."
    )

    return BridgeRepository(bridge=bridge, mtime_source=mtime_source)
