"""OmniFocus bridge protocol and implementations."""

from omnifocus_operator.bridge.errors import (
    BridgeConnectionError,
    BridgeError,
    BridgeProtocolError,
    BridgeTimeoutError,
)
from omnifocus_operator.bridge.mtime import (
    FileMtimeSource,
    MtimeSource,
)
from omnifocus_operator.bridge.real import (
    DEFAULT_OFOCUS_PATH,
    OMNIFOCUS_CONTAINER,
    RealBridge,
    sweep_orphaned_files,
)
from omnifocus_operator.contracts.protocols import Bridge

__all__ = [
    "DEFAULT_OFOCUS_PATH",
    "OMNIFOCUS_CONTAINER",
    "Bridge",
    "BridgeConnectionError",
    "BridgeError",
    "BridgeProtocolError",
    "BridgeTimeoutError",
    "FileMtimeSource",
    "MtimeSource",
    "RealBridge",
    "sweep_orphaned_files",
]
