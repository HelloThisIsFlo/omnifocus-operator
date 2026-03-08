---
phase: 16-task-editing
plan: 04
subsystem: api
tags: [bridge, pydantic, validation, mcp]

requires:
  - phase: 16-task-editing
    provides: "Edit task bridge dispatch, service layer, MCP tool registration"
provides:
  - "Fixed bridge removeTags key mismatch (BLOCKER resolved)"
  - "Clean Pydantic validation errors at model_validate sites"
  - "TaskEditSpec.tags accepts None for null-means-clear prep"
affects: [16-task-editing]

tech-stack:
  added: []
  patterns:
    - "ValidationError catch-and-clean at model_validate boundaries"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/bridge/bridge.js
    - bridge/tests/handleEditTask.test.js
    - src/omnifocus_operator/models/write.py
    - src/omnifocus_operator/server.py
    - tests/test_server.py

key-decisions:
  - "Pydantic ValidationError caught at both model_validate call sites, re-raised as clean ValueError"

patterns-established:
  - "ValidationError catch pattern: try/except at model_validate, join error msgs, raise ValueError from None"

requirements-completed: [EDIT-05, EDIT-09]

duration: 3min
completed: 2026-03-08
---

# Phase 16 Plan 04: Gap Closure -- Bridge Crash, Validation Noise, Tags Type

**Fixed bridge removeTags key mismatch (BLOCKER), cleaned Pydantic validation noise at model_validate boundaries, and updated TaskEditSpec.tags to accept None for null-means-clear**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T12:41:44Z
- **Completed:** 2026-03-08T12:45:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Bridge remove mode now reads `params.removeTagIds` instead of `params.tagIds` -- fixes crash when removeTags used alone
- Bridge test updated to pass `removeTagIds` matching real service-to-bridge contract
- Pydantic ValidationError caught at both `model_validate` call sites (add_tasks + edit_tasks), re-raised as clean ValueError
- TaskEditSpec.tags type updated to `list[str] | None | _Unset` preparing for null-means-clear semantics

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix bridge removeTags key mismatch, bridge test, and update tags model type** - `1378218` (fix)
2. **Task 2: Catch Pydantic ValidationError noise in server.py** - `796bf33` (fix)

## Files Created/Modified
- `src/omnifocus_operator/bridge/bridge.js` - Fixed remove mode to read `removeTagIds`
- `bridge/tests/handleEditTask.test.js` - Test uses `removeTagIds` matching real contract
- `src/omnifocus_operator/models/write.py` - TaskEditSpec.tags accepts None
- `src/omnifocus_operator/server.py` - ValidationError catch at both model_validate sites
- `tests/test_server.py` - 2 new tests for clean validation error output

## Decisions Made
- Pydantic ValidationError caught at model_validate boundaries and re-raised as clean ValueError with joined error messages -- keeps Pydantic internals out of MCP error responses

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Pre-commit hook detected pre-existing unstaged changes in service.py from other gap closure work, causing mypy failures. Resolved by letting the stash mechanism handle the separation cleanly.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Bridge removeTags blocker resolved -- UAT can now test remove-only tag operations
- Validation noise cleaned -- MCP clients see human-readable errors
- Tags type ready for Plan 05 null-means-clear service logic

---
*Phase: 16-task-editing*
*Completed: 2026-03-08*
