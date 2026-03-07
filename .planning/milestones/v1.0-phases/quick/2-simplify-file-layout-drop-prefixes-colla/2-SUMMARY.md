---
phase: quick-2
plan: 01
subsystem: infra
tags: [refactoring, file-layout, python-packaging]

requires:
  - phase: quick-2 (previous partial execution)
    provides: models/ renames and repository/mtime.py rename already done
provides:
  - Simplified file layout with no _ prefixes
  - server.py, service.py, repository.py as flat modules (not packages)
  - All bridge/ submodules renamed to drop _ prefix
  - simulator/data.py renamed from _data.py
affects: [all phases -- import paths changed internally]

tech-stack:
  added: []
  patterns:
    - "Single-file modules preferred over single-file packages"
    - "No _ prefix convention on internal modules"

key-files:
  created:
    - src/omnifocus_operator/server.py
    - src/omnifocus_operator/service.py
    - src/omnifocus_operator/repository.py
  modified:
    - src/omnifocus_operator/bridge/real.py
    - src/omnifocus_operator/bridge/factory.py
    - src/omnifocus_operator/bridge/simulator.py
    - src/omnifocus_operator/simulator/__main__.py
    - tests/test_repository.py
    - tests/test_ipc_engine.py
    - tests/test_server.py
    - tests/test_service.py
    - tests/test_simulator_bridge.py
    - tests/test_simulator_integration.py

key-decisions:
  - "Collapsed repository.py combines mtime protocol/implementations with OmniFocusRepository in one file"
  - "External import paths unchanged (from omnifocus_operator.server import create_server still works)"

patterns-established:
  - "No _ prefix on internal modules -- use plain names (errors.py not _errors.py)"
  - "Single-file packages collapsed to plain .py modules"

requirements-completed: []

duration: 5min
completed: 2026-03-07
---

# Quick Task 2: Simplify File Layout Summary

**Drop _ prefixes from all internal modules, collapse server/service/repository packages into flat modules, update all src and test imports**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-07T00:25:57Z
- **Completed:** 2026-03-07T00:30:32Z
- **Tasks:** 3 (includes previous executor's partial work on models/ and repository/mtime)
- **Files modified:** 27

## Accomplishments

- Renamed 7 bridge/simulator files to drop _ prefix (6 bridge + 1 simulator)
- Fixed all internal cross-references within bridge/, server/, service/, repository/
- Collapsed server/, service/, repository/ from packages to flat modules
- Updated all test file imports (6 test files)
- All 182 tests pass, ruff clean, mypy clean

## Task Commits

1. **Rename bridge/ and simulator/ files + update all imports** - `a578aee`
2. **Collapse server/, service/, repository/ packages** - `b15b42b`

## Files Created/Modified

- `src/omnifocus_operator/server.py` - Collapsed from server/_server.py + server/__init__.py
- `src/omnifocus_operator/service.py` - Collapsed from service/_service.py + service/__init__.py
- `src/omnifocus_operator/repository.py` - Combined repository/_repository.py + repository/mtime.py
- `src/omnifocus_operator/bridge/real.py` - Updated import from bridge._errors to bridge.errors
- `src/omnifocus_operator/bridge/factory.py` - Updated imports from bridge._* to bridge.*
- `src/omnifocus_operator/bridge/simulator.py` - Updated import from bridge._real to bridge.real
- `src/omnifocus_operator/simulator/data.py` - Renamed from _data.py
- `src/omnifocus_operator/simulator/__main__.py` - Updated import
- `tests/test_repository.py` - Updated imports
- `tests/test_ipc_engine.py` - Updated imports + mock.patch targets
- `tests/test_server.py` - Updated imports (server._server -> server)
- `tests/test_service.py` - Updated imports
- `tests/test_simulator_bridge.py` - Updated imports
- `tests/test_simulator_integration.py` - Updated imports

## Decisions Made

- Collapsed repository.py combines MtimeSource protocol/implementations and OmniFocusRepository in one file (natural grouping, reduces import complexity)
- External import paths unchanged -- `from omnifocus_operator.server import create_server` works the same

## Deviations from Plan

None -- plan executed as written (with the addition of test file updates, which were explicitly approved by user).

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- File layout simplified and clean
- Ready for milestone wrap-up or Phase 10

---
*Quick Task: 2*
*Completed: 2026-03-07*
