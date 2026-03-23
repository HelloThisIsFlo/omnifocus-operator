---
phase: 27-repository-contract-tests-for-behavioral-equivalence
plan: 01
subsystem: testing
tags: [golden-master, bridge, contract-tests, normalization, inmemorybridge]

# Dependency graph
requires:
  - phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
    provides: "Stateful InMemoryBridge with add_task/edit_task handlers"
provides:
  - "InMemoryBridge parent resolution in add_task (project > task > fallback)"
  - "InMemoryBridge tagIds resolution in add_task"
  - "InMemoryBridge tag name resolution in edit_task (from _tags list)"
  - "_resolve_parent and _resolve_tag_name shared helpers"
  - "tests/golden/ package with normalization/filtering helpers"
affects: [27-02-PLAN, capture_golden_master, test_bridge_contract]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Golden master normalization: strip dynamic fields per entity type for deterministic comparison"
    - "Shared _resolve_parent/_resolve_tag_name helpers eliminate duplication in InMemoryBridge"

key-files:
  created:
    - tests/golden/__init__.py
    - tests/golden/normalize.py
    - tests/golden/README.md
  modified:
    - tests/doubles/bridge.py
    - tests/test_stateful_bridge.py

key-decisions:
  - "Extracted _resolve_parent as shared helper reused by both add_task and edit_task moveTo"
  - "completionDate included in DYNAMIC_PROJECT_FIELDS (computed when project state changes)"
  - "repetitionRule included in DYNAMIC_TASK_FIELDS and DYNAMIC_PROJECT_FIELDS per D-18"

patterns-established:
  - "normalize_for_comparison pattern: entity_type string selects field set to strip"
  - "filter_to_known_ids pattern: three ID sets filter get_all to test-created entities"

requirements-completed: [INFRA-13, INFRA-14]

# Metrics
duration: 4min
completed: 2026-03-21
---

# Phase 27 Plan 01: InMemoryBridge Gaps + Golden Master Normalization Summary

**Fixed InMemoryBridge parent/tag resolution gaps and created tests/golden/ normalization package for contract test comparison**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-21T17:12:57Z
- **Completed:** 2026-03-21T17:16:56Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- InMemoryBridge now resolves parent param to {type, id, name} dict in add_task (was always None)
- InMemoryBridge now resolves tagIds to [{id, name}] in add_task (was always empty)
- InMemoryBridge edit_task now resolves tag names from _tags list (was using ID as name)
- Shared _resolve_parent and _resolve_tag_name helpers eliminate code duplication
- tests/golden/ package provides normalize_for_comparison, normalize_response, normalize_state, filter_to_known_ids

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix InMemoryBridge parent/tag resolution (TDD)**
   - `eac4cff` (test) -- RED: failing tests for parent/tag resolution gaps
   - `6fbc88e` (feat) -- GREEN: implementation passing all tests
2. **Task 2: Create tests/golden/ package** - `5b79b9a` (feat)

## Files Created/Modified
- `tests/doubles/bridge.py` -- Added _resolve_tag_name, _resolve_parent helpers; fixed add_task parent/tag resolution; refactored edit_task moveTo
- `tests/test_stateful_bridge.py` -- 8 new tests: parent resolution (project, task, unknown), tagIds resolution (known, unknown), edit_task tag name resolution
- `tests/golden/__init__.py` -- Package init re-exporting normalization helpers
- `tests/golden/normalize.py` -- DYNAMIC_*_FIELDS constants, normalize_for_comparison, normalize_response, normalize_state, filter_to_known_ids
- `tests/golden/README.md` -- Documents regeneration workflow and GOLD-01 requirement

## Decisions Made
- Extracted _resolve_parent as shared helper rather than duplicating logic -- used by both add_task and edit_task moveTo handlers
- completionDate included in DYNAMIC_PROJECT_FIELDS since it's computed by OmniFocus when project state changes
- repetitionRule included in both DYNAMIC_TASK_FIELDS and DYNAMIC_PROJECT_FIELDS per D-18 (next milestone)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- InMemoryBridge behavioral gaps fixed -- ready for golden master comparison
- tests/golden/ normalization helpers ready for import by capture script (Plan 02) and contract tests (Plan 02)
- Full test suite green (648 passed, 98% coverage)

## Self-Check: PASSED

- All 3 created files verified on disk
- All 3 commit hashes found in git log

---
*Phase: 27-repository-contract-tests-for-behavioral-equivalence*
*Completed: 2026-03-21*
