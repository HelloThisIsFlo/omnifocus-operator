"""Shared schedule derivation logic for OmniFocus repetition rules.

Maps (schedule_type, catch_up) to a 3-value schedule string used in the
structured RepetitionRule model.

The ``from_completion`` schedule type ignores ``catch_up`` -- OmniFocus UI
allows setting catchUpAutomatically on from-completion rules, but the value
has no effect. The server must not crash on this valid real-world state.
"""

from __future__ import annotations


def derive_schedule(schedule_type: str, catch_up: bool) -> str:
    """Derive 3-value schedule from schedule_type + catch_up flag.

    Returns one of: ``"from_completion"``, ``"regularly_with_catch_up"``,
    ``"regularly"``.

    ``catch_up`` is ignored when ``schedule_type`` is ``"from_completion"``
    because OmniFocus treats catchUpAutomatically as irrelevant in that
    context (the UI can still set it, but it has no effect).
    """
    if schedule_type == "from_completion":
        return "from_completion"
    if catch_up:
        return "regularly_with_catch_up"
    return "regularly"
