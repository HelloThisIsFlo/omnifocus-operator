---
phase: 22-service-decomposition
plan: 03
subsystem: api
tags: [service-layer, validation, resolution, srp]

# Dependency graph
requires:
  - phase: 22-02
    provides: DomainLogic with StubResolver/StubRepo test pattern
provides:
  - validate.py module (pure validation, no repo dependency)
  - Resolver.resolve_task method (entity existence check)
  - Edit target and anchor move routed through Resolver boundary
affects: [22-04, 26-bridge-replacement]

# Tech tracking
tech-stack:
  added: []
  patterns: [catch-and-rethrow for domain error messages, validation/resolution SRP split]

key-files:
  created: [src/omnifocus_operator/service/validate.py]
  modified: [src/omnifocus_operator/service/resolve.py, src/omnifocus_operator/service/service.py, src/omnifocus_operator/service/domain.py, tests/test_service_resolve.py, tests/test_service_domain.py]

key-decisions:
  - "service.py import update pulled into Task 1 commit (pre-commit mypy requires consistent imports)"
  - "Container move type-check stays as direct repo access (not resolution, verified by plan)"

patterns-established:
  - "Validation in validate.py (pure, no repo), resolution in resolve.py (async, repo-dependent)"
  - "Resolver only has raising methods -- resolve_task, resolve_parent, resolve_tags all raise ValueError if not found"
  - "Domain catches Resolver ValueError and re-raises with domain-specific message for boundary isolation"

requirements-completed: [SVCR-02, SVCR-03]

# Metrics
duration: 3min
completed: 2026-03-20
---

# Phase 22 Plan 03: Validation/Resolution SRP Split Summary

**Split validation from resolution into separate module, route entity existence checks through Resolver boundary**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-20T12:58:04Z
- **Completed:** 2026-03-20T13:01:19Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created validate.py as pure validation module (no async, no repo dependency)
- Added resolve_task to Resolver (raising ValueError if task not found, returns Task object)
- Routed edit target (service.py) and anchor move (domain.py) through Resolver boundary
- Container move type-check correctly left as direct repo access (not resolution)

## Task Commits

Each task was committed atomically:

1. **Task 1: Split validate.py from resolve.py and add resolve_task to Resolver** - `de18c3e` (refactor)
2. **Task 2: Route edit target and anchor move through Resolver, update imports and tests** - `7691365` (refactor)

## Files Created/Modified
- `src/omnifocus_operator/service/validate.py` - Pure validation functions (validate_task_name, validate_task_name_if_set)
- `src/omnifocus_operator/service/resolve.py` - Removed validation exports, added resolve_task method
- `src/omnifocus_operator/service/service.py` - Updated imports, edit_task uses resolver.resolve_task
- `src/omnifocus_operator/service/domain.py` - _process_anchor_move routes through resolver with catch-and-rethrow
- `tests/test_service_resolve.py` - Updated imports, added resolve_task tests
- `tests/test_service_domain.py` - Added resolve_task to StubResolver, updated _domain helper

## Decisions Made
- service.py import update pulled into Task 1 commit because pre-commit mypy requires all imports to be consistent within a commit
- Container move type-check stays as direct repo access per plan (verified: it checks "is this a task?" for cycle detection, not "does this exist?")

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] service.py import update pulled into Task 1**
- **Found during:** Task 1 (commit attempt)
- **Issue:** Pre-commit mypy fails when resolve.py no longer exports validation functions but service.py still imports them from there
- **Fix:** Updated service.py imports in the same commit as the resolve.py/validate.py split
- **Files modified:** src/omnifocus_operator/service/service.py
- **Verification:** mypy passes in pre-commit hook
- **Committed in:** de18c3e (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary for commit atomicity. Task 2 scope reduced slightly (import change already done). No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Validation/resolution boundary clean -- validate.py is pure, resolve.py is resolution-only
- Ready for Plan 04 (final gap closure tasks)
- 581 tests pass, mypy clean

## Self-Check: PASSED

All files and commits verified.

---
*Phase: 22-service-decomposition*
*Completed: 2026-03-20*
