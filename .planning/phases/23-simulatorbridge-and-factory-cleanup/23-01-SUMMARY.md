---
phase: 23-simulatorbridge-and-factory-cleanup
plan: 01
subsystem: infra
tags: [bridge, factory, safety-guard, pytest, cleanup]

# Dependency graph
requires:
  - phase: 19-inmemorybridge-export-cleanup
    provides: InMemoryBridge removed from production exports, test doubles via direct module paths
provides:
  - PYTEST safety guard on RealBridge.__init__ via _guard_automated_testing()
  - SimulatorBridge bypass via type(self) is RealBridge check
  - Simplified repository factory creating RealBridge directly
  - bridge/factory.py deleted, create_bridge removed from package
  - SimulatorBridge removed from bridge package exports
affects: [26-replace-inmemoryrepository, 27-repository-contract-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Type-identity guard: type(self) is RealBridge bypasses for subclasses"
    - "Direct bridge construction in repository factory (no factory indirection)"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/bridge/real.py
    - src/omnifocus_operator/bridge/__init__.py
    - src/omnifocus_operator/repository/factory.py
    - tests/test_service.py
    - tests/test_smoke.py
    - tests/test_simulator_bridge.py
    - tests/test_ipc_engine.py
    - tests/test_repository_factory.py
    - tests/test_simulator_integration.py
    - tests/test_server.py

key-decisions:
  - "PYTEST guard uses type(self) is RealBridge so subclasses like SimulatorBridge bypass automatically"
  - "Repository factory creates RealBridge directly -- no OMNIFOCUS_BRIDGE env var or bridge factory"
  - "_create_bridge_repository always uses FileMtimeSource (ConstantMtimeSource branch removed)"
  - "TestLifespan in test_simulator_bridge.py now uses InMemoryRepository instead of mocked SimulatorBridge"

patterns-established:
  - "Type-identity guard pattern: _guard_automated_testing on RealBridge, bypassed by subclasses"
  - "Negative export tests: verify removed exports raise ImportError and are absent from __all__"

requirements-completed: [INFRA-04, INFRA-05, INFRA-06, INFRA-07]

# Metrics
duration: 6min
completed: 2026-03-20
---

# Phase 23 Plan 01: SimulatorBridge and Factory Cleanup Summary

**PYTEST safety guard migrated to RealBridge._guard_automated_testing(), bridge factory deleted, repository factory simplified to create RealBridge directly**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-20T18:47:47Z
- **Completed:** 2026-03-20T18:54:35Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- PYTEST safety guard now lives on RealBridge itself via _guard_automated_testing() with type(self) is RealBridge bypass for subclasses
- bridge/factory.py deleted entirely, create_bridge removed from package exports
- SimulatorBridge removed from bridge package __all__ (importable only via direct module path)
- Repository factory creates RealBridge directly via _create_real_bridge() helper -- no OMNIFOCUS_BRIDGE env var
- All 592 tests pass, 97% coverage maintained

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate PYTEST guard to RealBridge and rewrite repository factory** - `58d29ad` (feat)
2. **Task 2: Delete bridge factory, clean exports, migrate all tests** - `e1dc460` (refactor)

## Files Created/Modified
- `src/omnifocus_operator/bridge/real.py` - Added _guard_automated_testing() method, called as first line of __init__
- `src/omnifocus_operator/bridge/__init__.py` - Removed SimulatorBridge and create_bridge from exports and __all__
- `src/omnifocus_operator/bridge/factory.py` - DELETED
- `src/omnifocus_operator/repository/factory.py` - Added _create_real_bridge() helper, removed bridge factory dependency
- `tests/test_service.py` - Removed create_bridge import and TestCreateBridge class
- `tests/test_smoke.py` - Rewritten to test RealBridge directly
- `tests/test_simulator_bridge.py` - Deleted TestFactory, added negative export tests, rewrote TestLifespan with InMemoryRepository
- `tests/test_ipc_engine.py` - Renamed TestSAFE01FactoryGuard to TestRealBridgeSafety, rewrote to test RealBridge directly
- `tests/test_repository_factory.py` - Removed OMNIFOCUS_BRIDGE, added delenv PYTEST_CURRENT_TEST and OMNIFOCUS_OFOCUS_PATH
- `tests/test_simulator_integration.py` - Removed OMNIFOCUS_BRIDGE, added delenv PYTEST_CURRENT_TEST and OMNIFOCUS_OFOCUS_PATH
- `tests/test_server.py` - Removed OMNIFOCUS_BRIDGE from all 5 test methods, added delenv PYTEST_CURRENT_TEST and OMNIFOCUS_OFOCUS_PATH

## Decisions Made
- PYTEST guard uses `type(self) is RealBridge` so SimulatorBridge bypasses automatically without opt-out machinery
- Repository factory creates RealBridge directly, removing all bridge factory indirection
- `_create_bridge_repository` always uses FileMtimeSource (ConstantMtimeSource branch removed since no more simulator path)
- TestLifespan tests in test_simulator_bridge.py rewritten to use InMemoryRepository (Phase 19 pattern)
- Bridge-only repository tests now create fake .ofocus bundle directory for FileMtimeSource

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed InMemoryRepository constructor call in test_simulator_bridge.py**
- **Found during:** Task 2 (TestLifespan rewrite)
- **Issue:** Plan showed InMemoryRepository(tasks=[], ...) but constructor takes snapshot=AllEntities(...)
- **Fix:** Wrapped seed data in AllEntities model before passing to InMemoryRepository
- **Files modified:** tests/test_simulator_bridge.py
- **Verification:** All 592 tests pass
- **Committed in:** e1dc460 (Task 2 commit)

**2. [Rule 1 - Bug] Added OMNIFOCUS_OFOCUS_PATH for bridge-only repository tests**
- **Found during:** Task 2 (test_repository_factory.py and test_server.py migration)
- **Issue:** After removing ConstantMtimeSource branch, bridge-only mode always needs valid .ofocus path
- **Fix:** Created fake OmniFocus.ofocus directory in tmp_path and set OMNIFOCUS_OFOCUS_PATH env var
- **Files modified:** tests/test_repository_factory.py, tests/test_server.py, tests/test_simulator_integration.py
- **Verification:** All 592 tests pass
- **Committed in:** e1dc460 (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for test correctness after factory removal. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Bridge factory fully removed, production code path simplified
- All test files use direct construction or InMemoryRepository
- Ready for Phase 26 (Replace InMemoryRepository with stateful InMemoryBridge) and Phase 27 (Repository contract tests)

---
*Phase: 23-simulatorbridge-and-factory-cleanup*
*Completed: 2026-03-20*
