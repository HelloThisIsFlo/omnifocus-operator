---
phase: quick-2
plan: 01
subsystem: infra
tags: [refactoring, file-layout, imports]

provides:
  - "Underscore-free module names in models/ and repository/mtime"
affects: [all phases that import from models/]

tech-stack:
  added: []
  patterns:
    - "Non-underscore module names for fuzzy-find friendliness"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/models/base.py
    - src/omnifocus_operator/models/common.py
    - src/omnifocus_operator/models/enums.py
    - src/omnifocus_operator/models/snapshot.py
    - src/omnifocus_operator/models/folder.py
    - src/omnifocus_operator/models/perspective.py
    - src/omnifocus_operator/models/project.py
    - src/omnifocus_operator/models/tag.py
    - src/omnifocus_operator/models/task.py
    - src/omnifocus_operator/repository/__init__.py
    - src/omnifocus_operator/repository/mtime.py
    - src/omnifocus_operator/repository/_repository.py
    - src/omnifocus_operator/service/_service.py

key-decisions:
  - "Only rename modules where no test files import from the underscore path directly"
  - "Skip collapsing server/service/repository packages -- tests depend on internal module paths for patching"

requirements-completed: []

duration: 9min
completed: 2026-03-06
---

# Quick Task 2: Simplify File Layout Summary

**Dropped _ prefix from 10 internal modules (models/ and repository/mtime) with zero test modifications**

## Performance

- **Duration:** 9 min
- **Started:** 2026-03-06T23:42:50Z
- **Completed:** 2026-03-06T23:51:53Z
- **Tasks:** 1 of 3 (Task 2 skipped, Task 3 merged into Task 1)
- **Files modified:** 14

## Accomplishments
- Renamed 9 models/ files: `_base.py` -> `base.py`, `_common.py` -> `common.py`, etc.
- Renamed `repository/_mtime.py` -> `repository/mtime.py`
- Updated all internal imports across src/ to match new names
- All 182 tests pass, mypy clean, ruff clean

## Task Commits

1. **Task 1: Drop _ prefixes on models/ and repository/mtime** - `24a1d52` (refactor)

## Files Created/Modified
- `src/omnifocus_operator/models/*.py` (9 renames) - Dropped underscore prefix
- `src/omnifocus_operator/models/__init__.py` - Updated import paths
- `src/omnifocus_operator/repository/mtime.py` - Renamed from `_mtime.py`
- `src/omnifocus_operator/repository/__init__.py` - Updated import path
- `src/omnifocus_operator/repository/_repository.py` - Updated TYPE_CHECKING import
- `src/omnifocus_operator/service/_service.py` - Updated TYPE_CHECKING import

## Decisions Made
- **Scope reduced from 16 renames to 10**: Tests import directly from underscore submodules in bridge/, server/, service/, repository/_repository, and simulator/_data. Renaming those would break tests, which violates the "no test modifications" constraint.
- **Package collapse skipped entirely**: Tests import `server._server._register_tools` and patch `bridge._real.asyncio` by module path. Collapsing packages would break these patch targets. Shim modules were attempted but fail for `unittest.mock.patch` targets (the patch must target the module where the code lives, not a re-export shim).

## Deviations from Plan

### Task 2 (Collapse single-file packages) -- SKIPPED

- **Reason:** Tests directly import from underscore submodules (`server._server._register_tools`, `server._server.app_lifespan`) and patch internal module attributes (`bridge._real.asyncio`). Python's `unittest.mock.patch` requires the patch target to be the actual module containing the code -- re-export shims don't intercept attribute access for patching. Collapsing packages while keeping tests working is impossible without modifying test files.
- **Impact:** File count stays at 29 instead of reducing to 23. The 10 renames still improve fuzzy-find ergonomics for the most frequently navigated files (models).

### Reduced rename scope (Task 1)

- **Planned:** 16 file renames (models: 9, bridge: 6, simulator: 1)
- **Actual:** 10 file renames (models: 9, repository: 1)
- **Reason:** Bridge files (6), server/_server.py, service/_service.py, repository/_repository.py, and simulator/_data.py have test imports at underscore paths. Cannot rename without test changes.

---

**Total deviations:** 1 task skipped, 1 task reduced scope
**Impact on plan:** Partial achievement -- models/ (the largest package, 9 files) is fully cleaned up. Remaining underscore files require a follow-up that includes test import updates.

## Issues Encountered
- First attempt tried full 16 renames + collapse, discovered test failures, reverted via `git reset --hard`
- Shim-based approach for backward compat failed because `mock.patch("module.asyncio")` must target the actual module, not a re-export

## User Setup Required
None - no external service configuration required.

## Deferred Items
- Rename remaining 10 underscore files (bridge: 6, server: 1, service: 1, repository: 1, simulator: 1) -- requires updating test import paths
- Collapse server/, service/, repository/ into plain modules -- requires updating test import paths and patch targets

---
*Quick task: 2-simplify-file-layout-drop-prefixes-colla*
*Completed: 2026-03-06*
