---
phase: 07-simulatorbridge-and-mock-simulator
plan: 01
subsystem: bridge
tags: [simulator, ipc, testing, file-bridge]

# Dependency graph
requires:
  - phase: 06-file-ipc-engine
    provides: RealBridge with file-based IPC mechanics
provides:
  - SimulatorBridge class (RealBridge subclass with no-op trigger)
  - Factory wiring for create_bridge('simulator')
  - Server lifespan handling for simulator bridge type
  - Package export of SimulatorBridge
affects: [07-02 mock-simulator, 08-realbridge]

# Tech tracking
tech-stack:
  added: []
  patterns: [subclass-override-hook for bridge variant]

key-files:
  created:
    - src/omnifocus_operator/bridge/_simulator.py
    - tests/test_simulator_bridge.py
  modified:
    - src/omnifocus_operator/bridge/_factory.py
    - src/omnifocus_operator/bridge/__init__.py
    - src/omnifocus_operator/server/_server.py
    - tests/test_service.py

key-decisions:
  - "SimulatorBridge inherits all IPC mechanics from RealBridge, only overrides _trigger_omnifocus as no-op"
  - "Simulator bridge uses ConstantMtimeSource (same as inmemory) since simulator data is static"
  - "Factory follows same lazy-import + env var pattern as real bridge case"

patterns-established:
  - "Bridge variant via subclass hook: override _trigger_omnifocus() to customize trigger behavior"

requirements-completed: [BRDG-03]

# Metrics
duration: 5min
completed: 2026-03-02
---

# Phase 7 Plan 1: SimulatorBridge Summary

**SimulatorBridge as RealBridge subclass with no-op _trigger_omnifocus, wired through factory and server lifespan with ConstantMtimeSource**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-02T18:18:50Z
- **Completed:** 2026-03-02T18:23:32Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- Created SimulatorBridge class that inherits all IPC file mechanics from RealBridge with a no-op trigger
- Wired create_bridge("simulator") through factory with OMNIFOCUS_IPC_DIR env var support
- Server lifespan handles "simulator" bridge type with ConstantMtimeSource and orphan sweep
- SimulatorBridge exported from omnifocus_operator.bridge package
- 14 new tests covering class behavior, factory, exports, and lifespan integration

## Task Commits

Each task was committed atomically:

1. **Task 1: Create SimulatorBridge class and unit tests**
   - `68c888f` (test: add failing tests for SimulatorBridge)
   - `35bd384` (feat: implement SimulatorBridge with no-op trigger)

2. **Task 2: Wire SimulatorBridge into factory, lifespan, and package exports**
   - `603df02` (test: add failing tests for factory, lifespan, and package wiring)
   - `96e9ddb` (feat: wire SimulatorBridge into factory, lifespan, and exports)

_Note: TDD tasks have multiple commits (test -> feat)_

## Files Created/Modified
- `src/omnifocus_operator/bridge/_simulator.py` - SimulatorBridge class (RealBridge subclass with no-op trigger)
- `tests/test_simulator_bridge.py` - 14 unit tests covering all SimulatorBridge behavior
- `src/omnifocus_operator/bridge/_factory.py` - Factory now returns SimulatorBridge for "simulator" type
- `src/omnifocus_operator/bridge/__init__.py` - SimulatorBridge added to package exports
- `src/omnifocus_operator/server/_server.py` - Lifespan handles "simulator" with ConstantMtimeSource
- `tests/test_service.py` - Updated stale test (was expecting NotImplementedError for simulator)

## Decisions Made
- SimulatorBridge inherits all IPC mechanics from RealBridge -- only _trigger_omnifocus is overridden as permanent no-op
- Simulator uses ConstantMtimeSource (same as inmemory) since simulator data is static and cache invalidation is tested in Phase 4
- Factory follows same lazy-import + env var pattern established by the "real" bridge case

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated stale test expecting NotImplementedError for simulator**
- **Found during:** Task 2 (factory wiring)
- **Issue:** test_service.py::TestCreateBridge::test_simulator_raises_not_implemented expected create_bridge("simulator") to raise NotImplementedError, which is no longer correct
- **Fix:** Changed test to assert create_bridge("simulator") returns SimulatorBridge instance
- **Files modified:** tests/test_service.py
- **Verification:** Full test suite passes (156 tests)
- **Committed in:** 96e9ddb (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Necessary correction of stale test. No scope creep.

## Issues Encountered
- Lifespan integration test initially timed out because SimulatorBridge.send_command blocks without a simulator process -- resolved by mocking send_command in lifespan tests

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- SimulatorBridge is ready to pair with the mock simulator process (Plan 02)
- The mock simulator will watch the IPC directory and write response files directly
- No blockers for Plan 02

---
*Phase: 07-simulatorbridge-and-mock-simulator*
*Completed: 2026-03-02*
