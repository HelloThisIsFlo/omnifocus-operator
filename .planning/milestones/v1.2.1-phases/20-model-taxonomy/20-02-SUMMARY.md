---
phase: 20-model-taxonomy
plan: 02
subsystem: api
tags: [pydantic, contracts, imports, typed-payloads, migration]

# Dependency graph
requires:
  - phase: 20-model-taxonomy-01
    provides: contracts/ package with Command, RepoPayload, RepoResult, Result models and consolidated protocols
provides:
  - All source code using contracts/ imports exclusively
  - Service builds typed CreateTaskRepoPayload and EditTaskRepoPayload
  - All three repos (Hybrid, Bridge, InMemory) accept typed payloads, return typed results
  - models/__init__.py exports read-side models only
  - Old files deleted: models/write.py, bridge/protocol.py, repository/protocol.py
affects: [21-pipeline-unification, 22-service-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns: [exclude-unset-for-clear-semantics, shared-unset-singleton, model-validate-for-partial-construction]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/service.py
    - src/omnifocus_operator/server.py
    - src/omnifocus_operator/repository/hybrid.py
    - src/omnifocus_operator/repository/bridge.py
    - src/omnifocus_operator/repository/in_memory.py
    - src/omnifocus_operator/repository/__init__.py
    - src/omnifocus_operator/repository/factory.py
    - src/omnifocus_operator/bridge/__init__.py
    - src/omnifocus_operator/bridge/factory.py
    - src/omnifocus_operator/models/__init__.py
    - tests/test_service.py
    - tests/test_models.py
    - tests/test_repository.py
    - tests/test_hybrid_repository.py
    - tests/test_simulator_bridge.py

key-decisions:
  - "edit_task repos use exclude_unset=True (not exclude_none) to preserve null-means-clear semantics"
  - "models/write.py _Unset replaced with import from contracts.base for singleton compatibility during migration"
  - "test_models.py and test_service.py migrated in Task 1 (Rule 3 blocking) instead of Task 2 as planned"
  - "Service builds EditTaskRepoPayload via model_validate with dynamic kwargs dict to support exclude_unset"

patterns-established:
  - "exclude_unset=True on edit repo payloads: None means clear, unset means unchanged"
  - "Service constructs repo kwargs dict dynamically, passing only user-changed fields"

requirements-completed: [MODL-02, MODL-03]

# Metrics
duration: 21min
completed: 2026-03-18
---

# Phase 20 Plan 02: Import Migration Summary

**Atomic switch from old paths to contracts/: all source+test imports migrated, typed repo payloads with null-means-clear semantics, three old files deleted**

## Performance

- **Duration:** 21 min
- **Started:** 2026-03-18T15:32:35Z
- **Completed:** 2026-03-18T15:53:35Z
- **Tasks:** 2
- **Files modified:** 15 (10 source + 5 test)
- **Files deleted:** 3

## Accomplishments
- All source code imports from contracts/ -- zero references to old paths
- Service builds typed CreateTaskRepoPayload and EditTaskRepoPayload for the repo boundary
- All three repos (Hybrid, Bridge, InMemory) accept typed payloads and return typed results
- models/__init__.py exports read-side models only (write models removed)
- Old files deleted: models/write.py, bridge/protocol.py, repository/protocol.py
- All 517 tests pass with only import/class-name changes (no assertion changes)
- mypy passes clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate source code to contracts/ imports and typed signatures** - `b8123b8` (feat)
2. **Task 2: Migrate test imports and delete old files** - `aeca701` (feat)

## Files Modified
- `src/omnifocus_operator/service.py` - CreateTaskCommand/EditTaskCommand params, typed repo payloads
- `src/omnifocus_operator/server.py` - CreateTaskCommand/EditTaskCommand for validation
- `src/omnifocus_operator/repository/hybrid.py` - Typed add_task/edit_task signatures
- `src/omnifocus_operator/repository/bridge.py` - Typed add_task/edit_task signatures
- `src/omnifocus_operator/repository/in_memory.py` - Typed add_task/edit_task signatures
- `src/omnifocus_operator/repository/__init__.py` - Repository from contracts.protocols
- `src/omnifocus_operator/repository/factory.py` - Repository from contracts.protocols
- `src/omnifocus_operator/bridge/__init__.py` - Bridge from contracts.protocols
- `src/omnifocus_operator/bridge/factory.py` - Bridge from contracts.protocols
- `src/omnifocus_operator/models/__init__.py` - Read-side only, write re-exports removed

## Files Deleted
- `src/omnifocus_operator/models/write.py` - Replaced by contracts/
- `src/omnifocus_operator/bridge/protocol.py` - Replaced by contracts/protocols.py
- `src/omnifocus_operator/repository/protocol.py` - Replaced by contracts/protocols.py

## Decisions Made
- **exclude_unset vs exclude_none**: edit_task repos use `exclude_unset=True` so that `None` values (meaning "clear this field") are preserved in the bridge payload. Service constructs `EditTaskRepoPayload` via `model_validate()` with a dynamic kwargs dict containing only user-changed fields.
- **Shared _Unset singleton**: During migration, `models/write.py` was updated to import `_Unset` from `contracts.base` instead of defining its own. This ensured `isinstance` checks in the service worked with both old (test) and new (source) model classes.
- **test_models.py migrated early**: Module-level imports from `omnifocus_operator.models` broke test collection after write model re-exports were removed. Migrated in Task 1 per Rule 3 (blocking).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] test_models.py migrated in Task 1 instead of Task 2**
- **Found during:** Task 1 (after removing write model re-exports from models/__init__.py)
- **Issue:** test_models.py has module-level imports of TaskCreateResult, TaskCreateSpec from omnifocus_operator.models. Removing re-exports broke test collection.
- **Fix:** Migrated test_models.py imports to contracts/ paths in Task 1
- **Files modified:** tests/test_models.py
- **Verification:** All 517 tests pass
- **Committed in:** b8123b8

**2. [Rule 1 - Bug] _Unset singleton incompatibility between models.write and contracts.base**
- **Found during:** Task 1 (after service switched to contracts.base._Unset)
- **Issue:** models.write._Unset and contracts.base._Unset are different classes. isinstance checks in service failed when tests passed old model instances.
- **Fix:** models/write.py imports _Unset and UNSET from contracts.base instead of defining its own
- **Files modified:** src/omnifocus_operator/models/write.py
- **Verification:** All 517 tests pass, isinstance checks work correctly
- **Committed in:** b8123b8

**3. [Rule 1 - Bug] null-means-clear broken by exclude_none=True in repos**
- **Found during:** Task 1 (test_edit_tasks_clear_field failure)
- **Issue:** Repos used `model_dump(exclude_none=True)` which stripped None values meant to clear fields (e.g., dueDate=null)
- **Fix:** Changed to `exclude_unset=True`. Service builds repo payload via model_validate with dynamic kwargs so only user-changed fields are "set".
- **Files modified:** service.py, repository/hybrid.py, repository/bridge.py, repository/in_memory.py
- **Verification:** test_edit_tasks_clear_field passes, all 517 tests pass
- **Committed in:** b8123b8

**4. [Rule 3 - Blocking] test_service.py isinstance check for CreateTaskResult**
- **Found during:** Task 1 (1 test checking isinstance(result, TaskCreateResult))
- **Issue:** Service returns CreateTaskResult (contracts) but test checked isinstance against TaskCreateResult (models.write) -- different classes
- **Fix:** Migrated that one test's import to contracts
- **Files modified:** tests/test_service.py (1 test)
- **Verification:** Test passes
- **Committed in:** b8123b8

**5. [Rule 3 - Blocking] test_simulator_bridge.py imports from deleted bridge/protocol.py**
- **Found during:** Task 2 (after deleting bridge/protocol.py)
- **Issue:** test_satisfies_bridge_protocol imported Bridge from omnifocus_operator.bridge.protocol
- **Fix:** Updated import to contracts.protocols
- **Files modified:** tests/test_simulator_bridge.py
- **Verification:** Test passes
- **Committed in:** aeca701

---

**Total deviations:** 5 auto-fixed (2 bugs, 3 blocking)
**Impact on plan:** Task boundary shifted -- test_models.py and one test_service.py test migrated in Task 1 instead of Task 2. The null-means-clear fix required a design refinement (exclude_unset + dynamic kwargs). No scope creep.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All imports use contracts/ paths exclusively
- Typed repo boundary established (CreateTaskRepoPayload, EditTaskRepoPayload)
- Ready for Phase 21 (pipeline unification) to replace service's internal dict-building with direct typed payload construction
- The dict-building in service.edit_task is the last remnant of the old approach -- Phase 21 can eliminate it

## Self-Check: PASSED

- All 15 modified files verified in commits
- Both commits (b8123b8, aeca701) verified in git log
- 3 deleted files confirmed absent
- 517 tests pass, mypy clean

---
*Phase: 20-model-taxonomy*
*Completed: 2026-03-18*
