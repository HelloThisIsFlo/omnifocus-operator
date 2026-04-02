"""Bridge serialization for repetition rules.

Converts structured ``RepetitionRuleRepoPayload`` (core domain types)
to the flat dict the OmniJS bridge expects.  Mirrors the read-side
parsing in ``hybrid.py`` / ``adapter.py``.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

from omnifocus_operator.rrule.builder import build_rrule
from omnifocus_operator.rrule.schedule import based_on_to_bridge, schedule_to_bridge

if TYPE_CHECKING:
    from omnifocus_operator.contracts.shared.repetition_rule import (
        RepetitionRuleRepoPayload,
    )

__all__ = ["serialize_repetition_rule"]


def serialize_repetition_rule(payload: RepetitionRuleRepoPayload) -> dict[str, Any]:
    """Convert structured repetition rule to bridge-format dict."""
    rule_string = build_rrule(payload.frequency, payload.end)
    schedule_type, catch_up = schedule_to_bridge(payload.schedule)
    anchor_date_key = based_on_to_bridge(payload.based_on)
    return {
        "ruleString": rule_string,
        "scheduleType": schedule_type,
        "anchorDateKey": anchor_date_key,
        "catchUpAutomatically": catch_up,
    }
