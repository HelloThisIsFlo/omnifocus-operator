---
phase: 09-error-serving-degraded-mode
plan: 01
subsystem: server
tags: [mcp, error-handling, degraded-mode, lifespan]

# Dependency graph
requires:
  - phase: 05-service-layer-and-mcp-server
    provides: OperatorService, app_lifespan, create_server
provides:
  - ErrorOperatorService class for degraded-mode error serving
  - try/except in app_lifespan yielding error service on startup failure
  - Simplified __main__.py without pre-async validation
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: [error-serving degraded mode, __getattr__ trap for service substitution]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/service/_service.py
    - src/omnifocus_operator/service/__init__.py
    - src/omnifocus_operator/server/_server.py
    - src/omnifocus_operator/__main__.py
    - tests/test_service.py
    - tests/test_server.py

key-decisions:
  - "ErrorOperatorService uses __getattr__ + object.__setattr__ to avoid __init__ loop"
  - "Lazy import of ErrorOperatorService inside except block to keep normal path clean"
  - "Moved pytest import to TYPE_CHECKING in test_server.py (no longer used at runtime after removing pytest.raises)"

patterns-established:
  - "Degraded mode pattern: catch Exception in lifespan, yield error-serving substitute service"

requirements-completed: [ERR-01, ERR-02, ERR-03, ERR-04, ERR-05, ERR-06, ERR-07]

# Metrics
duration: 3min
completed: 2026-03-06
---

# Phase 9 Plan 1: Error-Serving Degraded Mode Summary

**ErrorOperatorService with __getattr__ trap catches fatal startup errors and serves them as isError tool responses instead of crashing the MCP server**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-06T19:50:42Z
- **Completed:** 2026-03-06T19:54:32Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 6

## Accomplishments
- ErrorOperatorService class that intercepts all attribute access and raises RuntimeError with actionable error message
- app_lifespan wrapped in try/except, yielding ErrorOperatorService on startup failure with full traceback logged at ERROR level
- Simplified __main__.py: removed pre-async validation block, just logging setup + create_server + run
- 8 new tests (5 unit + 3 integration), updated 1 existing test from ExceptionGroup to degraded mode verification
- 182 total tests passing, 98.26% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `542305e` (test)
2. **Task 1 GREEN: Implementation** - `2b7970f` (feat)

_TDD task: RED (failing tests) then GREEN (implementation passing)_

## Files Created/Modified
- `src/omnifocus_operator/service/_service.py` - Added ErrorOperatorService class with __getattr__ trap
- `src/omnifocus_operator/service/__init__.py` - Added ErrorOperatorService to exports
- `src/omnifocus_operator/server/_server.py` - Wrapped app_lifespan body in try/except, yields ErrorOperatorService on failure
- `src/omnifocus_operator/__main__.py` - Removed pre-async validation block (bridge_type == "real" check)
- `tests/test_service.py` - Added TestErrorOperatorService (5 tests)
- `tests/test_server.py` - Added TestDegradedMode (3 tests), updated test_default_real_bridge_fails_at_startup

## Decisions Made
- ErrorOperatorService uses `object.__setattr__` to store `_error_message` without triggering `__getattr__`, and does NOT call `super().__init__()` to avoid creating a `_repository` attribute
- Import of ErrorOperatorService is lazy (inside except block) to keep the normal startup path clean
- Moved `import pytest` to TYPE_CHECKING in test_server.py since removing `pytest.raises(ExceptionGroup)` left no runtime usage

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test_does_not_call_super_init assertion**
- **Found during:** Task 1 GREEN phase
- **Issue:** `hasattr(service, "_repository")` triggers `__getattr__` which raises RuntimeError (not AttributeError), so hasattr propagates the exception instead of returning False
- **Fix:** Changed to `"_repository" not in service.__dict__` which checks instance dict directly without triggering `__getattr__`
- **Files modified:** tests/test_service.py
- **Verification:** Test passes
- **Committed in:** 2b7970f (GREEN commit)

**2. [Rule 3 - Blocking] Fixed ruff TC002 lint error for pytest import**
- **Found during:** Task 1 RED phase (pre-commit hook)
- **Issue:** Removing `pytest.raises(ExceptionGroup)` from test_server.py left `import pytest` with no runtime usage, triggering ruff TC002
- **Fix:** Moved `import pytest` into `TYPE_CHECKING` block
- **Files modified:** tests/test_server.py
- **Verification:** ruff check passes
- **Committed in:** 542305e (RED commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 blocking)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Error-serving degraded mode complete
- Server no longer crashes on startup failures -- agents get actionable error messages
- Ready for next phase or milestone wrap-up

---
*Phase: 09-error-serving-degraded-mode*
*Completed: 2026-03-06*
