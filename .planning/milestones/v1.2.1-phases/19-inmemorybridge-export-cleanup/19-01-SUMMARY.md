---
phase: 19-inmemorybridge-export-cleanup
plan: 01
subsystem: infra
tags: [python-imports, package-exports, factory-pattern, test-doubles]

# Dependency graph
requires: []
provides:
  - Clean production exports without test doubles in bridge and repository packages
  - Direct module imports for InMemoryBridge, BridgeCall, ConstantMtimeSource, InMemoryRepository in tests
  - No "inmemory" factory option in bridge or repository factories
affects: [23-simulatorbridge-factory-cleanup]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Test doubles imported via direct module paths, not package re-exports"
    - "SimulatorBridge as factory-based test bridge (replaces InMemoryBridge factory path)"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/bridge/__init__.py
    - src/omnifocus_operator/bridge/factory.py
    - src/omnifocus_operator/repository/__init__.py
    - src/omnifocus_operator/repository/factory.py
    - src/omnifocus_operator/service.py
    - tests/test_bridge.py
    - tests/test_service.py
    - tests/test_repository.py
    - tests/test_server.py
    - tests/test_repository_factory.py

key-decisions:
  - "Tool-calling server tests use monkeypatched InMemoryRepository instead of factory path"
  - "Non-tool-calling server tests use simulator swap with IPC dir"
  - "Removed unused InMemoryBridge import from test_service.py after deleting factory test"

patterns-established:
  - "Test doubles from direct module paths: from omnifocus_operator.bridge.in_memory import InMemoryBridge"
  - "Server integration tests needing data: monkeypatch create_repository to return InMemoryRepository"

requirements-completed: [INFRA-01, INFRA-02, INFRA-03]

# Metrics
duration: 7min
completed: 2026-03-17
---

# Phase 19 Plan 01: InMemoryBridge Export Cleanup Summary

**Removed all test doubles from production package exports and factory, migrated 10 test files to direct module imports, all 517 tests green**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-17T12:23:49Z
- **Completed:** 2026-03-17T12:31:00Z
- **Tasks:** 3
- **Files modified:** 10

## Accomplishments
- Removed InMemoryBridge, BridgeCall, ConstantMtimeSource from bridge package exports and InMemoryRepository from repository package exports
- Deleted 94-line "inmemory" factory case with inline sample data from bridge/factory.py
- Migrated all test imports to direct module paths (4 test files with top-level imports, 4 local imports in test_server.py)
- Refactored 9 server tests and 6 repository factory tests away from OMNIFOCUS_BRIDGE=inmemory
- All 517 tests pass, 94% coverage maintained

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove test doubles from production exports and factory** - `c39126c` (refactor)
2. **Task 2: Migrate test imports to direct module paths** - `ca2772a` (refactor)
3. **Task 3: Migrate factory-dependent tests and delete inmemory factory test** - `a37b74e` (refactor)

## Files Created/Modified
- `src/omnifocus_operator/bridge/__init__.py` - Removed InMemoryBridge, BridgeCall, ConstantMtimeSource from imports and __all__
- `src/omnifocus_operator/bridge/factory.py` - Deleted "inmemory" case, removed InMemoryBridge import, updated error messages
- `src/omnifocus_operator/repository/__init__.py` - Removed InMemoryRepository from imports, __all__, and docstring
- `src/omnifocus_operator/repository/factory.py` - Changed bridge_type condition from `in ("inmemory", "simulator")` to `== "simulator"`
- `src/omnifocus_operator/service.py` - Updated docstring to reference HybridRepository
- `tests/test_bridge.py` - Split import: BridgeCall, InMemoryBridge from bridge.in_memory
- `tests/test_service.py` - InMemoryBridge/InMemoryRepository from direct module paths, deleted inmemory factory test
- `tests/test_repository.py` - InMemoryRepository from repository.in_memory
- `tests/test_server.py` - All 4 local InMemoryRepository imports updated, 9 factory tests migrated
- `tests/test_repository_factory.py` - All 6 tests use simulator swap with IPC dir

## Decisions Made
- Tool-calling server tests (3 tests) use monkeypatched `omnifocus_operator.repository.create_repository` returning InMemoryRepository directly, since SimulatorBridge would timeout without a running simulator
- Non-tool-calling server tests (5 tests) use simulator swap + OMNIFOCUS_IPC_DIR=tmp_path, since they only call list_tools or check lifespan wiring
- Removed unused InMemoryBridge import from test_service.py after deleting the only test that used it (test_inmemory_returns_inmemory_bridge)
- Removed dead OMNIFOCUS_BRIDGE/OMNIFOCUS_REPOSITORY env vars from test_get_all_structured_content_is_camelcase which builds its own bridge directly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed monkeypatch target for create_repository**
- **Found during:** Task 3 (factory-dependent test migration)
- **Issue:** Plan suggested patching `omnifocus_operator.server.create_repository` but server.py imports it at runtime from `omnifocus_operator.repository`. Initial attempt used `omnifocus_operator.repository.factory.create_repository` which also didn't work because the import resolves through `__init__.py`.
- **Fix:** Used `omnifocus_operator.repository.create_repository` as the monkeypatch target
- **Files modified:** tests/test_server.py
- **Verification:** Test passes after fix
- **Committed in:** a37b74e (Task 3 commit)

**2. [Rule 1 - Bug] Removed unused InMemoryBridge import from test_service.py**
- **Found during:** Task 3 (after deleting test_inmemory_returns_inmemory_bridge)
- **Issue:** The import `from omnifocus_operator.bridge.in_memory import InMemoryBridge` became unused after deleting the only test that used it. ruff would flag this.
- **Fix:** Removed the unused import line
- **Files modified:** tests/test_service.py
- **Verification:** ruff check passes in pre-commit hook
- **Committed in:** a37b74e (Task 3 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
- Test count is 517 (not 534+ as stated in plan). Pre-existing discrepancy -- the plan referenced an outdated test count. All tests pass.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Production exports are clean: only production code importable from package paths
- Test doubles remain available via direct module imports
- SimulatorBridge export cleanup deferred to Phase 23 as planned
- Ready for Phase 20 (next phase in roadmap)

---
## Self-Check: PASSED

All 10 modified files verified present. All 3 task commits verified in git log.

---
*Phase: 19-inmemorybridge-export-cleanup*
*Completed: 2026-03-17*
