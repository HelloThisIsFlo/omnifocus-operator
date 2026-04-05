"""Shared fuzzy matching utilities for name resolution."""

from __future__ import annotations

import difflib
from typing import TYPE_CHECKING

from omnifocus_operator.config import FUZZY_MATCH_CUTOFF, FUZZY_MATCH_MAX_SUGGESTIONS

if TYPE_CHECKING:
    from collections.abc import Sequence

    from omnifocus_operator.service.resolve import _HasIdAndName


def suggest_close_matches(
    value: str,
    entity_names: list[str],
    n: int = FUZZY_MATCH_MAX_SUGGESTIONS,
    cutoff: float = FUZZY_MATCH_CUTOFF,
) -> list[str]:
    """Return close name matches for a failed resolution."""
    return difflib.get_close_matches(value, entity_names, n=n, cutoff=cutoff)


def format_suggestions(
    suggestions: list[str],
    entities: Sequence[_HasIdAndName],
) -> str:
    """Format fuzzy suggestions with IDs: 'name1 (id1), name2 (id2)'."""
    name_to_id = {e.name: e.id for e in entities}
    parts = []
    for name in suggestions:
        eid = name_to_id.get(name, "?")
        parts.append(f"{eid} ({name})")
    return ", ".join(parts)
