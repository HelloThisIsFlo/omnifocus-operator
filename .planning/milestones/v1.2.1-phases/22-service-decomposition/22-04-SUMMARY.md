---
phase: 22-service-decomposition
plan: 04
subsystem: service
tags: [domain-logic, null-semantics, refactoring, payload-builder]

# Dependency graph
requires:
  - phase: 22-03
    provides: DomainLogic extraction with tag/lifecycle/move/no-op rules
provides:
  - normalize_clear_intents method centralizing null-means-clear pattern
  - PayloadBuilder as pure construction (no semantic interpretation)
  - Fail-fast assert in _apply_replace enforcing normalization pipeline
affects: [service-pipeline, edit-task]

# Tech tracking
tech-stack:
  added: []
  patterns: [normalize-before-construct, fail-fast-assert-after-normalization]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/payload.py
    - src/omnifocus_operator/service/service.py
    - tests/test_service_domain.py
    - tests/test_service_payload.py

key-decisions:
  - "Fail-fast assert in _apply_replace instead of defensive fallback -- bypassing normalization is a bug"
  - "normalize_clear_intents returns new command via model_copy (immutable pattern)"

patterns-established:
  - "Normalize-before-construct: domain normalizes semantic intents before PayloadBuilder sees data"
  - "Fail-fast assert after normalization: downstream methods assert preconditions rather than defensively handling invalid state"

requirements-completed: [SVCR-04]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 22 Plan 04: Centralize Null-Means-Clear Summary

**DomainLogic.normalize_clear_intents centralizes note=None and tags.replace=None normalization, PayloadBuilder simplified to pure construction**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T13:03:53Z
- **Completed:** 2026-03-20T13:06:43Z
- **Tasks:** 1
- **Files modified:** 5

## Accomplishments
- Centralized null-means-clear normalization (note=None->'' and tags.replace=None->[]) in single DomainLogic method
- Removed semantic interpretation from PayloadBuilder -- now pure construction
- Replaced defensive isinstance fallback with fail-fast assert in _apply_replace
- Added 7 tests for normalize_clear_intents covering note/tag/unset cases
- Updated PayloadBuilder test to reflect new contract (receives pre-normalized data)

## Task Commits

Each task was committed atomically:

1. **Task 1: Centralize null-means-clear in DomainLogic and simplify PayloadBuilder** - `5836890` (refactor)

**Plan metadata:** (pending)

## Files Created/Modified
- `src/omnifocus_operator/service/domain.py` - Added normalize_clear_intents method, fail-fast assert in _apply_replace
- `src/omnifocus_operator/service/payload.py` - Removed note=None->'' conversion (now upstream)
- `src/omnifocus_operator/service/service.py` - Orchestrator calls normalize_clear_intents before payload building
- `tests/test_service_domain.py` - Added TestNormalizeClearIntents class (6 tests)
- `tests/test_service_payload.py` - Updated note test, added None-passthrough test

## Decisions Made
- Fail-fast assert in _apply_replace: bypassing normalization is a bug, not something to handle gracefully
- normalize_clear_intents returns new command via model_copy (immutable, no mutation)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed ActionsGroup import to EditTaskActions**
- **Found during:** Task 1 (tests)
- **Issue:** Plan referenced non-existent `ActionsGroup` class from `contracts.common`
- **Fix:** Used correct `EditTaskActions` from `contracts.use_cases.edit_task`
- **Files modified:** tests/test_service_domain.py
- **Verification:** All 588 tests pass
- **Committed in:** 5836890

---

**Total deviations:** 1 auto-fixed (1 bug in plan)
**Impact on plan:** Trivial import name correction. No scope change.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 22 (service-decomposition) is now complete -- all 4 plans executed
- Ready for UAT focusing on developer experience: package layout, naming, import patterns, boundary signatures

## Self-Check: PASSED

All files exist. Commit 5836890 verified.

---
*Phase: 22-service-decomposition*
*Completed: 2026-03-20*
