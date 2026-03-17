"""Bridge factory -- creates the appropriate bridge implementation.

The ``create_bridge`` function selects a bridge based on a string type
identifier (typically from the ``OMNIFOCUS_BRIDGE`` environment variable).
"""

from __future__ import annotations

import logging
from pathlib import Path
from typing import TYPE_CHECKING

if TYPE_CHECKING:
    from omnifocus_operator.bridge.protocol import Bridge

logger = logging.getLogger("omnifocus_operator")


def create_bridge(bridge_type: str) -> Bridge:
    """Create a bridge instance for the given *bridge_type*.

    Parameters
    ----------
    bridge_type:
        One of ``"simulator"`` or ``"real"``.

    Returns
    -------
    Bridge
        A bridge implementation matching the requested type.

    Raises
    ------
    ValueError
        For unknown bridge type strings.
    """
    match bridge_type:
        case "simulator":
            import os

            from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR
            from omnifocus_operator.bridge.simulator import SimulatorBridge

            ipc_dir_str = os.environ.get("OMNIFOCUS_IPC_DIR")
            ipc_dir = Path(ipc_dir_str) if ipc_dir_str else DEFAULT_IPC_DIR
            return SimulatorBridge(ipc_dir=ipc_dir)
        case "real":
            import os

            if os.environ.get("PYTEST_CURRENT_TEST"):
                msg = (
                    "RealBridge is not available during automated testing "
                    "(PYTEST_CURRENT_TEST is set). "
                    "Use OMNIFOCUS_BRIDGE=simulator instead."
                )
                raise RuntimeError(msg)

            from omnifocus_operator.bridge.real import DEFAULT_IPC_DIR, RealBridge

            ipc_dir_str = os.environ.get("OMNIFOCUS_IPC_DIR")
            ipc_dir = Path(ipc_dir_str) if ipc_dir_str else DEFAULT_IPC_DIR
            timeout = float(os.environ.get("OMNIFOCUS_BRIDGE_TIMEOUT", "10"))
            logger.debug(
                "create_bridge: type=%s, timeout=%.1fs, ipc_dir=%s",
                bridge_type,
                timeout,
                ipc_dir,
            )
            return RealBridge(ipc_dir=ipc_dir, timeout=timeout)
        case _:
            msg = f"Unknown bridge type: {bridge_type!r}. Use: simulator, real"
            raise ValueError(msg)
