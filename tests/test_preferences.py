"""Tests for OmniFocusPreferences: lazy load, caching, fallback, domain-typed settings."""

from __future__ import annotations

import pytest

from omnifocus_operator.agent_messages.warnings import (
    SETTINGS_FALLBACK_WARNING,
    SETTINGS_UNKNOWN_DUE_SOON_PAIR,
)
from omnifocus_operator.models.enums import DueSoonSetting
from omnifocus_operator.service.preferences import OmniFocusPreferences
from tests.doubles.bridge import InMemoryBridge

# ---------------------------------------------------------------------------
# Happy path: bridge returns user values
# ---------------------------------------------------------------------------


class TestPreferencesLoadsFromBridge:
    """OmniFocusPreferences loads settings from bridge and maps to domain types."""

    async def test_due_soon_maps_to_correct_enum(self) -> None:
        """Bridge (86400, 1) -> DueSoonSetting.TODAY."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DueSoonInterval": 86400, "DueSoonGranularity": 1})
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_due_soon_setting()

        assert result is DueSoonSetting.TODAY

    async def test_due_soon_factory_default_is_two_days(self) -> None:
        """Factory defaults (172800, 1) -> DueSoonSetting.TWO_DAYS."""
        bridge = InMemoryBridge()
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_due_soon_setting()

        assert result is DueSoonSetting.TWO_DAYS

    async def test_all_seven_due_soon_mappings(self) -> None:
        """Every known (interval, granularity) pair maps to the correct enum member."""
        cases = [
            (86400, 1, DueSoonSetting.TODAY),
            (86400, 0, DueSoonSetting.TWENTY_FOUR_HOURS),
            (172800, 1, DueSoonSetting.TWO_DAYS),
            (259200, 1, DueSoonSetting.THREE_DAYS),
            (345600, 1, DueSoonSetting.FOUR_DAYS),
            (432000, 1, DueSoonSetting.FIVE_DAYS),
            (604800, 1, DueSoonSetting.ONE_WEEK),
        ]
        for interval, granularity, expected in cases:
            bridge = InMemoryBridge()
            bridge.configure_settings(
                {"DueSoonInterval": interval, "DueSoonGranularity": granularity}
            )
            prefs = OmniFocusPreferences(bridge)
            result = await prefs.get_due_soon_setting()
            assert result is expected, f"({interval}, {granularity}) should map to {expected}"

    async def test_time_string_normalized_from_hhmmss(self) -> None:
        """Bridge returns 'HH:MM:SS' -> preserved as-is."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultDueTime": "19:00:00"})
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_default_time("due_date")

        assert result == "19:00:00"


# ---------------------------------------------------------------------------
# Lazy loading + caching
# ---------------------------------------------------------------------------


class TestPreferencesLazyAndCached:
    """Settings loaded lazily on first call, cached thereafter."""

    async def test_first_call_triggers_bridge(self) -> None:
        """First get_due_soon_setting() calls bridge.send_command."""
        bridge = InMemoryBridge()
        prefs = OmniFocusPreferences(bridge)

        await prefs.get_due_soon_setting()

        settings_calls = [c for c in bridge.calls if c.operation == "get_settings"]
        assert len(settings_calls) == 1

    async def test_second_call_does_not_trigger_bridge(self) -> None:
        """Second call uses cached value -- no additional bridge call."""
        bridge = InMemoryBridge()
        prefs = OmniFocusPreferences(bridge)

        await prefs.get_due_soon_setting()
        await prefs.get_due_soon_setting()

        settings_calls = [c for c in bridge.calls if c.operation == "get_settings"]
        assert len(settings_calls) == 1

    async def test_get_default_time_also_cached(self) -> None:
        """get_default_time uses the same cached load as get_due_soon_setting."""
        bridge = InMemoryBridge()
        prefs = OmniFocusPreferences(bridge)

        await prefs.get_due_soon_setting()
        await prefs.get_default_time("due_date")

        settings_calls = [c for c in bridge.calls if c.operation == "get_settings"]
        assert len(settings_calls) == 1


# ---------------------------------------------------------------------------
# Fallback: bridge failure -> factory defaults + warning
# ---------------------------------------------------------------------------


class TestPreferencesFallback:
    """When bridge fails, factory defaults are used with a warning."""

    async def test_bridge_error_returns_factory_default_due_soon(self) -> None:
        """Bridge raises -> DueSoonSetting.TWO_DAYS (factory default)."""
        bridge = InMemoryBridge()
        bridge.set_error(RuntimeError("OmniFocus not running"))
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_due_soon_setting()

        assert result is DueSoonSetting.TWO_DAYS

    async def test_bridge_error_returns_factory_default_time(self) -> None:
        """Bridge raises -> factory default times."""
        bridge = InMemoryBridge()
        bridge.set_error(RuntimeError("OmniFocus not running"))
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_default_time("due_date") == "17:00:00"
        assert await prefs.get_default_time("defer_date") == "00:00:00"
        assert await prefs.get_default_time("planned_date") == "09:00:00"

    async def test_bridge_error_emits_warning(self) -> None:
        """Bridge raises -> SETTINGS_FALLBACK_WARNING in warnings."""
        bridge = InMemoryBridge()
        bridge.set_error(RuntimeError("OmniFocus not running"))
        prefs = OmniFocusPreferences(bridge)

        await prefs.get_due_soon_setting()
        warnings = await prefs.get_warnings()

        assert SETTINGS_FALLBACK_WARNING in warnings

    async def test_bridge_error_does_not_retry(self) -> None:
        """After failure, _loaded stays True -- no re-entry."""
        bridge = InMemoryBridge()
        bridge.set_error(RuntimeError("OmniFocus not running"))
        prefs = OmniFocusPreferences(bridge)

        await prefs.get_due_soon_setting()
        bridge.clear_error()
        await prefs.get_due_soon_setting()

        # Still only one call -- the failed one
        settings_calls = [c for c in bridge.calls if c.operation == "get_settings"]
        assert len(settings_calls) == 1


# ---------------------------------------------------------------------------
# Unknown DueSoon pair -> fallback + warning
# ---------------------------------------------------------------------------


class TestPreferencesUnknownDueSoonPair:
    """Unknown (interval, granularity) pair falls back to TWO_DAYS + warning."""

    async def test_unknown_pair_returns_two_days(self) -> None:
        """Unrecognized (999999, 1) -> TWO_DAYS."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DueSoonInterval": 999999, "DueSoonGranularity": 1})
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_due_soon_setting()

        assert result is DueSoonSetting.TWO_DAYS

    async def test_unknown_pair_emits_warning(self) -> None:
        """Unrecognized pair emits SETTINGS_UNKNOWN_DUE_SOON_PAIR."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DueSoonInterval": 999999, "DueSoonGranularity": 1})
        prefs = OmniFocusPreferences(bridge)

        await prefs.get_due_soon_setting()
        warnings = await prefs.get_warnings()

        assert SETTINGS_UNKNOWN_DUE_SOON_PAIR in warnings


# ---------------------------------------------------------------------------
# Time normalization: HH:MM -> HH:MM:SS
# ---------------------------------------------------------------------------


class TestPreferencesTimeNormalization:
    """Time strings normalized: both 'HH:MM:SS' and 'HH:MM' produce 'HH:MM:SS'."""

    async def test_hhmm_padded_to_hhmmss(self) -> None:
        """'09:00' -> '09:00:00'."""
        bridge = InMemoryBridge()
        # Factory default for DefaultPlannedTime is "09:00" (HH:MM)
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_default_time("planned_date")

        assert result == "09:00:00"

    async def test_hhmmss_stays_hhmmss(self) -> None:
        """'19:00:00' stays '19:00:00'."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultDueTime": "19:00:00"})
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_default_time("due_date")

        assert result == "19:00:00"

    async def test_factory_default_due_time_normalized(self) -> None:
        """Factory default '17:00' -> '17:00:00'."""
        bridge = InMemoryBridge()
        prefs = OmniFocusPreferences(bridge)

        result = await prefs.get_default_time("due_date")

        assert result == "17:00:00"


# ---------------------------------------------------------------------------
# Default time mapping: field name -> settings key
# ---------------------------------------------------------------------------


class TestPreferencesDefaultTimeMapping:
    """get_default_time maps field names to correct OmniFocus settings keys."""

    async def test_due_date_maps_to_default_due_time(self) -> None:
        """'due_date' -> DefaultDueTime."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultDueTime": "19:00:00"})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_default_time("due_date") == "19:00:00"

    async def test_defer_date_maps_to_default_start_time(self) -> None:
        """'defer_date' -> DefaultStartTime."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultStartTime": "08:00:00"})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_default_time("defer_date") == "08:00:00"

    async def test_planned_date_maps_to_default_planned_time(self) -> None:
        """'planned_date' -> DefaultPlannedTime."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"DefaultPlannedTime": "10:30:00"})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_default_time("planned_date") == "10:30:00"

    async def test_unknown_field_raises_value_error(self) -> None:
        """Unknown field name raises ValueError."""
        bridge = InMemoryBridge()
        prefs = OmniFocusPreferences(bridge)

        with pytest.raises(ValueError, match="Unknown date field"):
            await prefs.get_default_time("unknown_field")


# ---------------------------------------------------------------------------
# Task-property preference keys: completesWithChildren + task type default
# ---------------------------------------------------------------------------


class TestPreferencesNewTaskPropertyKeys:
    """OFMCompleteWhenLastItemComplete + OFMTaskDefaultSequential surface as
    ``get_complete_with_children_default()`` / ``get_task_type_default()`` with
    OF factory-default fallback when the bridge omits (or lacks) the key.
    """

    # --- OFMCompleteWhenLastItemComplete ----------------------------------

    async def test_complete_with_children_true_when_bridge_returns_true(self) -> None:
        """Bridge returns True -> getter returns True."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"OFMCompleteWhenLastItemComplete": True})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_complete_with_children_default() is True

    async def test_complete_with_children_false_when_bridge_returns_false(self) -> None:
        """Bridge returns False -> getter returns False."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"OFMCompleteWhenLastItemComplete": False})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_complete_with_children_default() is False

    async def test_complete_with_children_factory_default_when_key_absent(self) -> None:
        """Key absent (user kept factory default) -> True."""
        bridge = InMemoryBridge()
        bridge._settings.pop("OFMCompleteWhenLastItemComplete", None)
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_complete_with_children_default() is True

    async def test_complete_with_children_factory_default_when_key_none(self) -> None:
        """Key present but ``None`` (bridge null) -> factory default True."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"OFMCompleteWhenLastItemComplete": None})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_complete_with_children_default() is True

    # --- OFMTaskDefaultSequential -----------------------------------------

    async def test_task_type_sequential_when_bridge_returns_true(self) -> None:
        """Bridge returns True -> 'sequential'."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"OFMTaskDefaultSequential": True})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_task_type_default() == "sequential"

    async def test_task_type_parallel_when_bridge_returns_false(self) -> None:
        """Bridge returns False -> 'parallel'."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"OFMTaskDefaultSequential": False})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_task_type_default() == "parallel"

    async def test_task_type_factory_default_parallel_when_key_absent(self) -> None:
        """Key absent (user kept factory default) -> 'parallel'."""
        bridge = InMemoryBridge()
        bridge._settings.pop("OFMTaskDefaultSequential", None)
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_task_type_default() == "parallel"

    async def test_task_type_factory_default_parallel_when_key_none(self) -> None:
        """Key present but ``None`` (bridge null) -> factory default 'parallel'."""
        bridge = InMemoryBridge()
        bridge.configure_settings({"OFMTaskDefaultSequential": None})
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_task_type_default() == "parallel"

    # --- Lazy-load-once invariant (PREFS-04) ------------------------------

    async def test_single_bridge_call_for_many_getter_invocations(self) -> None:
        """All five preference getters share the same cached load: only one
        ``get_settings`` bridge call regardless of invocation count/order.
        """
        bridge = InMemoryBridge()
        prefs = OmniFocusPreferences(bridge)

        await prefs.get_complete_with_children_default()
        await prefs.get_task_type_default()
        await prefs.get_due_soon_setting()
        await prefs.get_default_time("due_date")
        # Second round: still one load.
        await prefs.get_complete_with_children_default()
        await prefs.get_task_type_default()

        settings_calls = [c for c in bridge.calls if c.operation == "get_settings"]
        assert len(settings_calls) == 1

    # --- Bridge failure fallback ------------------------------------------

    async def test_fallback_to_factory_defaults_when_bridge_raises(self) -> None:
        """Bridge raises -> both new getters return factory defaults
        (True / 'parallel') and SETTINGS_FALLBACK_WARNING is emitted.
        """
        bridge = InMemoryBridge()
        bridge.set_error(RuntimeError("OmniFocus not running"))
        prefs = OmniFocusPreferences(bridge)

        assert await prefs.get_complete_with_children_default() is True
        assert await prefs.get_task_type_default() == "parallel"

        warnings = await prefs.get_warnings()
        assert SETTINGS_FALLBACK_WARNING in warnings
