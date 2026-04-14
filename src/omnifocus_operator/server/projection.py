"""Response shaping: stripping, field projection, and list response assembly.

Stripping removes noise from entity dicts (null, [], "", false, "none").
Projection selects which fields the agent sees (include groups / only fields).
Both operate on model_dump(by_alias=True) output dicts -- pure dict transforms.
"""

from __future__ import annotations

from typing import TYPE_CHECKING, Any

if TYPE_CHECKING:
    from collections.abc import Sequence

    from omnifocus_operator.contracts.use_cases.list.common import ListResult
    from omnifocus_operator.models.base import OmniFocusBaseModel

# -- Stripping constants (STRIP-01, STRIP-02) ---------------------------------

NEVER_STRIP: frozenset[str] = frozenset({"availability"})
"""Keys excluded from stripping regardless of value."""

_STRIP_HASHABLE: frozenset[Any] = frozenset({None, "", False, "none"})
"""Hashable values that cause a key to be stripped."""


def _is_strip_value(v: Any) -> bool:
    """Return True if value should be stripped from an entity dict."""
    # Lists are unhashable -- check empty list explicitly, non-empty lists are kept
    if isinstance(v, list):
        return len(v) == 0
    # Dicts and other unhashable types are never stripped
    if isinstance(v, dict):
        return False
    return v in _STRIP_HASHABLE


# -- Stripping functions -------------------------------------------------------


def strip_entity(entity: dict[str, Any]) -> dict[str, Any]:
    """Remove keys whose values are in STRIP_VALUES, except NEVER_STRIP keys.

    Operates on a single entity dict (post model_dump).
    """
    return {k: v for k, v in entity.items() if k in NEVER_STRIP or not _is_strip_value(v)}


def strip_all_entities(data: dict[str, Any]) -> dict[str, Any]:
    """Strip each entity in a get_all response (tasks, projects, tags, folders, perspectives).

    Returns a new dict with the same structure but stripped entity dicts.
    """
    result: dict[str, Any] = {}
    for key, value in data.items():
        if isinstance(value, list):
            result[key] = [strip_entity(item) if isinstance(item, dict) else item for item in value]
        else:
            result[key] = value
    return result


# -- Field projection (FSEL-01 through FSEL-08) -------------------------------


def resolve_fields(
    *,
    include: Sequence[str],
    only: Sequence[str],
    default_fields: frozenset[str],
    field_groups: dict[str, frozenset[str]],
) -> tuple[frozenset[str], list[str]]:
    """Resolve which fields to keep after stripping.

    Returns (allowed_fields, warnings).

    Rules:
    - No include, no only -> default_fields (default projection)
    - include adds group fields to defaults
    - include: ["*"] returns all fields (defaults + all groups)
    - only returns exact fields + id (always included)
    - include + only conflict: only wins, include ignored, warning added (D-06)
    - Invalid only field names: case-insensitive lookup, warning per unrecognized name
    """
    warnings: list[str] = []

    # All valid field names (union of defaults + all groups)
    all_fields = default_fields | frozenset().union(*field_groups.values())

    # Conflict: only takes precedence (D-06)
    if include and only:
        warnings.append(
            "'include' and 'only' are mutually exclusive. "
            "'include' was ignored because 'only' was provided. "
            "Use one or the other."
        )
        return _resolve_only(only, all_fields, warnings)

    if only:
        return _resolve_only(only, all_fields, warnings)

    # include handling (empty include → defaults only)
    return _resolve_include(include, default_fields, field_groups, all_fields, warnings)


def _resolve_only(
    only: Sequence[str],
    all_fields: frozenset[str],
    warnings: list[str],
) -> tuple[frozenset[str], list[str]]:
    """Resolve `only` field selection: exact fields + id, case-insensitive."""
    # Build case-insensitive lookup: lowercase -> original field name
    lower_to_original: dict[str, str] = {f.lower(): f for f in all_fields}

    resolved: set[str] = {"id"}  # id always included
    for name in only:
        original = lower_to_original.get(name.lower())
        if original is not None:
            resolved.add(original)
        else:
            warnings.append(
                f"Unknown field '{name}' in only — ignored. "
                f"Valid fields are listed in the tool description."
            )

    return frozenset(resolved), warnings


def _resolve_include(
    include: Sequence[str],
    default_fields: frozenset[str],
    field_groups: dict[str, frozenset[str]],
    all_fields: frozenset[str],
    warnings: list[str],
) -> tuple[frozenset[str], list[str]]:
    """Resolve `include` group selection: defaults + requested groups."""
    if "*" in include:
        return all_fields, warnings

    result = set(default_fields)
    for group_name in include:
        group = field_groups.get(group_name)
        if group is not None:
            result |= group
        # Invalid include group names are caught by Pydantic Literal validation
        # before reaching here (FSEL-04), so no warning needed.

    return frozenset(result), warnings


# -- Entity projection ---------------------------------------------------------


def project_entity(entity: dict[str, Any], allowed_fields: frozenset[str]) -> dict[str, Any]:
    """Keep only allowed_fields keys in an entity dict."""
    return {k: v for k, v in entity.items() if k in allowed_fields}


# -- List response shaping (full pipeline) -------------------------------------


def shape_list_response[T: OmniFocusBaseModel](
    result: ListResult[T],
    *,
    include: Sequence[str],
    only: Sequence[str],
    default_fields: frozenset[str],
    field_groups: dict[str, frozenset[str]],
    warnings_from_service: list[str] | None = None,
) -> dict[str, Any]:
    """Full pipeline: serialize, strip, project, reassemble envelope.

    1. Serialize each item via model_dump(by_alias=True)
    2. Strip each entity dict
    3. Resolve fields and project
    4. Build envelope: {items, total, hasMore}
    5. If warnings exist (service + projection), add warnings list
    """
    # 1. Serialize
    items = [item.model_dump(by_alias=True) for item in result.items]

    # 2. Strip
    items = [strip_entity(item) for item in items]

    # 3. Resolve and project
    allowed_fields, projection_warnings = resolve_fields(
        include=include,
        only=only,
        default_fields=default_fields,
        field_groups=field_groups,
    )
    items = [project_entity(item, allowed_fields) for item in items]

    # 4. Build envelope
    envelope: dict[str, Any] = {
        "items": items,
        "total": result.total,
        "hasMore": result.has_more,
    }

    # 5. Collect warnings
    all_warnings: list[str] = []
    if warnings_from_service:
        all_warnings.extend(warnings_from_service)
    if result.warnings:
        all_warnings.extend(result.warnings)
    all_warnings.extend(projection_warnings)

    if all_warnings:
        envelope["warnings"] = all_warnings

    return envelope


def shape_list_response_strip_only[T: OmniFocusBaseModel](
    result: ListResult[T],
) -> dict[str, Any]:
    """Strip items only (no field selection). For list_tags, list_folders, list_perspectives."""
    items = [strip_entity(item.model_dump(by_alias=True)) for item in result.items]
    envelope: dict[str, Any] = {
        "items": items,
        "total": result.total,
        "hasMore": result.has_more,
    }
    if result.warnings:
        envelope["warnings"] = result.warnings
    return envelope
