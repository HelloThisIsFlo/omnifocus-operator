---
phase: 16-task-editing
plan: 01
subsystem: models, bridge
tags: [pydantic, sentinel, patch-model, omnijs, vitest]

requires:
  - phase: 15-write-pipeline
    provides: TaskCreateSpec/TaskCreateResult patterns, handleAddTask bridge handler, OmniFocusBaseModel

provides:
  - UNSET sentinel for patch semantics (omit/null/value distinction)
  - TaskEditSpec patch model with tag mutual exclusivity validation
  - MoveToSpec with exactly-one-key constraint
  - TaskEditResult with optional warnings
  - handleEditTask bridge handler (fields, tags, movement)

affects: [16-02-service-repo, 16-03-mcp-tool]

tech-stack:
  added: [pydantic_core.core_schema.is_instance_schema]
  patterns: [UNSET sentinel for patch models, model_json_schema override for clean schemas, hasOwnProperty tag mode dispatch in bridge.js]

key-files:
  created:
    - bridge/tests/handleEditTask.test.js
  modified:
    - src/omnifocus_operator/models/write.py
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/bridge/bridge.js

key-decisions:
  - "_Unset uses __get_pydantic_core_schema__ with is_instance_schema for Pydantic v2 compatibility"
  - "model_json_schema override strips _Unset from JSON schema output for clean MCP tool schemas"
  - "Bridge tagMode dispatch: replace/add/remove/add_remove with removals-first ordering"
  - "Bridge moveTo uses position+containerId/anchorId shape (service layer translates from MoveToSpec)"

patterns-established:
  - "UNSET sentinel: singleton with __bool__=False, __get_pydantic_core_schema__, model_json_schema override"
  - "Patch model pattern: required id + UNSET defaults for all optional fields"
  - "Tag mode dispatch in bridge: tagMode string + tagIds/addTagIds/removeTagIds arrays"

requirements-completed: [EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-08]

duration: 5min
completed: 2026-03-08
---

# Phase 16 Plan 01: Models & Bridge Handler Summary

**UNSET sentinel with Pydantic v2 patch models (TaskEditSpec, MoveToSpec, TaskEditResult) and bridge.js handleEditTask with field/tag/movement dispatch**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-08T03:10:07Z
- **Completed:** 2026-03-08T03:15:00Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- UNSET sentinel with full Pydantic v2 integration (core schema, JSON schema cleanup)
- TaskEditSpec patch model: id required, all others UNSET-default, tag mutual exclusivity validator
- MoveToSpec: exactly-one-key constraint for beginning/ending/before/after positions
- handleEditTask bridge handler: hasOwnProperty field updates, 4 tag modes, 4 movement positions
- 32 Vitest tests covering all edge cases (field types, tag modes, movement, errors, combined ops)

## Task Commits

Each task was committed atomically:

1. **Task 1: UNSET sentinel + TaskEditSpec + MoveToSpec + TaskEditResult models** - `c2854d0` (feat)
2. **Task 2: bridge.js handleEditTask + dispatch wiring + Vitest tests** - `7acfe9a` (feat)

## Files Created/Modified
- `src/omnifocus_operator/models/write.py` - UNSET sentinel, MoveToSpec, TaskEditSpec, TaskEditResult, _clean_unset_from_schema helper
- `src/omnifocus_operator/models/__init__.py` - Re-exports and model_rebuild for new models
- `src/omnifocus_operator/bridge/bridge.js` - handleEditTask handler + edit_task dispatch route
- `bridge/tests/handleEditTask.test.js` - 32 Vitest tests for bridge edit handler

## Decisions Made
- Used `__get_pydantic_core_schema__` with `is_instance_schema` rather than `arbitrary_types_allowed` -- keeps type safety and works with union types
- Override `model_json_schema` with full signature match (not `**kwargs`) to satisfy mypy
- Bridge tagMode is a flat string discriminator (not nested objects) -- simpler for OmniJS
- Bridge moveTo uses `{position, containerId, anchorId}` shape -- service layer will translate from MoveToSpec's key-is-position design

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Pydantic schema generation error for _Unset type**
- **Found during:** Task 1 (model creation)
- **Issue:** Pydantic v2 cannot generate schema for arbitrary classes in union types
- **Fix:** Added `__get_pydantic_core_schema__` classmethod using `core_schema.is_instance_schema(cls)`
- **Files modified:** src/omnifocus_operator/models/write.py
- **Verification:** All model checks pass, JSON schema is clean
- **Committed in:** c2854d0 (Task 1 commit)

**2. [Rule 3 - Blocking] Pre-commit hook failures (ruff B007, mypy override signature)**
- **Found during:** Task 1 (commit attempt)
- **Issue:** Unused loop variables (ruff B007) and `model_json_schema(**kwargs)` signature incompatible with BaseModel supertype (mypy)
- **Fix:** Renamed unused vars to `_key`/`_def_name`, expanded `model_json_schema` signature to match parent's full parameter list
- **Files modified:** src/omnifocus_operator/models/write.py
- **Verification:** All pre-commit hooks pass
- **Committed in:** c2854d0 (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for Pydantic v2 compatibility and linter compliance. No scope creep.

## Issues Encountered

- Plan referenced `tests/bridge_tests/` path but actual test directory is `bridge/tests/` -- used correct path

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Models and bridge handler ready for Plan 02 (service layer, repository protocol)
- Service layer will translate TaskEditSpec -> bridge params (tag resolution, MoveToSpec -> moveTo shape)
- All existing tests pass (400 pytest, 68 Vitest)

---
*Phase: 16-task-editing*
*Completed: 2026-03-08*
