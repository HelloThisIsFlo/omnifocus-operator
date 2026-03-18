---
phase: 20-model-taxonomy
plan: 01
subsystem: api
tags: [pydantic, protocols, contracts, cqrs, model-taxonomy]

# Dependency graph
requires:
  - phase: 18-write-model-base
    provides: WriteModel base class, UNSET sentinel, _clean_unset_from_schema
  - phase: 19-in-memory-bridge-export
    provides: Clean InMemoryBridge exports, test infrastructure
provides:
  - contracts/ package with three-layer model taxonomy (Command, RepoPayload, RepoResult, Result)
  - Renamed sub-models: TagAction, MoveAction, EditTaskActions
  - Consolidated protocols: Service, Repository, Bridge in one file
  - New Service protocol (agent-facing boundary)
  - Typed CreateTaskRepoPayload, EditTaskRepoPayload, MoveToRepoPayload
  - Typed CreateTaskRepoResult, EditTaskRepoResult
affects: [20-02-import-migration, 21-pipeline-unification, 22-service-extraction]

# Tech tracking
tech-stack:
  added: []
  patterns: [three-layer-model-taxonomy, contracts-package, consolidated-protocols]

key-files:
  created:
    - src/omnifocus_operator/contracts/__init__.py
    - src/omnifocus_operator/contracts/base.py
    - src/omnifocus_operator/contracts/common.py
    - src/omnifocus_operator/contracts/protocols.py
    - src/omnifocus_operator/contracts/use_cases/__init__.py
    - src/omnifocus_operator/contracts/use_cases/create_task.py
    - src/omnifocus_operator/contracts/use_cases/edit_task.py
  modified: []

key-decisions:
  - "Tasks 1 and 2 committed together due to mypy requiring use_cases modules for protocols.py TYPE_CHECKING imports"
  - "MoveAction and TagAction imports in edit_task.py placed under TYPE_CHECKING per ruff TC001, resolved by model_rebuild in __init__.py"

patterns-established:
  - "Three-layer naming: Command (agent intent), RepoPayload (bridge-ready), RepoResult (repo confirmation), Result (agent outcome)"
  - "contracts/ package with use_cases/ subdirectory per operation"
  - "model_rebuild() with shared namespace in contracts/__init__.py for forward ref resolution"

requirements-completed: [MODL-01, MODL-04]

# Metrics
duration: 5min
completed: 2026-03-18
---

# Phase 20 Plan 01: Contracts Package Summary

**Seven-file contracts/ package with three-layer model taxonomy (Command/RepoPayload/RepoResult/Result), consolidated Service/Repository/Bridge protocols, and renamed value objects (TagAction, MoveAction, EditTaskActions)**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-18T15:25:20Z
- **Completed:** 2026-03-18T15:30:09Z
- **Tasks:** 2
- **Files created:** 7

## Accomplishments
- Created contracts/ package with full typed contract for write pipeline
- Three layers distinguishable by class name: Command, RepoPayload, RepoResult, Result
- All protocols (Service, Repository, Bridge) consolidated in one file
- New Service protocol defines the agent-facing boundary (didn't exist before)
- model_rebuild with AwareDatetime namespace resolves all forward references
- All 517 existing tests pass unchanged -- purely additive

## Task Commits

Each task was committed atomically:

1. **Task 1: Create contracts/ base, common, protocols, and use_cases modules** - `1eec555` (feat)
2. **Task 2: Add contracts/__init__.py with model_rebuild and re-exports** - `f69bd2e` (feat)

## Files Created
- `src/omnifocus_operator/contracts/__init__.py` - Re-exports + model_rebuild for all contracts models
- `src/omnifocus_operator/contracts/base.py` - CommandModel, UNSET sentinel, _clean_unset_from_schema
- `src/omnifocus_operator/contracts/common.py` - TagAction, MoveAction shared value objects
- `src/omnifocus_operator/contracts/protocols.py` - Service, Repository, Bridge protocols
- `src/omnifocus_operator/contracts/use_cases/__init__.py` - Empty package init
- `src/omnifocus_operator/contracts/use_cases/create_task.py` - CreateTaskCommand, CreateTaskRepoPayload, CreateTaskRepoResult, CreateTaskResult
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` - EditTaskCommand, EditTaskActions, EditTaskRepoPayload, MoveToRepoPayload, EditTaskRepoResult, EditTaskResult

## Decisions Made
- Tasks 1 and 2 were committed with use_cases modules in the first commit because mypy requires the modules to exist for TYPE_CHECKING imports in protocols.py. The __init__.py (model_rebuild) was committed separately as Task 2.
- MoveAction and TagAction imports in edit_task.py placed under TYPE_CHECKING per ruff TC001 rule. model_rebuild in __init__.py resolves them at runtime.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Created use_cases modules in Task 1 commit**
- **Found during:** Task 1
- **Issue:** protocols.py has TYPE_CHECKING imports from use_cases/create_task.py and use_cases/edit_task.py. Mypy pre-commit hook requires these modules to exist even for TYPE_CHECKING imports.
- **Fix:** Created full use_cases module files in the Task 1 commit instead of deferring to Task 2
- **Files modified:** use_cases/create_task.py, use_cases/edit_task.py, use_cases/__init__.py
- **Verification:** mypy passes, all 517 tests pass
- **Committed in:** 1eec555

---

**Total deviations:** 1 auto-fixed (blocking)
**Impact on plan:** Task 2's use_cases file creation was pulled into Task 1 for mypy compliance. Task 2 commit contains only the __init__.py with model_rebuild. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- contracts/ package is fully importable and schema-generatable
- Ready for Plan 02 (import migration) to rewire existing code to use contracts/ models
- All new models coexist with old models in models/write.py -- no breaking changes

## Self-Check: PASSED

- All 7 created files exist
- Both commits (1eec555, f69bd2e) verified in git log

---
*Phase: 20-model-taxonomy*
*Completed: 2026-03-18*
