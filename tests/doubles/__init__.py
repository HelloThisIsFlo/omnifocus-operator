"""Test doubles for OmniFocus Operator.

All test doubles are re-exported here for convenience:
    from tests.doubles import InMemoryBridge, StubBridge
"""

from tests.doubles.bridge import BridgeCall, InMemoryBridge
from tests.doubles.mtime import ConstantMtimeSource
from tests.doubles.simulator import SimulatorBridge
from tests.doubles.stub_bridge import StubBridge

__all__ = [
    "BridgeCall",
    "ConstantMtimeSource",
    "InMemoryBridge",
    "SimulatorBridge",
    "StubBridge",
]
