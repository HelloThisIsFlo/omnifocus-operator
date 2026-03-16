---
phase: 15-write-pipeline-task-creation
plan: 02
subsystem: repository, service
tags: [pydantic, bridge, write-pipeline, validation, task-creation]

# Dependency graph
requires:
  - phase: 15-write-pipeline-task-creation
    plan: 01
    provides: TaskCreateSpec, TaskCreateResult write models, bridge.js handleAddTask
provides:
  - Repository.add_task protocol method with resolved_tag_ids parameter
  - HybridRepository write-through-bridge with _mark_stale invalidation
  - InMemoryRepository in-memory add_task for testing
  - BridgeRepository add_task with cache invalidation
  - Service.add_task with name validation, parent resolution, tag resolution
  - Factory wiring bridge into HybridRepository
affects: [15-03]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Repository add_task accepts resolved_tag_ids kwarg (resolution done in service)"
    - "Service validates all inputs before delegating to repository"
    - "_mark_stale replaces TEMPORARY_simulate_write for post-write freshness"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/protocol.py
    - src/omnifocus_operator/repository/hybrid.py
    - src/omnifocus_operator/repository/in_memory.py
    - src/omnifocus_operator/repository/bridge.py
    - src/omnifocus_operator/repository/factory.py
    - src/omnifocus_operator/service.py
    - tests/test_hybrid_repository.py
    - tests/test_repository.py
    - tests/test_repository_factory.py
    - tests/test_service.py

key-decisions:
  - "Repository.add_task takes resolved_tag_ids parameter -- tag name resolution stays in service layer"
  - "Factory uses create_bridge() for SAFE-01 compliance (not direct RealBridge construction)"
  - "BridgeRepository.add_task invalidates cache (sets _cached=None) instead of WAL polling"

patterns-established:
  - "Write methods: service validates, resolves references, delegates to repository"
  - "Parent resolution: try project first, then task, ValueError if neither"
  - "Tag resolution: case-insensitive name match, ID fallback, ambiguity error with IDs"

requirements-completed: [CREA-01, CREA-02, CREA-03, CREA-04, CREA-05, CREA-08]

# Metrics
duration: 7min
completed: 2026-03-08
---

# Phase 15 Plan 02: Repository & Service Layer for Task Creation Summary

**Repository add_task protocol extension with HybridRepository bridge write-through, service-layer validation (name, parent, tag resolution), and factory bridge wiring**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-08T00:20:04Z
- **Completed:** 2026-03-08T00:26:49Z
- **Tasks:** 2
- **Files modified:** 10

## Accomplishments
- Repository protocol extended with add_task(spec, resolved_tag_ids) across all 3 implementations
- Service.add_task validates name (non-empty), resolves parent (project-first, then task), resolves tags (case-insensitive name, ID fallback, ambiguity error)
- TEMPORARY_simulate_write replaced with _mark_stale -- real bridge writes now flow through add_task
- Factory wires bridge into HybridRepository via create_bridge() for SAFE-01 compliance

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Repository layer** - `cc833a6` (test), `4b87fe8` (feat) -- protocol, hybrid, in-memory, bridge, factory
2. **Task 2: Service layer** - `b173555` (test), `83bbfa1` (feat) -- validation, parent resolution, tag resolution

## Files Created/Modified
- `src/omnifocus_operator/repository/protocol.py` - add_task method on Repository protocol
- `src/omnifocus_operator/repository/hybrid.py` - add_task via bridge + _mark_stale, bridge constructor param
- `src/omnifocus_operator/repository/in_memory.py` - add_task with synthetic ID and Task model construction
- `src/omnifocus_operator/repository/bridge.py` - add_task with cache invalidation
- `src/omnifocus_operator/repository/factory.py` - create_bridge wiring for hybrid mode
- `src/omnifocus_operator/service.py` - add_task with _resolve_parent, _resolve_tags
- `tests/test_hybrid_repository.py` - 8 new TestAddTask tests, updated freshness tests
- `tests/test_repository.py` - 5 new TestInMemoryAddTask tests
- `tests/test_repository_factory.py` - SAFE-01 bridge env var in hybrid tests
- `tests/test_service.py` - 13 new TestAddTask tests

## Decisions Made
- Repository.add_task takes resolved_tag_ids as keyword-only parameter -- tag name-to-ID resolution happens in service layer where it's testable without bridge
- Factory uses create_bridge() instead of direct RealBridge construction -- SAFE-01 is enforced during tests
- BridgeRepository invalidates cache by setting _cached=None (no WAL polling needed for bridge-only mode)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] BridgeRepository also needed add_task for protocol compliance**
- **Found during:** Task 1 (full test suite run)
- **Issue:** Adding add_task to Repository protocol broke BridgeRepository isinstance check
- **Fix:** Added add_task to BridgeRepository with cache invalidation
- **Files modified:** src/omnifocus_operator/repository/bridge.py
- **Verification:** All 379 tests pass
- **Committed in:** 4b87fe8 (Task 1 GREEN commit)

**2. [Rule 2 - Missing Critical] Factory SAFE-01 compliance**
- **Found during:** Task 1 (factory wiring)
- **Issue:** Direct RealBridge construction in factory would bypass SAFE-01 safety guard
- **Fix:** Used create_bridge() which enforces PYTEST_CURRENT_TEST check
- **Files modified:** src/omnifocus_operator/repository/factory.py, tests/test_repository_factory.py
- **Verification:** Factory tests set OMNIFOCUS_BRIDGE=inmemory, all pass
- **Committed in:** 4b87fe8 (Task 1 GREEN commit)

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both essential for correctness and safety. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Service.add_task complete with full validation pipeline
- Ready for Plan 15-03: MCP tool registration (add_tasks tool)
- All 379 tests passing

---
*Phase: 15-write-pipeline-task-creation*
*Completed: 2026-03-08*

## Self-Check: PASSED
