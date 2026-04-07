---
phase: 44-migrate-list-query-filters-to-patch-semantics-eliminate-null
plan: 02
subsystem: contracts, service
tags: [availability-filter, enum, service-translation, patch-semantics]
dependency_graph:
  requires: [44-01]
  provides: [availability-expansion, filter-enum-types, service-unset-translation]
  affects: [service/service.py, contracts/use_cases/list/]
tech_stack:
  added: []
  patterns: [filter-enum-with-ALL, module-level-expansion-helpers]
key_files:
  created:
    - src/omnifocus_operator/contracts/use_cases/list/_enums.py
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/__init__.py
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/projects.py
    - src/omnifocus_operator/contracts/use_cases/list/tags.py
    - src/omnifocus_operator/contracts/use_cases/list/folders.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - src/omnifocus_operator/service/service.py
    - tests/test_list_contracts.py
    - tests/test_list_pipelines.py
    - tests/test_descriptions.py
decisions:
  - Filter enums as separate _enums.py module mirroring core enums plus ALL
  - Module-level expansion helpers (not methods on pipelines) for reuse by inline pass-throughs
  - matches_inbox_name widened to object type for UNSET safety
metrics:
  duration_seconds: 585
  completed: "2026-04-07T14:54:44Z"
  tasks_completed: 2
  tasks_total: 2
  files_created: 1
  files_modified: 11
  tests_added: 25
  tests_total: 1693
---

# Phase 44 Plan 02: AvailabilityFilter Enums and Service Layer Translation Summary

AvailabilityFilter enums with ALL shorthand for ergonomic "include everything" queries, empty-list rejection on all availability fields, and service layer translation from Patch/UNSET to None with availability expansion.

## Commits

| Task | Commit | Description |
|------|--------|-------------|
| 1 | d66b825 | AvailabilityFilter enums with ALL shorthand and empty-list rejection |
| 2 | 1a08e1c | Service layer UNSET translation, availability expansion, matches_inbox_name |

## Task 1: AvailabilityFilter Enums

- Created `_enums.py` with `AvailabilityFilter`, `TagAvailabilityFilter`, `FolderAvailabilityFilter`
- Each mirrors its core enum (Availability, TagAvailability, FolderAvailability) plus `ALL = "all"`
- Updated all 4 query models (tasks, projects, tags, folders) to use filter enums
- RepoQuery models remain unchanged (core enums)
- Added `_reject_empty_availability` field_validator on all 4 query models
- Added `AVAILABILITY_EMPTY` error template in errors.py
- Re-exported filter enums from list `__init__.py`
- 13 new tests covering enum values, re-exports, ALL acceptance, and empty-list rejection

## Task 2: Service Layer Translation

- Added `_expand_availability`, `_expand_tag_availability`, `_expand_folder_availability` module-level helpers
- ALL in filter list expands to full core enum list (e.g., `list(Availability)`)
- Mixed ALL + other values accepted but adds `AVAILABILITY_MIXED_ALL` warning
- Updated `matches_inbox_name` signature from `str | None` to `object` -- `isinstance(value, str)` guard handles UNSET, None, int cleanly
- Updated `_ListProjectsPipeline._check_inbox_search_warning` to pass raw `self._query.search` (UNSET-safe after matches_inbox_name change)
- Updated list_tags and list_folders pass-throughs with warnings plumbing for mixed-ALL
- Added filter enums to `_INTERNAL_CLASSES` in test_descriptions.py
- 12 new tests covering matches_inbox_name with UNSET/None/str/int, availability expansion for all 5 list methods, mixed-ALL warnings

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Filter enum classes flagged by description enforcement test**
- **Found during:** Task 2 verification
- **Issue:** New AvailabilityFilter enum classes had inline docstrings, violating the centralized description convention
- **Fix:** Added all 3 filter enum class names to `_INTERNAL_CLASSES` in test_descriptions.py (they are internal, not agent-facing)
- **Files modified:** tests/test_descriptions.py
- **Commit:** 1a08e1c

## Verification

- `uv run pytest tests/ -x -q` -- 1693 passed
- `uv run pytest tests/test_list_contracts.py -x -q` -- 107 passed
- `uv run pytest tests/test_list_pipelines.py -x -q` -- 54 passed
- `uv run pytest tests/test_output_schema.py -x -q` -- 32 passed
- `uv run mypy src/omnifocus_operator/service/service.py --strict` -- Success
- Coverage: 98.18%

## Self-Check: PASSED

All files exist, all commits found, all key content verified.
