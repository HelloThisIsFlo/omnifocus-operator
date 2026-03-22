"""Golden master fixtures and comparison helpers for bridge contract tests."""

from tests.golden_master.normalize import (
    DYNAMIC_PROJECT_FIELDS,
    DYNAMIC_TAG_FIELDS,
    DYNAMIC_TASK_FIELDS,
    filter_to_known_ids,
    normalize_for_comparison,
    normalize_response,
    normalize_state,
)

__all__ = [
    "DYNAMIC_PROJECT_FIELDS",
    "DYNAMIC_TAG_FIELDS",
    "DYNAMIC_TASK_FIELDS",
    "filter_to_known_ids",
    "normalize_for_comparison",
    "normalize_response",
    "normalize_state",
]
