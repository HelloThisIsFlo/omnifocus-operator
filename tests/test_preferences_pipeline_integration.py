"""Integration tests: write pipeline fetches per-field default times from preferences.

Covers PREF-04, PREF-05, PREF-06, PREF-07:
- PREF-04: Date-only dueDate enriched with DefaultDueTime from OmniFocusPreferences
- PREF-05: Date-only deferDate enriched with DefaultStartTime from OmniFocusPreferences
- PREF-06: Date-only plannedDate enriched with DefaultPlannedTime from OmniFocusPreferences
- PREF-07: Each field gets its OWN default time (field-aware dispatch)

These tests verify the full wiring: InMemoryBridge -> OmniFocusPreferences ->
_AddTaskPipeline/_EditTaskPipeline -> bridge receives correct datetime strings.
"""

from __future__ import annotations

from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand
from omnifocus_operator.repository import BridgeOnlyRepository
from omnifocus_operator.service import OperatorService
from omnifocus_operator.service.preferences import OmniFocusPreferences
from tests.doubles import ConstantMtimeSource
from tests.doubles.bridge import InMemoryBridge

from .conftest import make_task_dict

# ---------------------------------------------------------------------------
# Helpers
# ---------------------------------------------------------------------------


def _make_service(bridge: InMemoryBridge) -> OperatorService:
    """Build a minimal OperatorService wired to the given bridge."""

    repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
    preferences = OmniFocusPreferences(bridge)
    return OperatorService(repository=repo, preferences=preferences)


def _get_add_task_params(bridge: InMemoryBridge) -> dict:
    """Return params from the first add_task bridge call."""
    add_calls = [c for c in bridge.calls if c.operation == "add_task"]
    assert add_calls, "Expected at least one add_task bridge call"
    params = add_calls[0].params
    assert params is not None
    return params


def _get_edit_task_params(bridge: InMemoryBridge) -> dict:
    """Return params from the first edit_task bridge call."""
    edit_calls = [c for c in bridge.calls if c.operation == "edit_task"]
    assert edit_calls, "Expected at least one edit_task bridge call"
    params = edit_calls[0].params
    assert params is not None
    return params


# ---------------------------------------------------------------------------
# PREF-04: date-only dueDate enriched with DefaultDueTime
# ---------------------------------------------------------------------------


class TestAddTaskDateOnlyDueDate:
    """AddTask enriches date-only dueDate with DefaultDueTime (PREF-04)."""

    async def test_date_only_due_date_uses_preference_default_time(self) -> None:
        """Date-only dueDate reaches bridge with user's DefaultDueTime (17:00 factory default)."""
        bridge = InMemoryBridge()
        # Factory default is "17:00" -> normalized to "17:00:00"
        service = _make_service(bridge)

        await service.add_task(AddTaskCommand(name="Task", due_date="2026-07-15"))

        params = _get_add_task_params(bridge)
        assert params["dueDate"] == "2026-07-15T17:00:00"

    async def test_date_only_due_date_uses_custom_preference_time(self) -> None:
        """Date-only dueDate uses a user-customized DefaultDueTime (e.g. 19:00)."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultDueTime": "19:00"})
        service = _make_service(bridge)

        await service.add_task(AddTaskCommand(name="Task", due_date="2026-07-15"))

        params = _get_add_task_params(bridge)
        assert params["dueDate"] == "2026-07-15T19:00:00"

    async def test_full_datetime_due_date_is_not_altered(self) -> None:
        """A full datetime dueDate passes through unchanged (no default time applied)."""
        bridge = InMemoryBridge()
        service = _make_service(bridge)

        await service.add_task(AddTaskCommand(name="Task", due_date="2026-07-15T10:00:00"))

        params = _get_add_task_params(bridge)
        assert params["dueDate"] == "2026-07-15T10:00:00"


# ---------------------------------------------------------------------------
# PREF-05: date-only deferDate enriched with DefaultStartTime
# ---------------------------------------------------------------------------


class TestAddTaskDateOnlyDeferDate:
    """AddTask enriches date-only deferDate with DefaultStartTime (PREF-05)."""

    async def test_date_only_defer_date_uses_preference_default_time(self) -> None:
        """Date-only deferDate reaches bridge with DefaultStartTime."""
        bridge = InMemoryBridge()
        # Factory default is "00:00" -> normalized to "00:00:00"
        service = _make_service(bridge)

        await service.add_task(AddTaskCommand(name="Task", defer_date="2026-07-15"))

        params = _get_add_task_params(bridge)
        assert params["deferDate"] == "2026-07-15T00:00:00"

    async def test_date_only_defer_date_uses_custom_preference_time(self) -> None:
        """Date-only deferDate uses a user-customized DefaultStartTime (e.g. 08:00)."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultStartTime": "08:00"})
        service = _make_service(bridge)

        await service.add_task(AddTaskCommand(name="Task", defer_date="2026-07-15"))

        params = _get_add_task_params(bridge)
        assert params["deferDate"] == "2026-07-15T08:00:00"


# ---------------------------------------------------------------------------
# PREF-06: date-only plannedDate enriched with DefaultPlannedTime
# ---------------------------------------------------------------------------


class TestAddTaskDateOnlyPlannedDate:
    """AddTask enriches date-only plannedDate with DefaultPlannedTime (PREF-06)."""

    async def test_date_only_planned_date_uses_preference_default_time(self) -> None:
        """Date-only plannedDate reaches bridge with DefaultPlannedTime."""
        bridge = InMemoryBridge()
        # Factory default is "09:00" -> normalized to "09:00:00"
        service = _make_service(bridge)

        await service.add_task(AddTaskCommand(name="Task", planned_date="2026-07-15"))

        params = _get_add_task_params(bridge)
        assert params["plannedDate"] == "2026-07-15T09:00:00"

    async def test_date_only_planned_date_uses_custom_preference_time(self) -> None:
        """Date-only plannedDate uses a user-customized DefaultPlannedTime (e.g. 10:00)."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultPlannedTime": "10:00"})
        service = _make_service(bridge)

        await service.add_task(AddTaskCommand(name="Task", planned_date="2026-07-15"))

        params = _get_add_task_params(bridge)
        assert params["plannedDate"] == "2026-07-15T10:00:00"


# ---------------------------------------------------------------------------
# PREF-07: field-aware dispatch — each field gets its OWN default time
# ---------------------------------------------------------------------------


class TestAddTaskFieldAwareDateDispatch:
    """Each date field gets its own field-specific default time (PREF-07).

    The pipeline must call get_default_time(field) per-field, not a single
    shared default. This test sends all three date-only fields in one command
    and verifies each arrives at the bridge with a *different* time.
    """

    async def test_all_three_date_fields_get_different_default_times(self) -> None:
        """All three date-only fields in one AddTask each get their field-specific time."""
        bridge = InMemoryBridge()
        bridge.configure_settings(
            {
                "DefaultDueTime": "17:00",
                "DefaultStartTime": "08:00",
                "DefaultPlannedTime": "11:00",
            }
        )
        service = _make_service(bridge)

        await service.add_task(
            AddTaskCommand(
                name="Task",
                due_date="2026-07-15",
                defer_date="2026-07-10",
                planned_date="2026-07-12",
            )
        )

        params = _get_add_task_params(bridge)
        assert params["dueDate"] == "2026-07-15T17:00:00", "dueDate should use DefaultDueTime"
        assert params["deferDate"] == "2026-07-10T08:00:00", "deferDate should use DefaultStartTime"
        assert params["plannedDate"] == "2026-07-12T11:00:00", (
            "plannedDate should use DefaultPlannedTime"
        )

    async def test_factory_defaults_each_field_gets_different_time(self) -> None:
        """With factory defaults, each field gets distinct times (17:00, 00:00, 09:00)."""
        bridge = InMemoryBridge()
        # Factory defaults: due=17:00, defer=00:00, planned=09:00
        service = _make_service(bridge)

        await service.add_task(
            AddTaskCommand(
                name="Task",
                due_date="2026-07-15",
                defer_date="2026-07-10",
                planned_date="2026-07-12",
            )
        )

        params = _get_add_task_params(bridge)
        assert params["dueDate"] == "2026-07-15T17:00:00"
        assert params["deferDate"] == "2026-07-10T00:00:00"
        assert params["plannedDate"] == "2026-07-12T09:00:00"
        # Confirm they are NOT all the same time (proving field-aware dispatch)
        times = {params["dueDate"][-8:], params["deferDate"][-8:], params["plannedDate"][-8:]}
        assert len(times) == 3, f"Expected 3 distinct times, got: {times}"


# ---------------------------------------------------------------------------
# EditTask pipeline: same field-aware enrichment (PREF-04/05/06/07)
# ---------------------------------------------------------------------------


class TestEditTaskDateOnlyNormalization:
    """_EditTaskPipeline also fetches per-field default times from preferences.

    Validates the same PREF-04/05/06/07 requirements apply to edit_task.
    """

    async def test_edit_date_only_due_date_uses_preference_default_time(self) -> None:
        """date-only dueDate in edit_task reaches bridge with DefaultDueTime."""
        bridge = InMemoryBridge(data={"tasks": [make_task_dict(id="task-001", name="Existing")]})
        bridge.configure_settings({"DefaultDueTime": "18:00"})
        service = _make_service(bridge)

        await service.edit_task(EditTaskCommand(id="task-001", due_date="2026-07-15"))

        params = _get_edit_task_params(bridge)
        assert params["dueDate"] == "2026-07-15T18:00:00"

    async def test_edit_date_only_defer_date_uses_preference_default_time(self) -> None:
        """date-only deferDate in edit_task reaches bridge with DefaultStartTime."""
        bridge = InMemoryBridge(data={"tasks": [make_task_dict(id="task-001", name="Existing")]})
        bridge.configure_settings({"DefaultStartTime": "06:00"})
        service = _make_service(bridge)

        await service.edit_task(EditTaskCommand(id="task-001", defer_date="2026-07-15"))

        params = _get_edit_task_params(bridge)
        assert params["deferDate"] == "2026-07-15T06:00:00"

    async def test_edit_date_only_planned_date_uses_preference_default_time(self) -> None:
        """date-only plannedDate in edit_task reaches bridge with DefaultPlannedTime."""
        bridge = InMemoryBridge(data={"tasks": [make_task_dict(id="task-001", name="Existing")]})
        bridge.configure_settings({"DefaultPlannedTime": "14:00"})
        service = _make_service(bridge)

        await service.edit_task(EditTaskCommand(id="task-001", planned_date="2026-07-15"))

        params = _get_edit_task_params(bridge)
        assert params["plannedDate"] == "2026-07-15T14:00:00"

    async def test_edit_all_three_fields_each_get_field_specific_time(self) -> None:
        """All three date-only fields in one EditTask get field-specific times (PREF-07)."""
        bridge = InMemoryBridge(data={"tasks": [make_task_dict(id="task-001", name="Existing")]})
        bridge.configure_settings(
            {
                "DefaultDueTime": "20:00",
                "DefaultStartTime": "07:00",
                "DefaultPlannedTime": "12:00",
            }
        )
        service = _make_service(bridge)

        await service.edit_task(
            EditTaskCommand(
                id="task-001",
                due_date="2026-07-15",
                defer_date="2026-07-10",
                planned_date="2026-07-12",
            )
        )

        params = _get_edit_task_params(bridge)
        assert params["dueDate"] == "2026-07-15T20:00:00", "dueDate should use DefaultDueTime"
        assert params["deferDate"] == "2026-07-10T07:00:00", "deferDate should use DefaultStartTime"
        assert params["plannedDate"] == "2026-07-12T12:00:00", (
            "plannedDate should use DefaultPlannedTime"
        )
