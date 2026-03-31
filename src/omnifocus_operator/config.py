"""Application configuration — hard-coded defaults and tunable parameters."""

# -- Fuzzy matching (used by DomainLogic.suggest_close_matches) ---------------
# Maximum number of suggestions returned for a failed name resolution.
FUZZY_MATCH_MAX_SUGGESTIONS: int = 3
# Minimum similarity ratio (0.0-1.0) for a name to be considered a match.
FUZZY_MATCH_CUTOFF: float = 0.6
