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

__all__ = [
    "Bridge",
    "BridgeCall",
    "BridgeConnectionError",
    "BridgeError",
    "BridgeProtocolError",
    "BridgeTimeoutError",
    "InMemoryBridge",
    "create_bridge",
]
