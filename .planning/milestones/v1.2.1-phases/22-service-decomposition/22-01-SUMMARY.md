---
phase: 22-service-decomposition
plan: 01
subsystem: api
tags: [service-layer, decomposition, refactoring, dependency-injection]

# Dependency graph
requires:
  - phase: 21-write-pipeline-unification
    provides: "Unified kwargs dict -> model_validate pattern, exclude_unset standardization"
  - phase: 20-model-taxonomy
    provides: "Typed payloads, contracts/ package, Service protocol"
provides:
  - "service/ package with 4 modules: service.py, resolve.py, domain.py, payload.py"
  - "Thin orchestrator OperatorService with explicit Service protocol conformance"
  - "Independently testable Resolver, DomainLogic, PayloadBuilder classes"
  - "Preserved import paths: from omnifocus_operator.service import OperatorService"
affects: [22-service-decomposition-plan-02, phase-23-simulator-bridge]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "DI-based service decomposition: Resolver(repo), DomainLogic(repo, resolver), PayloadBuilder()"
    - "model_fields_set for detecting explicitly-set fields vs defaults in no-op detection"

key-files:
  created:
    - src/omnifocus_operator/service/__init__.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/service/resolve.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/payload.py
  modified:
    - tests/test_warnings.py

key-decisions:
  - "Used model_fields_set instead of is-not-None checks for no-op detection -- correctly handles null-means-clear semantics for dates/note"
  - "Temporary copy of monolith in service/service.py for Task 1 to keep intermediate commits mypy-clean"
  - "Updated test_warnings.py to scan service submodules (domain.py, service.py) for warning constant references"

patterns-established:
  - "Service package pattern: __init__.py re-exports, implementations in own files (mirrors repository/)"
  - "DomainLogic._all_fields_match uses model_fields_set for set-vs-default detection"
  - "_Unset checks stay in orchestrator; domain methods receive clean Python values"

requirements-completed: [SVCR-01, SVCR-02, SVCR-03, SVCR-04]

# Metrics
duration: 12min
completed: 2026-03-19
---

# Phase 22 Plan 01: Service Decomposition Summary

**Converted 669-line monolithic service.py into 4-module service/ package with DI-based Resolver, DomainLogic, PayloadBuilder and thin orchestrator**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-19T23:01:53Z
- **Completed:** 2026-03-19T23:14:08Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Decomposed monolithic service.py (669 lines) into service/ package with 4 modules
- OperatorService now reads as thin orchestration: validate -> resolve -> domain -> build -> delegate
- Resolver, DomainLogic, PayloadBuilder each independently importable and testable
- All 522 existing tests pass unchanged, mypy clean, 96.89% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Create service/ package with resolve.py, domain.py, payload.py modules** - `58e96c7` (feat)
2. **Task 2: Rewrite service.py as thin orchestrator, delete old file** - `ec5cbd8` (feat)

## Files Created/Modified
- `src/omnifocus_operator/service/__init__.py` - Package re-exports: OperatorService, ErrorOperatorService
- `src/omnifocus_operator/service/service.py` - Thin orchestrator (251 lines, down from 669)
- `src/omnifocus_operator/service/resolve.py` - Resolver class + validate_task_name standalone
- `src/omnifocus_operator/service/domain.py` - DomainLogic class with lifecycle, tags, cycle, no-op, move
- `src/omnifocus_operator/service/payload.py` - PayloadBuilder class for typed repo payloads
- `tests/test_warnings.py` - Updated to scan service submodules for warning constant references
- `src/omnifocus_operator/service.py` - Deleted (replaced by service/ package)

## Decisions Made
- Used `model_fields_set` instead of `is not None` checks for no-op/empty-edit detection -- the old approach couldn't distinguish "field not provided" from "field explicitly set to None (clear)" for dates and note
- Created temporary copy of monolith in service/service.py during Task 1 to keep intermediate commit mypy-clean (the dynamic import bridge caused Any propagation to server.py)
- Updated test_warnings.py to check `service.domain` and `service.service` modules instead of the old monolithic `service` module

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed no-op detection using model_fields_set**
- **Found during:** Task 2 (test_clear_due_date failure)
- **Issue:** `_is_empty_edit` and `_all_fields_match` used `is not None` checks, but `None` is a valid explicit value for clearable fields (dates, note). Setting `due_date=None` was incorrectly detected as no-op.
- **Fix:** Changed both methods to use `payload.model_fields_set` to detect which fields were explicitly provided during `model_validate(kwargs)`.
- **Files modified:** `src/omnifocus_operator/service/domain.py`
- **Verification:** test_clear_due_date passes, all 522 tests pass
- **Committed in:** ec5cbd8 (Task 2 commit)

**2. [Rule 3 - Blocking] Updated test_warnings.py consumers list**
- **Found during:** Task 2 (test_all_warning_constants_referenced_in_consumers failure)
- **Issue:** Warning consolidation test only scanned the old monolithic `service` module. After decomposition, warning constants live in `service/domain.py`.
- **Fix:** Updated `_WARNING_CONSUMERS` to include `service_orchestrator` and `service_domain` modules.
- **Files modified:** `tests/test_warnings.py`
- **Verification:** All 3 test_warnings.py tests pass
- **Committed in:** ec5cbd8 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes essential for correctness. No scope creep.

## Issues Encountered
- Intermediate commit state (Task 1) required a temporary monolith copy in service/service.py because the `__init__.py` re-export required service.py to exist, but creating the thin orchestrator was Task 2's responsibility. Solved by copying the old code temporarily; Task 2 replaced it entirely.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- service/ package structure ready for Plan 02 (new unit tests for extracted modules)
- Resolver, DomainLogic, PayloadBuilder are independently testable with stub/fake dependencies
- DomainLogic tests should use stub Resolver (not InMemoryRepository) per Phase 26 preparation

## Self-Check: PASSED

- All 5 created files exist under service/
- Old service.py confirmed deleted
- Both task commits (58e96c7, ec5cbd8) found in git log

---
*Phase: 22-service-decomposition*
*Completed: 2026-03-19*
