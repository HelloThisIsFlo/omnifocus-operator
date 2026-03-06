"""OmniFocus bridge protocol, implementations, and factory."""

from omnifocus_operator.bridge._errors import (
    BridgeConnectionError,
    BridgeError,
    BridgeProtocolError,
    BridgeTimeoutError,
)
from omnifocus_operator.bridge._factory import create_bridge
from omnifocus_operator.bridge._in_memory import BridgeCall, InMemoryBridge
from omnifocus_operator.bridge._protocol import Bridge
from omnifocus_operator.bridge._real import (
    DEFAULT_OFOCUS_PATH,
    OMNIFOCUS_CONTAINER,
    RealBridge,
    sweep_orphaned_files,
)
from omnifocus_operator.bridge._simulator import SimulatorBridge

__all__ = [
    "DEFAULT_OFOCUS_PATH",
    "OMNIFOCUS_CONTAINER",
    "Bridge",
    "BridgeCall",
    "BridgeConnectionError",
    "BridgeError",
    "BridgeProtocolError",
    "BridgeTimeoutError",
    "InMemoryBridge",
    "RealBridge",
    "SimulatorBridge",
    "create_bridge",
    "sweep_orphaned_files",
]
