"""Test doubles for OmniFocus Operator.

All test doubles are re-exported here for convenience:
    from tests.doubles import InMemoryBridge, StubBridge
"""

from tests.doubles.bridge import BridgeCall, InMemoryBridge, StubBridge
from tests.doubles.mtime import ConstantMtimeSource
from tests.doubles.simulator import SimulatorBridge

__all__ = [
    "BridgeCall",
    "ConstantMtimeSource",
    "InMemoryBridge",
    "SimulatorBridge",
    "StubBridge",
]
