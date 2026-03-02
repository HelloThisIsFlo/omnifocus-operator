"""SimulatorBridge -- file-based IPC bridge without OmniFocus trigger.

SimulatorBridge is a minimal RealBridge subclass that overrides
``_trigger_omnifocus()`` as a permanent no-op.  All IPC file mechanics
(request writing, response polling, cleanup, orphan sweep) are inherited
from RealBridge.

Designed to pair with the mock simulator process (Phase 7 Plan 02), which
monitors the IPC directory and writes response files directly -- no URL
scheme trigger needed.
"""

from __future__ import annotations

from omnifocus_operator.bridge._real import RealBridge


class SimulatorBridge(RealBridge):
    """File-based IPC bridge that skips OmniFocus URL scheme trigger.

    Inherits all IPC mechanics from :class:`RealBridge`.  The only
    difference is that ``_trigger_omnifocus()`` does nothing, allowing
    a separate mock-simulator process to respond to request files.
    """

    def _trigger_omnifocus(self, file_prefix: str) -> None:
        """No-op -- the mock simulator watches the IPC directory directly."""
