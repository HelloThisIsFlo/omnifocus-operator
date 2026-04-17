"""Application configuration -- hard-coded defaults and tunable parameters."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import datetime

from pydantic_settings import BaseSettings, SettingsConfigDict

from omnifocus_operator.models.enums import EntityType

# -- Default pagination --------------------------------------------------------
# Maximum items returned by list tools when no explicit limit is provided.
# Agents can override with limit=null to get all results.
DEFAULT_LIST_LIMIT: int = 50

# -- Batch processing ----------------------------------------------------------
# Maximum items accepted in a single add_tasks or edit_tasks call.
MAX_BATCH_SIZE: int = 50

# Minimum batch size to emit MCP progress notifications from write tools.
# Below this threshold the handlers skip progress entirely.
#
# Observed symptom: Claude Code's MCP client rejects every progress
# notification the server emits with "unknown progressToken" -- even though
# the client itself put that token in the request's _meta.progressToken.
# After N such rejections, the client closes the stdio transport, breaking
# every subsequent tool call in the session.
#
# Precise client-side mechanism NOT verified. It could be that Claude Code
# doesn't register a callback for the tokens it sends, or that it cleans them
# up too eagerly relative to when notifications get dispatched. We can't tell
# from the outside without reading the client source. What we CAN verify:
# fewer emitted notifications -> sessions stay alive longer.
#
# Chosen threshold: single-item calls (the dominant UAT/agent pattern) emit
# zero progress and have zero strike exposure. Larger batches still emit
# intermediate progress since they run long enough for progress UX to matter.
PROGRESS_NOTIFICATION_MIN_BATCH_SIZE: int = 3

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


# -- Field groups for response projection (D-04) --------------------------------
# Field names use camelCase (alias names) -- they operate on model_dump(by_alias=True) output.

TASK_DEFAULT_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "availability",
        "order",
        "project",
        "dueDate",
        "inheritedDueDate",
        "deferDate",
        "inheritedDeferDate",
        "plannedDate",
        "inheritedPlannedDate",
        "flagged",
        "inheritedFlagged",
        "urgency",
        "tags",
    }
)

TASK_FIELD_GROUPS: dict[str, frozenset[str]] = {
    "notes": frozenset({"note"}),
    "metadata": frozenset(
        {
            "added",
            "modified",
            "completionDate",
            "dropDate",
            "inheritedCompletionDate",
            "inheritedDropDate",
            "url",
        }
    ),
    "hierarchy": frozenset({"parent", "hasChildren"}),
    "time": frozenset({"estimatedMinutes", "repetitionRule"}),
}

PROJECT_DEFAULT_FIELDS: frozenset[str] = frozenset(
    {
        "id",
        "name",
        "availability",
        "dueDate",
        "deferDate",
        "plannedDate",
        "flagged",
        "urgency",
        "tags",
    }
)

PROJECT_FIELD_GROUPS: dict[str, frozenset[str]] = {
    "notes": frozenset({"note"}),
    "metadata": frozenset({"added", "modified", "completionDate", "dropDate", "url"}),
    "hierarchy": frozenset({"folder", "hasChildren"}),
    "time": frozenset({"estimatedMinutes", "repetitionRule"}),
    "review": frozenset({"nextReviewDate", "reviewInterval", "lastReviewDate", "nextTask"}),
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
    bridge_timeout: float = 30.0
    sqlite_path: str | None = None
    ofocus_path: str | None = None


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


def local_now() -> datetime:
    """Return current time as a tz-aware local datetime.

    OmniFocus stores all dates as naive local time. The server runs on
    the same Mac. Using local time means the API matches OmniFocus's
    mental model: "5pm" means 5pm, period.

    Returns tz-aware (not naive) so arithmetic with UTC-anchored values
    (CF epoch subtraction in query_builder) works correctly -- Python
    handles the offset automatically in tz-aware subtraction.

    Evidence: timezone deep-dive proved the conversion formula across
    430 tasks in both BST and GMT. See .research/deep-dives/timezone-behavior/
    """
    return datetime.now().astimezone()
