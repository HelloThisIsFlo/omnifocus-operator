---
phase: 21-write-pipeline-unification
plan: 01
subsystem: service
tags: [pydantic, model-validate, payload-construction, refactoring]

# Dependency graph
requires:
  - phase: 20-model-taxonomy
    provides: Typed repo payloads (CreateTaskRepoPayload, EditTaskRepoPayload) with snake_case fields
provides:
  - Symmetric payload construction for both write paths (kwargs dict -> model_validate)
  - Snake_case intermediate dict in edit_task (no camelCase roundtrip)
affects: [21-write-pipeline-unification plan 02, 22-service-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns: [kwargs-dict-model-validate for repo payload construction]

key-files:
  created: []
  modified: [src/omnifocus_operator/service.py]

key-decisions:
  - "add_task uses kwargs dict with only populated fields instead of passing all fields (many as None) to constructor"
  - "edit_task builds snake_case payload dict from the start, eliminating _payload_to_repo mapping"
  - "MoveToRepoPayload constructed directly from snake_case dict via **kwargs"

patterns-established:
  - "kwargs dict -> model_validate() for both add_task and edit_task repo payload construction"

requirements-completed: [PIPE-01, PIPE-02]

# Metrics
duration: 3min
completed: 2026-03-19
---

# Phase 21 Plan 01: Service Payload Unification Summary

**Symmetric kwargs dict -> model_validate() payload construction for both add_task and edit_task, eliminating camelCase roundtrip and _payload_to_repo mapping**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-19T18:14:50Z
- **Completed:** 2026-03-19T18:18:02Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- add_task builds CreateTaskRepoPayload via kwargs dict with only populated fields, then model_validate()
- edit_task builds payload in snake_case from the start -- no camelCase intermediate dict
- _payload_to_repo mapping dict and its loop eliminated entirely
- No-op detection, tag diff, and move_to all use snake_case keys consistently
- All 522 tests pass, mypy clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Converge add_task payload construction to kwargs dict pattern** - `8107a6b` (refactor)
2. **Task 2: Eliminate camelCase roundtrip in edit_task payload construction** - `da06be0` (refactor)

## Files Created/Modified
- `src/omnifocus_operator/service.py` - Both add_task and edit_task payload construction unified to kwargs dict -> model_validate() pattern

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Service layer now uses symmetric payload construction for both write paths
- Ready for plan 02: repo serialization convergence (exclude_none -> exclude_unset), BridgeWriteMixin extraction, and explicit protocol conformance

## Self-Check: PASSED

- FOUND: src/omnifocus_operator/service.py
- FOUND: 21-01-SUMMARY.md
- FOUND: 8107a6b (Task 1 commit)
- FOUND: da06be0 (Task 2 commit)

---
*Phase: 21-write-pipeline-unification*
*Completed: 2026-03-19*
