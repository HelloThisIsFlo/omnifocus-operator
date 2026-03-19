"""BridgeWriteMixin -- shared bridge-sending logic for write operations.

Centralizes the model_dump(by_alias=True, exclude_unset=True) + send_command
pattern used by both BridgeRepository and HybridRepository.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from omnifocus_operator.contracts.protocols import Bridge
    from omnifocus_operator.models.base import OmniFocusBaseModel


class BridgeWriteMixin:
    """Shared bridge-sending logic for BridgeRepository and HybridRepository.

    Expects the concrete class to have a ``_bridge: Bridge`` attribute.
    """

    _bridge: Bridge

    async def _send_to_bridge(self, command: str, payload: OmniFocusBaseModel) -> dict[str, Any]:
        """Serialize payload to camelCase dict and send via bridge.

        Uses ``by_alias=True`` for camelCase keys (bridge expects camelCase)
        and ``exclude_unset=True`` to omit fields not explicitly set.
        """
        raw = payload.model_dump(by_alias=True, exclude_unset=True)
        return await self._bridge.send_command(command, raw)
