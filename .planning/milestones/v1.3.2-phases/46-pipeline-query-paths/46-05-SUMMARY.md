---
phase: 46-pipeline-query-paths
plan: 05
subsystem: service
tags: [dataclass, date-filter, resolver, warnings, refactoring]

# Dependency graph
requires:
  - phase: 45-date-models-resolution
    provides: resolve_date_filter pure function, DueSoonSetting enum
provides:
  - ResolvedDateBounds dataclass as rich return type from resolve_date_filter
  - Due-soon None fallback with agent-facing warning
  - Clean top-level imports in _resolve_date_filters (no noqa)
affects: [46-pipeline-query-paths]

# Tech tracking
tech-stack:
  added: []
  patterns: [ResolvedDateBounds rich return type from resolver, warning propagation via dataclass]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/service/resolve_dates.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - tests/test_resolve_dates.py
    - tests/test_list_pipelines.py
    - tests/test_warnings.py

key-decisions:
  - "ResolvedDateBounds is a frozen dataclass with after/before/warnings fields"
  - "Due-soon None fallback uses TODAY bounds (conservative, narrowest window)"
  - "DueSoonSetting placed under TYPE_CHECKING since only used in lazy annotation"
  - "resolve_dates.py added to warning enforcement consumer list"

patterns-established:
  - "ResolvedDateBounds: resolver returns rich type with warnings instead of bare tuple"

requirements-completed: [RESOLVE-12, EXEC-01, EXEC-02]

# Metrics
duration: 10min
completed: 2026-04-08
---

# Phase 46 Plan 05: Date Resolver Rich Type + Due-Soon Fallback Summary

**ResolvedDateBounds dataclass replaces bare tuple return, due-soon None case falls back to TODAY with agent warning, inline imports cleaned up**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-08T13:29:41Z
- **Completed:** 2026-04-08T13:39:39Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- resolve_date_filter returns ResolvedDateBounds (frozen dataclass with after, before, warnings)
- due="soon" with no threshold defaults to TODAY bounds + emits DUE_SOON_THRESHOLD_NOT_DETECTED warning
- All 4 inline noqa: PLC0415 imports removed from _resolve_date_filters, moved to proper top-level locations
- 1857 tests passing, 97.81% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: ResolvedDateBounds rich return type + due-soon fallback** - `14a32ce` (test: RED), `312a754` (feat: GREEN)
2. **Task 2: Move inline imports to top-level** - `a32ae71` (refactor)

_Note: Task 1 used TDD (test -> feat commits)_

## Files Created/Modified
- `src/omnifocus_operator/service/resolve_dates.py` - ResolvedDateBounds dataclass, updated return types, due-soon fallback logic
- `src/omnifocus_operator/agent_messages/warnings.py` - DUE_SOON_THRESHOLD_NOT_DETECTED constant
- `src/omnifocus_operator/service/service.py` - Consumes ResolvedDateBounds, top-level imports, warning propagation
- `tests/test_resolve_dates.py` - All tests updated to use ResolvedDateBounds attributes, new fallback + rich type tests
- `tests/test_list_pipelines.py` - Pipeline test for due-soon fallback warning propagation
- `tests/test_warnings.py` - Added resolve_dates to warning enforcement consumer list

## Decisions Made
- ResolvedDateBounds is a frozen dataclass (immutable) with `field(default_factory=list)` for warnings
- DueSoonSetting import placed under TYPE_CHECKING since `from __future__ import annotations` makes the local variable annotation lazy -- only runtime uses need runtime imports
- resolve_dates.py added to _WARNING_CONSUMERS in test_warnings.py since it now imports warning constants directly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated warning enforcement test consumer list**
- **Found during:** Task 2 (full test suite verification)
- **Issue:** test_warnings.py checks that all warning constants are referenced in consumer modules, but resolve_dates.py was not in the consumer list
- **Fix:** Added resolve_dates to _WARNING_CONSUMERS in test_warnings.py
- **Files modified:** tests/test_warnings.py
- **Verification:** Full test suite green (1857 tests)
- **Committed in:** a32ae71 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary for enforcement test to pass. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ResolvedDateBounds is the canonical return type for resolve_date_filter
- Warning propagation wired: resolver warnings flow through pipeline to agent response
- All inline imports removed, service.py has clean top-level import structure

## Self-Check: PASSED

All 6 modified files exist. All 3 task commits verified (14a32ce, 312a754, a32ae71).

---
*Phase: 46-pipeline-query-paths*
*Completed: 2026-04-08*
