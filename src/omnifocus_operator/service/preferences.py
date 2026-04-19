"""OmniFocus preferences — lazy-loaded, cached, domain-typed settings.

Reads date-related preferences from OmniFocus via the bridge ``get_settings``
command. Caches values for the server's lifetime (restart to refresh).

Falls back to OmniFocus factory defaults with a warning when the bridge
is unavailable.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, ClassVar

from omnifocus_operator.agent_messages.warnings import (
    SETTINGS_FALLBACK_WARNING,
    SETTINGS_UNKNOWN_DUE_SOON_PAIR,
)
from omnifocus_operator.models.enums import DueSoonSetting

if TYPE_CHECKING:
    from omnifocus_operator.contracts.protocols import Bridge

logger = logging.getLogger(__name__)

__all__ = ["OmniFocusPreferences"]


class OmniFocusPreferences:
    """Domain-typed OmniFocus preferences with lazy load and cache.

    Consumers get ``DueSoonSetting`` enums and normalized time strings —
    never raw bridge interval/granularity values.
    """

    _FACTORY_DEFAULTS: ClassVar[dict[str, Any]] = {
        "DefaultDueTime": "17:00",
        "DefaultStartTime": "00:00",
        "DefaultPlannedTime": "09:00",
        "DueSoonInterval": 172800,
        "DueSoonGranularity": 1,
        # Task-property defaults. Absence in the OF Setting store means the
        # user kept the factory default — resolve to these explicit values.
        # Raw bool storage; the task-type getter translates to "parallel" /
        # "sequential" at read time.
        "OFMCompleteWhenLastItemComplete": True,
        "OFMTaskDefaultSequential": False,
    }

    # Maps (interval_seconds, granularity) -> DueSoonSetting enum member.
    # Migrated from repository/hybrid/hybrid.py.
    _SETTING_MAP: ClassVar[dict[tuple[int, int], DueSoonSetting]] = {
        (86400, 1): DueSoonSetting.TODAY,
        (86400, 0): DueSoonSetting.TWENTY_FOUR_HOURS,
        (172800, 1): DueSoonSetting.TWO_DAYS,
        (259200, 1): DueSoonSetting.THREE_DAYS,
        (345600, 1): DueSoonSetting.FOUR_DAYS,
        (432000, 1): DueSoonSetting.FIVE_DAYS,
        (604800, 1): DueSoonSetting.ONE_WEEK,
    }

    # Maps domain field names to OmniFocus settings keys.
    _DEFAULT_TIME_MAP: ClassVar[dict[str, str]] = {
        "due_date": "DefaultDueTime",
        "defer_date": "DefaultStartTime",
        "planned_date": "DefaultPlannedTime",
    }

    def __init__(self, bridge: Bridge) -> None:
        self._bridge = bridge
        self._loaded = False
        self._warnings: list[str] = []

        # Initialize with factory defaults (used as fallback on bridge failure)
        defaults = self._FACTORY_DEFAULTS
        self._due_soon = self._SETTING_MAP[
            (
                defaults["DueSoonInterval"],
                defaults["DueSoonGranularity"],
            )
        ]
        self._default_due_time = self._normalize_time(defaults["DefaultDueTime"])
        self._default_start_time = self._normalize_time(defaults["DefaultStartTime"])
        self._default_planned_time = self._normalize_time(defaults["DefaultPlannedTime"])

        # Task-property defaults (stored as domain-ready values, not raw bools)
        self._complete_with_children_default: bool = bool(
            defaults["OFMCompleteWhenLastItemComplete"]
        )
        self._task_type_default: str = (
            "sequential" if defaults["OFMTaskDefaultSequential"] else "parallel"
        )

    @staticmethod
    def _normalize_time(raw: str) -> str:
        """Normalize time string to HH:MM:SS format.

        OmniJS returns times inconsistently: "19:00:00" (HH:MM:SS) or "09:00" (HH:MM).
        This ensures a consistent HH:MM:SS output.
        """
        parts = raw.split(":")
        if len(parts) == 2:
            return f"{parts[0]}:{parts[1]}:00"
        return raw

    async def _ensure_loaded(self) -> None:
        """Load settings from bridge on first call. Cached thereafter.

        Sets ``_loaded = True`` before the bridge call to prevent re-entry
        loops on failure (T-50-02 mitigation).
        """
        if self._loaded:
            return

        self._loaded = True  # Before bridge call — prevents re-entry on failure

        try:
            raw = await self._bridge.send_command("get_settings")
        except Exception:
            logger.warning("Failed to read OmniFocus preferences; using factory defaults")
            self._warnings.append(SETTINGS_FALLBACK_WARNING)
            return

        self._apply(raw)

    def _apply(self, raw: dict[str, Any]) -> None:
        """Apply raw bridge settings to cached instance fields."""
        # Time settings
        time_fields = {
            "DefaultDueTime": "_default_due_time",
            "DefaultStartTime": "_default_start_time",
            "DefaultPlannedTime": "_default_planned_time",
        }
        for settings_key, attr_name in time_fields.items():
            if settings_key in raw:
                setattr(self, attr_name, self._normalize_time(str(raw[settings_key])))

        # DueSoon setting
        interval = raw.get("DueSoonInterval")
        granularity = raw.get("DueSoonGranularity")
        if interval is not None and granularity is not None:
            key = (int(interval), int(granularity))
            setting = self._SETTING_MAP.get(key)
            if setting is not None:
                self._due_soon = setting
            else:
                logger.warning(
                    "Unknown DueSoon pair (%s, %s); using factory default TWO_DAYS",
                    interval,
                    granularity,
                )
                self._warnings.append(SETTINGS_UNKNOWN_DUE_SOON_PAIR)
                # Keep factory default (TWO_DAYS)

        # OFMCompleteWhenLastItemComplete — absence means user kept factory
        # default (True). Type-coerce to bool to guard against garbage
        # (T-56-01 tampering mitigation).
        if (
            "OFMCompleteWhenLastItemComplete" in raw
            and raw["OFMCompleteWhenLastItemComplete"] is not None
        ):
            self._complete_with_children_default = bool(raw["OFMCompleteWhenLastItemComplete"])

        # OFMTaskDefaultSequential — absence means user kept factory default
        # ("parallel"). OF Setting store typically omits this key unless the
        # user has flipped it away from factory default.
        if "OFMTaskDefaultSequential" in raw and raw["OFMTaskDefaultSequential"] is not None:
            self._task_type_default = (
                "sequential" if bool(raw["OFMTaskDefaultSequential"]) else "parallel"
            )

    async def get_due_soon_setting(self) -> DueSoonSetting:
        """Return the DueSoonSetting enum for the user's OmniFocus preference."""
        await self._ensure_loaded()
        return self._due_soon

    async def get_default_time(self, field: str) -> str:
        """Return the normalized default time (HH:MM:SS) for a date field.

        Args:
            field: One of ``"due_date"``, ``"defer_date"``, ``"planned_date"``.

        Raises:
            ValueError: If *field* is not a recognized date field name.
        """
        await self._ensure_loaded()

        attr_map = {
            "due_date": self._default_due_time,
            "defer_date": self._default_start_time,
            "planned_date": self._default_planned_time,
        }
        if field not in attr_map:
            msg = f"Unknown date field: {field!r}. Expected one of: {', '.join(attr_map)}"
            raise ValueError(msg)
        return attr_map[field]

    async def get_complete_with_children_default(self) -> bool:
        """Return the user's ``OFMCompleteWhenLastItemComplete`` preference.

        OmniFocus factory default is ``True``. When the OF Setting store
        omits the key (user has not changed it from factory default) or
        the bridge fails, this returns ``True``.
        """
        await self._ensure_loaded()
        return self._complete_with_children_default

    async def get_task_type_default(self) -> str:
        """Return ``"parallel"`` or ``"sequential"`` per ``OFMTaskDefaultSequential``.

        OmniFocus factory default is ``"parallel"`` (the Setting store
        typically omits ``OFMTaskDefaultSequential`` until the user flips
        it). When the key is absent or the bridge fails, returns
        ``"parallel"``.
        """
        await self._ensure_loaded()
        return self._task_type_default

    async def get_warnings(self) -> list[str]:
        """Return accumulated warnings from settings loading."""
        await self._ensure_loaded()
        return list(self._warnings)
