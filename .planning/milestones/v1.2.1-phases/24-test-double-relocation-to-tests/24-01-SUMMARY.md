---
phase: 24-test-double-relocation-to-tests
plan: 01
subsystem: infra
tags: [test-doubles, imports, package-structure]

# Dependency graph
requires:
  - phase: 19-inmemorybridge-export-cleanup
    provides: InMemoryBridge removed from bridge package exports
  - phase: 23-simulatorbridge-and-factory-cleanup
    provides: SimulatorBridge/factory removed from bridge package exports
provides:
  - tests/doubles/ package with all 5 test doubles relocated from src/
  - Structural import barrier: production code cannot import test doubles
  - Negative import tests proving old paths are broken
affects: [26-replace-inmemoryrepository, 27-repository-contract-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: ["tests/doubles/ as canonical test double location", "negative import tests for deleted modules"]

key-files:
  created:
    - tests/doubles/__init__.py
    - tests/doubles/bridge.py
    - tests/doubles/simulator.py
    - tests/doubles/mtime.py
    - tests/doubles/repository.py
  modified:
    - src/omnifocus_operator/bridge/mtime.py
    - tests/test_bridge.py
    - tests/test_repository.py
    - tests/test_service.py
    - tests/test_server.py
    - tests/test_hybrid_repository.py
    - tests/test_ipc_engine.py
    - tests/test_simulator_bridge.py
    - tests/test_simulator_integration.py
    - tests/test_service_resolve.py

key-decisions:
  - "ConstantMtimeSource explicitly inherits MtimeSource protocol (was structural typing)"
  - "FileMtimeSource explicitly inherits MtimeSource protocol (consistency)"
  - "All negative import tests consolidated in TestTestDoubleRelocation class in test_bridge.py"

patterns-established:
  - "Test doubles import pattern: from tests.doubles import ClassName"
  - "Negative import tests: ModuleNotFoundError for deleted modules, ImportError for removed classes"

requirements-completed: [INFRA-08, INFRA-09]

# Metrics
duration: 5min
completed: 2026-03-20
---

# Phase 24 Plan 01: Test Double Relocation Summary

**Relocated all 5 test doubles (InMemoryBridge, BridgeCall, SimulatorBridge, ConstantMtimeSource, InMemoryRepository) from src/ to tests/doubles/, creating structural import barrier between production and test code**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-20T19:40:22Z
- **Completed:** 2026-03-20T19:45:51Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Created tests/doubles/ package with 4 modules and convenience re-exports in __init__.py
- Deleted 3 source files (bridge/in_memory.py, bridge/simulator.py, repository/in_memory.py)
- Cleaned mtime.py: removed ConstantMtimeSource, made FileMtimeSource explicitly implement MtimeSource
- Migrated imports in 9 test files from old production paths to tests.doubles
- Added 5 negative import tests proving old paths raise ModuleNotFoundError/ImportError
- All 597 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1: Create tests/doubles/ package with relocated test doubles, delete source files** - `f3e4dd7` (feat)
2. **Task 2: Migrate test imports and add negative import tests** - `4814170` (feat)

## Files Created/Modified
- `tests/doubles/__init__.py` - Package init with re-exports of all 5 test doubles
- `tests/doubles/bridge.py` - InMemoryBridge and BridgeCall test doubles
- `tests/doubles/simulator.py` - SimulatorBridge test double
- `tests/doubles/mtime.py` - ConstantMtimeSource test double (now explicitly inherits MtimeSource)
- `tests/doubles/repository.py` - InMemoryRepository test double
- `src/omnifocus_operator/bridge/mtime.py` - Removed ConstantMtimeSource, FileMtimeSource now inherits MtimeSource
- `tests/test_bridge.py` - Import migration + TestTestDoubleRelocation with 5 negative tests
- `tests/test_repository.py` - Import migration
- `tests/test_service.py` - Import migration
- `tests/test_server.py` - Import migration (8 local imports)
- `tests/test_hybrid_repository.py` - Import migration
- `tests/test_ipc_engine.py` - Import migration
- `tests/test_simulator_bridge.py` - Import migration (7 local imports)
- `tests/test_simulator_integration.py` - Import migration
- `tests/test_service_resolve.py` - Import migration

## Decisions Made
- ConstantMtimeSource and FileMtimeSource both explicitly inherit from MtimeSource protocol (was structural typing before, now explicit per D-07)
- Negative import tests consolidated in single TestTestDoubleRelocation class in test_bridge.py rather than scattered across files
- Used ModuleNotFoundError for 4 tests (entire module deleted) and ImportError for 1 test (class removed from existing module) for precision

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- INFRA-08 (no test doubles in src/) and INFRA-09 (no src/ imports from tests/) both satisfied
- tests/doubles/ established as canonical location for all test doubles
- Ready for Phase 25 (Patch/PatchOrClear type aliases) or Phase 26 (InMemoryRepository replacement)

## Self-Check: PASSED

- All 5 test double files exist in tests/doubles/
- All 3 source files confirmed deleted
- Commits f3e4dd7 and 4814170 verified in git log

---
*Phase: 24-test-double-relocation-to-tests*
*Completed: 2026-03-20*
