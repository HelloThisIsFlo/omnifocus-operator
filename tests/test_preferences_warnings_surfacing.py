"""Tests for PREF-03: Preferences warnings surface to agent responses.

When preferences loading fails (bridge error) or produces warnings (unknown
DueSoon pair), those warnings must reach the agent through the result's
`warnings` field — not just logs.

This test file verifies that all pipelines calling preferences methods
drain warnings via `get_warnings()` and include them in results.
"""

from __future__ import annotations

from typing import Any

from omnifocus_operator.agent_messages.warnings import (
    SETTINGS_FALLBACK_WARNING,
    SETTINGS_UNKNOWN_DUE_SOON_PAIR,
)
from omnifocus_operator.contracts.use_cases.add.tasks import AddTaskCommand
from omnifocus_operator.contracts.use_cases.edit.tasks import EditTaskCommand
from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery
from omnifocus_operator.repository import BridgeOnlyRepository
from omnifocus_operator.service import OperatorService
from omnifocus_operator.service.preferences import OmniFocusPreferences
from tests.doubles import ConstantMtimeSource
from tests.doubles.bridge import InMemoryBridge

from .conftest import make_task_dict


class FailingSettingsBridge(InMemoryBridge):
    """Bridge that fails only for get_settings, simulating OmniFocus not running.

    This allows testing that preferences fallback warnings flow through to
    pipeline results when the bridge is partially unavailable.
    """

    async def send_command(
        self, operation: str, params: dict[str, Any] | None = None
    ) -> dict[str, Any]:
        if operation == "get_settings":
            raise RuntimeError("OmniFocus not running")
        return await super().send_command(operation, params)


class UnknownDueSoonBridge(InMemoryBridge):
    """Bridge that returns an unknown DueSoon (interval, granularity) pair.

    Triggers SETTINGS_UNKNOWN_DUE_SOON_PAIR warning.
    """

    def __init__(self, **kwargs: Any) -> None:
        super().__init__(**kwargs)
        # Configure an unknown pair that maps to nothing
        self.configure_settings({"DueSoonInterval": 999999, "DueSoonGranularity": 1})


def _make_service(bridge: InMemoryBridge) -> OperatorService:
    """Build OperatorService with the given bridge."""
    repo = BridgeOnlyRepository(bridge=bridge, mtime_source=ConstantMtimeSource())
    preferences = OmniFocusPreferences(bridge)
    return OperatorService(repository=repo, preferences=preferences)


# ---------------------------------------------------------------------------
# PREF-03: add_task surfaces preferences fallback warning
# ---------------------------------------------------------------------------


class TestAddTaskSurfacesPreferencesWarnings:
    """AddTask pipeline includes preferences warnings in result."""

    async def test_fallback_warning_surfaces_in_add_task_result(self) -> None:
        """When get_settings fails, SETTINGS_FALLBACK_WARNING appears in AddTaskResult.warnings."""
        bridge = FailingSettingsBridge()
        service = _make_service(bridge)

        # Use date-only to trigger preferences call for default time
        result = await service.add_task(AddTaskCommand(name="Test task", due_date="2026-07-15"))

        assert result.status == "success"
        assert result.warnings is not None
        assert SETTINGS_FALLBACK_WARNING in result.warnings


# ---------------------------------------------------------------------------
# PREF-03: edit_task surfaces preferences fallback warning
# ---------------------------------------------------------------------------


class TestEditTaskSurfacesPreferencesWarnings:
    """EditTask pipeline includes preferences warnings in result."""

    async def test_fallback_warning_surfaces_in_edit_task_result(self) -> None:
        """When get_settings fails, SETTINGS_FALLBACK_WARNING appears in EditTaskResult.warnings."""
        bridge = FailingSettingsBridge(
            data={"tasks": [make_task_dict(id="task-001", name="Existing")]}
        )
        service = _make_service(bridge)

        # Use date-only to trigger preferences call for default time
        result = await service.edit_task(EditTaskCommand(id="task-001", due_date="2026-07-15"))

        assert result.status == "success"
        assert result.warnings is not None
        assert SETTINGS_FALLBACK_WARNING in result.warnings


# ---------------------------------------------------------------------------
# PREF-03: list_tasks surfaces preferences warning (due="soon" trigger)
# ---------------------------------------------------------------------------


class TestListTasksSurfacesPreferencesWarnings:
    """ListTasks pipeline includes preferences warnings in result."""

    async def test_unknown_due_soon_warning_surfaces_in_list_tasks_result(self) -> None:
        """Unknown DueSoon pair -> SETTINGS_UNKNOWN_DUE_SOON_PAIR in result.warnings."""
        bridge = UnknownDueSoonBridge()
        service = _make_service(bridge)

        # Use due="soon" to trigger get_due_soon_setting() call
        result = await service.list_tasks(ListTasksQuery(due="soon"))

        assert result.warnings is not None
        assert SETTINGS_UNKNOWN_DUE_SOON_PAIR in result.warnings

    async def test_fallback_warning_surfaces_in_list_tasks_result(self) -> None:
        """Bridge failure during due='soon' -> SETTINGS_FALLBACK_WARNING in result."""
        bridge = FailingSettingsBridge()
        service = _make_service(bridge)

        # Use due="soon" to trigger get_due_soon_setting() call
        result = await service.list_tasks(ListTasksQuery(due="soon"))

        assert result.warnings is not None
        assert SETTINGS_FALLBACK_WARNING in result.warnings
