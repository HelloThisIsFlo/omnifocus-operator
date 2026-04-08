"""Application configuration -- hard-coded defaults and tunable parameters."""

from __future__ import annotations

from dataclasses import dataclass

from pydantic import field_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

from omnifocus_operator.contracts.use_cases.list._enums import (
    DueSoonSetting,  # noqa: TC001 — Pydantic needs this at runtime
)
from omnifocus_operator.models.enums import EntityType

# -- Default pagination --------------------------------------------------------
# Maximum items returned by list tools when no explicit limit is provided.
# Agents can override with limit=null to get all results.
DEFAULT_LIST_LIMIT: int = 50

# -- Fuzzy matching (used by DomainLogic.suggest_close_matches) ---------------
# Maximum number of suggestions returned for a failed name resolution.
FUZZY_MATCH_MAX_SUGGESTIONS: int = 3
# Minimum similarity ratio (0.0-1.0) for a name to be considered a match.
FUZZY_MATCH_CUTOFF: float = 0.6


# -- System locations ----------------------------------------------------------
@dataclass(frozen=True)
class SystemLocation:
    """A synthetic location that isn't a real OmniFocus entity."""

    id: str
    name: str
    type: EntityType


SYSTEM_LOCATION_PREFIX: str = "$"

SYSTEM_LOCATIONS: dict[str, SystemLocation] = {
    "inbox": SystemLocation(id="$inbox", name="Inbox", type=EntityType.PROJECT),
}


# -- Centralized settings (pydantic-settings) ---------------------------------


class Settings(BaseSettings):
    """All OPERATOR_* environment variables in one place.

    Each field maps to an env var via the ``OPERATOR_`` prefix.
    For example ``log_level`` reads ``OPERATOR_LOG_LEVEL``.
    """

    model_config = SettingsConfigDict(env_prefix="OPERATOR_")

    log_level: str = "INFO"
    week_start: str = "monday"
    repository: str = "hybrid"
    ipc_dir: str | None = None
    bridge_timeout: float = 10.0
    sqlite_path: str | None = None
    ofocus_path: str | None = None
    due_soon_threshold: DueSoonSetting | None = None

    @field_validator("due_soon_threshold", mode="before")
    @classmethod
    def _validate_due_soon_threshold(cls, value: object) -> DueSoonSetting | None:
        from omnifocus_operator.contracts.use_cases.list._enums import (  # noqa: PLC0415
            DueSoonSetting,
        )

        if value is None:
            return None
        if isinstance(value, DueSoonSetting):
            return value
        if isinstance(value, str):
            try:
                return DueSoonSetting[value.upper()]
            except KeyError:
                valid = ", ".join(m.name for m in DueSoonSetting)
                raise ValueError(
                    f"Invalid OPERATOR_DUE_SOON_THRESHOLD '{value}'. Valid values: {valid}"
                ) from None
        raise ValueError(f"Expected string or None, got {type(value).__name__}")


_settings: Settings | None = None


def get_settings() -> Settings:
    """Return the cached Settings singleton (created on first access)."""
    global _settings
    if _settings is None:
        _settings = Settings()
    return _settings


def reset_settings() -> None:
    """Reset the cached Settings instance (for testing)."""
    global _settings
    _settings = None


# -- Week start configuration ------------------------------------------------
# Affects {this: "w"} calendar alignment in date filters.
# Valid values: "monday", "sunday". Read from OPERATOR_WEEK_START env var.

WEEK_START_MAP: dict[str, int] = {"monday": 0, "sunday": 6}  # Python weekday() values


def get_week_start() -> int:
    """Return Python weekday int for configured week start. Default Monday."""

    raw = get_settings().week_start.lower()
    if raw not in WEEK_START_MAP:
        raise ValueError(f"Invalid OPERATOR_WEEK_START '{raw}' -- use 'monday' or 'sunday'")
    return WEEK_START_MAP[raw]
