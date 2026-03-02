---
phase: 06-file-ipc-engine
plan: 03
subsystem: server
tags: [ipc, lifespan, sweep, bridge, startup]

# Dependency graph
requires:
  - phase: 06-file-ipc-engine (plan 02)
    provides: sweep_orphaned_files implementation, RealBridge with IPC directory
provides:
  - sweep_orphaned_files called during server startup lifespan
  - RealBridge.ipc_dir read-only property for external access
affects: [08-real-bridge-integration]

# Tech tracking
tech-stack:
  added: []
  patterns: [hasattr guard for bridge-type-agnostic feature gating]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/bridge/_real.py
    - src/omnifocus_operator/server/_server.py
    - tests/test_real_bridge.py
    - tests/test_server.py

key-decisions:
  - "hasattr(bridge, 'ipc_dir') guard keeps lifespan bridge-type-agnostic"
  - "Patch source module (omnifocus_operator.bridge) for lazy import testing"

patterns-established:
  - "Feature gating via hasattr: bridge-type-specific behavior guarded by attribute presence"

requirements-completed: [IPC-06]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 6 Plan 3: Sweep Wiring Summary

**Wired sweep_orphaned_files into app_lifespan with hasattr guard and read-only ipc_dir property on RealBridge**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T17:06:39Z
- **Completed:** 2026-03-02T17:10:04Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments
- RealBridge now exposes `ipc_dir` as a read-only property for external callers
- `app_lifespan` calls `sweep_orphaned_files(bridge.ipc_dir)` before cache pre-warm
- `hasattr(bridge, "ipc_dir")` guard ensures InMemoryBridge skips sweep
- Full test suite passes (142 tests, 97.16% coverage)

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for ipc_dir and sweep wiring** - `f3b2d32` (test)
2. **Task 1 (GREEN): Implementation passing all tests** - `c5b2749` (feat)

_TDD task: RED commit for failing tests, GREEN commit for implementation._

## Files Created/Modified
- `src/omnifocus_operator/bridge/_real.py` - Added `ipc_dir` read-only property on RealBridge
- `src/omnifocus_operator/server/_server.py` - Import sweep_orphaned_files, call before cache pre-warm with hasattr guard
- `tests/test_real_bridge.py` - Added TestIpcDirProperty (2 tests)
- `tests/test_server.py` - Added TestIPC06OrphanSweepWiring (3 tests: no sweep for inmemory, sweep for ipc_dir bridges, ordering)

## Decisions Made
- Used `hasattr(bridge, "ipc_dir")` guard instead of checking bridge_type string -- keeps the lifespan bridge-type-agnostic and extensible
- Patched `omnifocus_operator.bridge.sweep_orphaned_files` (source module) for tests since the lazy import inside app_lifespan creates local bindings

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test seed data for InMemoryBridge**
- **Found during:** Task 1 (TDD GREEN phase)
- **Issue:** Tests creating InMemoryBridge() with default empty dict caused Pydantic ValidationError when repository tried to validate the snapshot
- **Fix:** Provided seed_data with empty lists for all 5 collection keys
- **Files modified:** tests/test_server.py
- **Verification:** All tests pass
- **Committed in:** c5b2749 (GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Minor test fixture fix. No scope creep.

## Issues Encountered
None beyond the seed data fix documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- IPC-06 requirement fully met: server startup sweeps orphaned IPC files before accepting requests
- All Phase 6 requirements complete (IPC-01 through IPC-06)
- Ready for Phase 7 (Simulator Bridge)

---
*Phase: 06-file-ipc-engine*
*Completed: 2026-03-02*
