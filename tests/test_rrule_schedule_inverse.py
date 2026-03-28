"""Tests for inverse bridge mapping functions.

Tests schedule_to_bridge and based_on_to_bridge inverse mappings,
including round-trip consistency with the forward derive_schedule.
"""

from __future__ import annotations

from omnifocus_operator.models.enums import BasedOn, Schedule
from omnifocus_operator.rrule.schedule import (
    based_on_to_bridge,
    derive_schedule,
    schedule_to_bridge,
)

# Bridge-to-internal mapping (same as adapter._SCHEDULE_TYPE_MAP)
_BRIDGE_SCHEDULE_MAP = {"Regularly": "regularly", "FromCompletion": "from_completion"}


class TestScheduleToBridge:
    """Tests for schedule_to_bridge inverse mapping."""

    def test_regularly(self) -> None:
        assert schedule_to_bridge(Schedule.REGULARLY) == ("Regularly", False)

    def test_regularly_with_catch_up(self) -> None:
        assert schedule_to_bridge(Schedule.REGULARLY_WITH_CATCH_UP) == ("Regularly", True)

    def test_from_completion(self) -> None:
        assert schedule_to_bridge(Schedule.FROM_COMPLETION) == ("FromCompletion", False)


class TestBasedOnToBridge:
    """Tests for based_on_to_bridge inverse mapping."""

    def test_due_date(self) -> None:
        assert based_on_to_bridge(BasedOn.DUE_DATE) == "DueDate"

    def test_defer_date(self) -> None:
        assert based_on_to_bridge(BasedOn.DEFER_DATE) == "DeferDate"

    def test_planned_date(self) -> None:
        assert based_on_to_bridge(BasedOn.PLANNED_DATE) == "PlannedDate"


class TestRoundTrip:
    """Verify schedule_to_bridge -> derive_schedule produces the original enum value.

    The bridge uses PascalCase (Regularly, FromCompletion); derive_schedule
    takes the lowercase internal form (regularly, from_completion). We map
    through the same adapter table used in production.
    """

    def test_regularly_round_trip(self) -> None:
        bridge_type, catch_up = schedule_to_bridge(Schedule.REGULARLY)
        internal = _BRIDGE_SCHEDULE_MAP[bridge_type]
        assert derive_schedule(internal, catch_up) == Schedule.REGULARLY.value

    def test_regularly_with_catch_up_round_trip(self) -> None:
        bridge_type, catch_up = schedule_to_bridge(Schedule.REGULARLY_WITH_CATCH_UP)
        internal = _BRIDGE_SCHEDULE_MAP[bridge_type]
        assert derive_schedule(internal, catch_up) == Schedule.REGULARLY_WITH_CATCH_UP.value

    def test_from_completion_round_trip(self) -> None:
        bridge_type, catch_up = schedule_to_bridge(Schedule.FROM_COMPLETION)
        internal = _BRIDGE_SCHEDULE_MAP[bridge_type]
        assert derive_schedule(internal, catch_up) == Schedule.FROM_COMPLETION.value
