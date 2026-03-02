"""Bridge factory -- creates the appropriate bridge implementation.

The ``create_bridge`` function selects a bridge based on a string type
identifier (typically from the ``OMNIFOCUS_BRIDGE`` environment variable).
"""

from __future__ import annotations

from typing import TYPE_CHECKING

from omnifocus_operator.bridge._in_memory import InMemoryBridge

if TYPE_CHECKING:
    from omnifocus_operator.bridge._protocol import Bridge


def create_bridge(bridge_type: str) -> Bridge:
    """Create a bridge instance for the given *bridge_type*.

    Parameters
    ----------
    bridge_type:
        One of ``"inmemory"``, ``"simulator"``, or ``"real"``.

    Returns
    -------
    Bridge
        A bridge implementation matching the requested type.

    Raises
    ------
    NotImplementedError
        For ``"simulator"`` or ``"real"`` (not yet available).
    ValueError
        For unknown bridge type strings.
    """
    match bridge_type:
        case "inmemory":
            return InMemoryBridge(
                data={
                    "tasks": [
                        {
                            "id": "task-001",
                            "name": "Sample Task",
                            "note": "",
                            "completed": False,
                            "completedByChildren": False,
                            "flagged": False,
                            "effectiveFlagged": False,
                            "sequential": False,
                            "hasChildren": False,
                            "shouldUseFloatingTimeZone": False,
                            "active": True,
                            "effectiveActive": True,
                            "status": "Available",
                            "inInbox": False,
                            "dueDate": None,
                            "tags": [],
                        }
                    ],
                    "projects": [
                        {
                            "id": "proj-001",
                            "name": "Sample Project",
                            "note": "",
                            "completed": False,
                            "completedByChildren": False,
                            "flagged": False,
                            "effectiveFlagged": False,
                            "sequential": False,
                            "hasChildren": True,
                            "shouldUseFloatingTimeZone": False,
                            "taskStatus": "Available",
                            "containsSingletonActions": False,
                            "status": "Active",
                        }
                    ],
                    "tags": [
                        {
                            "id": "tag-001",
                            "name": "work",
                            "active": True,
                            "effectiveActive": True,
                            "status": "Active",
                            "allowsNextAction": True,
                        }
                    ],
                    "folders": [
                        {
                            "id": "folder-001",
                            "name": "Work",
                            "active": True,
                            "effectiveActive": True,
                            "status": "Active",
                        }
                    ],
                    "perspectives": [
                        {
                            "id": None,
                            "name": "Inbox",
                            "builtin": True,
                        }
                    ],
                }
            )
        case "simulator":
            msg = "SimulatorBridge not yet implemented (Phase 7)"
            raise NotImplementedError(msg)
        case "real":
            msg = (
                "RealBridge not yet implemented (Phase 8). "
                "Set OMNIFOCUS_BRIDGE=inmemory for development."
            )
            raise NotImplementedError(msg)
        case _:
            msg = (
                f"Unknown bridge type: {bridge_type!r}. "
                "Use: inmemory, simulator, real"
            )
            raise ValueError(msg)
