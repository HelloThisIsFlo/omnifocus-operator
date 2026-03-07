"""OmniFocus bridge protocol, implementations, and factory."""

from omnifocus_operator.bridge.errors import (
    BridgeConnectionError,
    BridgeError,
    BridgeProtocolError,
    BridgeTimeoutError,
)
from omnifocus_operator.bridge.factory import create_bridge
from omnifocus_operator.bridge.in_memory import BridgeCall, InMemoryBridge
from omnifocus_operator.bridge.mtime import (
    ConstantMtimeSource,
    FileMtimeSource,
    MtimeSource,
)
from omnifocus_operator.bridge.protocol import Bridge
from omnifocus_operator.bridge.real import (
    DEFAULT_OFOCUS_PATH,
    OMNIFOCUS_CONTAINER,
    RealBridge,
    sweep_orphaned_files,
)
from omnifocus_operator.bridge.simulator import SimulatorBridge

__all__ = [
    "DEFAULT_OFOCUS_PATH",
    "OMNIFOCUS_CONTAINER",
    "Bridge",
    "BridgeCall",
    "BridgeConnectionError",
    "BridgeError",
    "BridgeProtocolError",
    "BridgeTimeoutError",
    "ConstantMtimeSource",
    "FileMtimeSource",
    "InMemoryBridge",
    "MtimeSource",
    "RealBridge",
    "SimulatorBridge",
    "create_bridge",
    "sweep_orphaned_files",
]
