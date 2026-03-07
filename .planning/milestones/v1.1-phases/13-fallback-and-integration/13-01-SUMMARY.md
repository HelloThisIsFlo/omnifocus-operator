---
phase: 13-fallback-and-integration
plan: 01
subsystem: repository
tags: [factory-pattern, env-var-routing, error-serving, sqlite, bridge]

requires:
  - phase: 12-sqlite-reader
    provides: HybridRepository for SQLite-based reads
  - phase: 11-datasource-protocol
    provides: Repository protocol, BridgeRepository
provides:
  - Repository factory (create_repository) routing reads based on OMNIFOCUS_REPOSITORY env var
  - Server lifespan restructured to use factory instead of inline bridge setup
  - SQLite-not-found error-serving with actionable fix/workaround message
affects: [13-fallback-and-integration]

tech-stack:
  added: []
  patterns: [factory-pattern for repository selection, always-sweep IPC]

key-files:
  created:
    - src/omnifocus_operator/repository/factory.py
    - tests/test_repository_factory.py
  modified:
    - src/omnifocus_operator/repository/__init__.py
    - src/omnifocus_operator/server.py
    - tests/test_server.py
    - tests/test_simulator_bridge.py
    - tests/test_simulator_integration.py

key-decisions:
  - "Factory duplicates _DEFAULT_DB_PATH constant (avoids coupling to hybrid.py private)"
  - "IPC sweep always runs before factory call (handles missing dirs gracefully)"
  - "Bridge mode warning mentions both blocked-unavailability and speed tradeoffs"

patterns-established:
  - "Repository factory pattern: create_repository(type) mirrors create_bridge(type)"
  - "Error messages distinguish fix vs workaround (OMNIFOCUS_SQLITE_PATH vs OMNIFOCUS_REPOSITORY=bridge)"

requirements-completed: [FALL-01, FALL-03]

duration: 7min
completed: 2026-03-07
---

# Phase 13 Plan 01: Repository Factory Summary

**Repository factory routing reads via OMNIFOCUS_REPOSITORY env var with SQLite-not-found error-serving**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-07T19:08:26Z
- **Completed:** 2026-03-07T19:16:00Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Repository factory (`create_repository`) routes to HybridRepository (sqlite/hybrid) or BridgeRepository (bridge) based on env var
- SQLite-not-found raises FileNotFoundError with actionable fix (OMNIFOCUS_SQLITE_PATH) and workaround (OMNIFOCUS_REPOSITORY=bridge)
- Server lifespan simplified: IPC sweep always runs, then factory handles all repository setup
- All 297 tests pass at 98% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Create repository factory with tests** - `369d28e` (feat, TDD)
2. **Task 2: Restructure server lifespan to use factory** - `5b5d9bb` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/factory.py` - Repository factory with sqlite/bridge routing and path validation
- `src/omnifocus_operator/repository/__init__.py` - Added create_repository export
- `src/omnifocus_operator/server.py` - Lifespan uses create_repository(), always sweeps IPC
- `tests/test_repository_factory.py` - 13 factory unit tests
- `tests/test_server.py` - Updated for factory-driven architecture, added SQLite-not-found test
- `tests/test_simulator_bridge.py` - Updated lifespan tests for OMNIFOCUS_REPOSITORY env var
- `tests/test_simulator_integration.py` - Added OMNIFOCUS_REPOSITORY=bridge for simulator tests

## Decisions Made
- Duplicated `_DEFAULT_DB_PATH` in factory.py rather than importing private constant from hybrid.py
- IPC sweep runs unconditionally before the try/except block (sweep handles missing dirs gracefully)
- Bridge mode warning mentions both missing 'blocked' availability and speed tradeoffs (~500ms vs ~50ms)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated existing tests for new default repository mode**
- **Found during:** Task 2 (Server lifespan restructure)
- **Issue:** Existing tests using OMNIFOCUS_BRIDGE=inmemory without OMNIFOCUS_REPOSITORY=bridge were hitting the real SQLite database (new default is sqlite, not bridge)
- **Fix:** Added OMNIFOCUS_REPOSITORY=bridge to all tests that use the real lifespan with bridge mode; updated sweep mock patch paths from omnifocus_operator.bridge to omnifocus_operator.bridge.real; updated degraded mode tests to patch create_repository instead of create_bridge
- **Files modified:** tests/test_server.py, tests/test_simulator_bridge.py, tests/test_simulator_integration.py
- **Verification:** All 297 tests pass
- **Committed in:** 5b5d9bb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary update -- changing the default from bridge to sqlite required updating all tests that assumed bridge was the default. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Repository factory ready for integration with remaining phase 13 plans
- OMNIFOCUS_REPOSITORY env var documented in error messages for discoverability

---
*Phase: 13-fallback-and-integration*
*Completed: 2026-03-07*

## Self-Check: PASSED
