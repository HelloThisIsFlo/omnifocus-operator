---
phase: 06-file-ipc-engine
plan: 02
subsystem: bridge
tags: [ipc, pid, orphan-sweep, factory, directory-config, env-var]

# Dependency graph
requires:
  - phase: 06-file-ipc-engine
    provides: RealBridge class with file-based IPC mechanics (Plan 01)
provides:
  - DEFAULT_IPC_DIR constant for OmniFocus 4 sandbox path
  - OMNIFOCUS_IPC_DIR env var override for dev/test
  - IPC directory auto-creation on RealBridge init
  - PID-based orphan sweep (sweep_orphaned_files)
  - Factory wiring: create_bridge("real") returns RealBridge
  - Package exports: RealBridge and sweep_orphaned_files
affects: [07-simulator-bridge, 08-real-bridge-trigger]

# Tech tracking
tech-stack:
  added: []
  patterns: [pid-liveness-check, orphan-file-sweep, lazy-factory-import]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/bridge/_real.py
    - src/omnifocus_operator/bridge/_factory.py
    - src/omnifocus_operator/bridge/__init__.py
    - tests/test_real_bridge.py
    - tests/test_service.py
    - tests/test_smoke.py

key-decisions:
  - "sweep_orphaned_files is standalone async function, not a RealBridge method -- called explicitly during server lifespan"
  - "Factory imports RealBridge lazily (inside match case) to avoid importing when only InMemoryBridge needed"
  - "_is_pid_alive uses os.kill(pid, 0) with errno.ESRCH/EPERM for cross-user PID detection"
  - "IPC directory auto-created synchronously in __init__ (one-time startup cost, not hot path)"

patterns-established:
  - "PID liveness check: os.kill(pid, 0) with errno handling for dead/alive/permission-denied"
  - "Orphan sweep: regex match IPC filenames, check PID liveness, unlink dead files"
  - "Lazy factory import: import implementation inside match case to avoid eager loading"

requirements-completed: [IPC-04, IPC-06]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 6 Plan 02: IPC Directory Config and Orphan Sweep Summary

**DEFAULT_IPC_DIR constant, PID-based orphan sweep, env var override, factory wiring, and package exports for RealBridge**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T15:52:52Z
- **Completed:** 2026-03-02T15:57:46Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 6

## Accomplishments
- DEFAULT_IPC_DIR constant pointing to OmniFocus 4 sandbox IPC path (`~/Library/Group Containers/34YW5A73WQ.../ipc`)
- `sweep_orphaned_files()` async function that removes IPC files from dead PIDs while preserving alive-PID files
- `_is_pid_alive()` using `os.kill(pid, 0)` with proper `errno.ESRCH`/`EPERM` handling
- RealBridge auto-creates IPC directory on initialization via `mkdir(parents=True, exist_ok=True)`
- Factory `create_bridge("real")` now returns working RealBridge with OMNIFOCUS_IPC_DIR env var override
- RealBridge and sweep_orphaned_files exported from `omnifocus_operator.bridge` package
- 16 new tests across 4 test classes (33 total in test_real_bridge.py), all passing

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for IPC directory config, orphan sweep, factory, exports** - `c04aca7` (test)
2. **Task 1 GREEN: Implement IPC directory config, orphan sweep, factory wiring, and exports** - `ff1456c` (feat)

_TDD task with RED (failing tests) then GREEN (implementation) commits. No refactor needed._

## Files Created/Modified
- `src/omnifocus_operator/bridge/_real.py` - Added DEFAULT_IPC_DIR, _IPC_FILE_RE, _is_pid_alive(), sweep_orphaned_files(), auto-mkdir in __init__
- `src/omnifocus_operator/bridge/_factory.py` - Wired create_bridge("real") with lazy import and env var override
- `src/omnifocus_operator/bridge/__init__.py` - Added RealBridge and sweep_orphaned_files to exports and __all__
- `tests/test_real_bridge.py` - Added 16 tests: TestIPCDirectory (5), TestOrphanSweep (7), TestFactory (2), TestExports (2)
- `tests/test_service.py` - Updated TestCreateBridge: replaced NotImplementedError test with working RealBridge test
- `tests/test_smoke.py` - Updated test_default_bridge_is_real to verify RealBridge instantiation

## Decisions Made
- `sweep_orphaned_files` is a standalone async function rather than a RealBridge method -- callers invoke it explicitly during server startup (lifespan), keeping the class focused on IPC mechanics
- Factory imports RealBridge lazily inside the match case to avoid importing heavy IPC machinery when only InMemoryBridge is needed
- `_is_pid_alive` handles three cases: `errno.ESRCH` (dead), `errno.EPERM` (alive but different user), and pid <= 0 (invalid)
- IPC directory creation is synchronous in `__init__` -- acceptable one-time startup cost, not in the hot path

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated pre-existing tests expecting NotImplementedError for "real" bridge**
- **Found during:** Task 1 GREEN phase
- **Issue:** 3 tests in test_service.py and test_smoke.py expected create_bridge("real") to raise NotImplementedError, which is no longer correct after implementing RealBridge factory wiring
- **Fix:** Replaced NotImplementedError assertions with isinstance(bridge, RealBridge) checks using monkeypatched OMNIFOCUS_IPC_DIR env var
- **Files modified:** tests/test_service.py, tests/test_smoke.py
- **Verification:** All 137 tests pass, no regressions
- **Committed in:** ff1456c (GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Required to keep test suite green after implementing the "real" factory case. No scope creep.

## Issues Encountered
None -- plan executed smoothly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 6 (File IPC Engine) is now complete
- RealBridge is fully wired: discoverable via factory, configurable via env var, self-cleaning on startup
- SimulatorBridge (Phase 7) can now subclass RealBridge and override _trigger_omnifocus()
- Phase 8 will implement the actual URL scheme trigger in _trigger_omnifocus()

---
*Phase: 06-file-ipc-engine*
*Completed: 2026-03-02*
