---
phase: 53-response-shaping
plan: 03
subsystem: server
tags: [stripping, projection, field-groups, config, response-shaping]
dependency_graph:
  requires:
    - phase: 53-01
      provides: inherited field names on models
    - phase: 53-02
      provides: server/ package structure
  provides:
    - "Field group definitions in config.py (TASK_DEFAULT_FIELDS, PROJECT_DEFAULT_FIELDS, TASK_FIELD_GROUPS, PROJECT_FIELD_GROUPS)"
    - "server/projection.py: strip_entity, strip_all_entities, resolve_fields, project_entity, shape_list_response"
    - "Bidirectional field group enforcement tests"
  affects: [53-04, 53-05]
tech_stack:
  added: []
  patterns:
    - "Pure dict transforms on model_dump(by_alias=True) output"
    - "_is_strip_value helper for unhashable type safety (list/dict)"
    - "Case-insensitive field name lookup via lowercase mapping"
key_files:
  created:
    - src/omnifocus_operator/server/projection.py
    - tests/test_projection.py
  modified:
    - src/omnifocus_operator/config.py
decisions:
  - "Used _is_strip_value helper instead of set membership for STRIP_VALUES — lists are unhashable, need isinstance check before frozenset lookup"
  - "Empty dicts are never stripped — only entity-level values (null, [], '', false, 'none') are stripped"
metrics:
  duration: 5m
  completed: "2026-04-14T14:04:00Z"
  tasks: 2/2
  tests: 2073 passed (32 new)
  files_modified: 3
requirements_completed: [STRIP-01, STRIP-02, STRIP-03, FSEL-02, FSEL-10, FSEL-11, FSEL-12]
---

# Phase 53 Plan 03: Response Shaping Infrastructure Summary

Field group definitions centralized in config.py, stripping/projection/shaping functions in server/projection.py, 32 comprehensive tests with bidirectional model-group enforcement.

## Changes

### Production Code

- **config.py**: Added 4 field group constants — `TASK_DEFAULT_FIELDS` (15 fields), `PROJECT_DEFAULT_FIELDS` (14 fields), `TASK_FIELD_GROUPS` (4 groups: notes/metadata/hierarchy/time), `PROJECT_FIELD_GROUPS` (5 groups: +review). All camelCase names matching model_dump output.
- **server/projection.py**: New module with 6 public functions:
  - `strip_entity()` — removes null/[]/""/ false/"none" from entity dicts, never strips availability (STRIP-01/02)
  - `strip_all_entities()` — applies strip_entity to each entity in get_all collections
  - `resolve_fields()` — resolves include/only to allowed field set with conflict handling (D-06) and case-insensitive matching
  - `project_entity()` — keeps only allowed fields from entity dict
  - `shape_list_response()` — full pipeline: serialize, strip, project, assemble envelope with warnings

### Tests

- **tests/test_projection.py**: 32 tests across 5 classes:
  - `TestStripping` (10): all 5 strip values, availability exception, multiple values, dict preservation, strip_all_entities, envelope fields
  - `TestFieldSelection` (12): include groups, include *, only exact, only+id, conflict, invalid, case-insensitive, project_entity, multiple groups, review group, multiple invalid warnings
  - `TestShapeListResponse` (3): default fields, only projection, warning collection
  - `TestFieldGroupSync` (6): task model<->group sync, project model<->group sync, group fields exist on model, no field in multiple groups — catches drift in both directions

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] STRIP_VALUES set can't contain unhashable list**
- **Found during:** Task 1 GREEN phase
- **Issue:** Plan specified `STRIP_VALUES: set = {None, [], "", False, "none"}` but `[]` is unhashable — Python raises TypeError when constructing the set
- **Fix:** Split into `_STRIP_HASHABLE` frozenset (hashable values) and `_is_strip_value()` helper that checks isinstance(list) for empty list and isinstance(dict) for dicts before frozenset membership
- **Files modified:** src/omnifocus_operator/server/projection.py
- **Commit:** 1dff9ff3

## Decisions Made

- **`_is_strip_value` over set membership**: Lists and dicts are unhashable, so `v in {None, [], ...}` raises TypeError on non-empty lists. The helper function handles type dispatch explicitly: empty list -> strip, non-empty list -> keep, dict -> keep, then hashable frozenset check.

## Verification

- `uv run pytest tests/test_projection.py -q`: 32 passed
- `uv run pytest tests/ -q`: 2073 passed, 97.78% coverage
- `grep "TASK_DEFAULT_FIELDS" src/omnifocus_operator/config.py`: found
- `grep "def strip_entity" src/omnifocus_operator/server/projection.py`: found
- `strip_entity({"availability": "available", "flagged": False})` returns `{"availability": "available"}`

## Self-Check: PASSED

- All 3 key files exist (server/projection.py, tests/test_projection.py, config.py)
- Commit 5bee4e92 exists (Task 1 RED)
- Commit 1dff9ff3 exists (Task 1 GREEN)
- Commit a0bf1a5f exists (Task 2)
- SUMMARY.md exists
