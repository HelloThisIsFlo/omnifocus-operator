"""BridgeWriteMixin -- shared bridge-sending logic for write operations.

Centralizes the model_dump(by_alias=True, exclude_unset=True) + send_command
pattern used by both BridgeRepository and HybridRepository.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from omnifocus_operator.repository.repetition_rule import serialize_repetition_rule

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
        raw = self._dump_payload(payload)
        return await self._bridge.send_command(command, raw)

    def _dump_payload(self, payload: OmniFocusBaseModel) -> dict[str, Any]:
        """Serialize payload to bridge-ready dict, handling repetition rules.

        The default model_dump produces nested core-type dicts for
        repetition rules. This method intercepts and re-serializes
        them to the flat bridge format the OmniJS bridge expects.
        """
        raw = payload.model_dump(by_alias=True, exclude_unset=True)
        rep_key = "repetitionRule"
        if rep_key in raw and raw[rep_key] is not None:
            raw[rep_key] = serialize_repetition_rule(getattr(payload, "repetition_rule"))
        return raw
