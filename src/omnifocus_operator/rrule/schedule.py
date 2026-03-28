"""Shared schedule derivation logic for OmniFocus repetition rules.

Maps (schedule_type, catch_up) to a 3-value schedule string used in the
structured RepetitionRule model, and provides inverse mappings for the
write path.

The ``from_completion`` schedule type ignores ``catch_up`` -- OmniFocus UI
allows setting catchUpAutomatically on from-completion rules, but the value
has no effect. The server must not crash on this valid real-world state.
"""

from __future__ import annotations

from omnifocus_operator.models.enums import BasedOn, Schedule


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


# -- Inverse mappings (write path) ------------------------------------------


def schedule_to_bridge(schedule: Schedule) -> tuple[str, bool]:
    """Inverse of derive_schedule: Schedule enum -> (scheduleType, catchUpAutomatically).

    Maps the 3-value Schedule enum back to the bridge's 2-field representation.
    """
    if schedule == Schedule.FROM_COMPLETION:
        return ("FromCompletion", False)
    if schedule == Schedule.REGULARLY_WITH_CATCH_UP:
        return ("Regularly", True)
    return ("Regularly", False)


def based_on_to_bridge(based_on: BasedOn) -> str:
    """BasedOn enum -> OmniJS anchorDateKey string."""
    return {
        BasedOn.DUE_DATE: "DueDate",
        BasedOn.DEFER_DATE: "DeferDate",
        BasedOn.PLANNED_DATE: "PlannedDate",
    }[based_on]
