"""Application configuration — hard-coded defaults and tunable parameters."""

import os
from dataclasses import dataclass

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

# -- Week start configuration ------------------------------------------------
# Affects {this: "w"} calendar alignment in date filters.
# Valid values: "monday", "sunday". Read from OPERATOR_WEEK_START env var.

WEEK_START_MAP: dict[str, int] = {"monday": 0, "sunday": 6}  # Python weekday() values


def get_week_start() -> int:
    """Return Python weekday int for configured week start. Default Monday."""

    raw = os.environ.get("OPERATOR_WEEK_START", "monday").lower()
    if raw not in WEEK_START_MAP:
        raise ValueError(f"Invalid OPERATOR_WEEK_START '{raw}' -- use 'monday' or 'sunday'")
    return WEEK_START_MAP[raw]
