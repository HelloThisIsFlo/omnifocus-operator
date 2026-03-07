---
phase: 02-data-models
plan: 02
subsystem: models
tags: [pydantic, entity-models, round-trip, database-snapshot, type-checking]

# Dependency graph
requires:
  - phase: 02-data-models
    plan: 01
    provides: "OmniFocusBaseModel, OmniFocusEntity, ActionableEntity, enums, common models, factory functions"
provides:
  - "Task model (32 fields) matching bridge flattenedTasks output"
  - "Project model (31 fields) matching bridge flattenedProjects output"
  - "Tag model (9 fields), Folder model (8 fields), Perspective model (3 fields with nullable id)"
  - "DatabaseSnapshot aggregating all 5 entity collections"
  - "Full bridge JSON round-trip test coverage for all entity types"
affects: [03-bridge, 04-repository, 05-mcp-server]

# Tech tracking
tech-stack:
  added: []
  patterns: [TYPE_CHECKING imports with _types_namespace for Pydantic rebuild, model_rebuild ordering]

key-files:
  created:
    - src/omnifocus_operator/models/_task.py
    - src/omnifocus_operator/models/_project.py
    - src/omnifocus_operator/models/_tag.py
    - src/omnifocus_operator/models/_folder.py
    - src/omnifocus_operator/models/_perspective.py
    - src/omnifocus_operator/models/_snapshot.py
  modified:
    - src/omnifocus_operator/models/__init__.py
    - tests/test_models.py

key-decisions:
  - "TYPE_CHECKING imports + _types_namespace dict for model_rebuild() to satisfy both ruff TC rules and Pydantic runtime resolution"
  - "Task-specific fields (added, modified, active, effectiveActive) placed on Task not ActionableEntity since Project lacks them in bridge output"
  - "Perspective extends OmniFocusBaseModel (not OmniFocusEntity) because builtin perspectives have null id"

patterns-established:
  - "model_rebuild(_types_namespace=_ns) pattern: centralized namespace dict in __init__.py for all forward reference resolution"
  - "Rebuild ordering: base -> subclasses -> aggregators (ActionableEntity -> Task -> Project -> Tag -> Folder -> DatabaseSnapshot)"

requirements-completed: [MODL-01, MODL-02, MODL-03, MODL-04, MODL-05, MODL-06]

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 02 Plan 02: Entity Models Summary

**All OmniFocus entity models (Task/32, Project/31, Tag/9, Folder/8, Perspective/3) with DatabaseSnapshot aggregator and bridge JSON round-trip validation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-01T22:42:50Z
- **Completed:** 2026-03-01T22:47:14Z
- **Tasks:** 2
- **Files modified:** 8

## Accomplishments
- Task model with 32 fields (7 entity-specific + 25 inherited from ActionableEntity)
- Project model with 31 fields including dual status (EntityStatus + TaskStatus) and nested ReviewInterval
- Tag (9), Folder (8), Perspective (3 with nullable id) models matching bridge output exactly
- DatabaseSnapshot aggregator for all 5 entity collections
- 17 new tests covering round-trips, validation errors, nested objects, and full payload fidelity
- 39 total model tests passing, 96% coverage, mypy strict clean, ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Implement entity models and DatabaseSnapshot**
   - `4a1fd87` (test) - TDD RED: failing tests for all entity models and DatabaseSnapshot
   - `225f5a0` (feat) - TDD GREEN: implement all 6 model files + __init__.py updates

2. **Task 2: Comprehensive test suite**
   - Tests written in Task 1 RED phase (4a1fd87) -- both tasks share the same TDD cycle
   - All 17 entity tests verified passing in Task 1 GREEN phase (225f5a0)

_Note: TDD tasks have RED (test) + GREEN (feat) commits_

## Files Created/Modified
- `src/omnifocus_operator/models/_task.py` - Task model: 32 fields (ActionableEntity + status, inbox, relationships)
- `src/omnifocus_operator/models/_project.py` - Project model: 31 fields (ActionableEntity + dual status, review, structure)
- `src/omnifocus_operator/models/_tag.py` - Tag model: 9 fields (OmniFocusEntity + lifecycle, allowsNextAction)
- `src/omnifocus_operator/models/_folder.py` - Folder model: 8 fields (OmniFocusEntity + lifecycle)
- `src/omnifocus_operator/models/_perspective.py` - Perspective model: 3 fields (OmniFocusBaseModel with nullable id)
- `src/omnifocus_operator/models/_snapshot.py` - DatabaseSnapshot: aggregates all 5 entity lists
- `src/omnifocus_operator/models/__init__.py` - Re-exports + model_rebuild() with _types_namespace
- `tests/test_models.py` - 17 new tests (39 total) covering MODL-01 through MODL-06

## Decisions Made
- Used TYPE_CHECKING imports in all entity modules (ruff TC rule compliance) combined with centralized `_types_namespace` dict in `__init__.py` for Pydantic model_rebuild(). This satisfies both ruff's type-checking import rules and Pydantic's runtime type resolution needs.
- Placed `added`, `modified`, `active`, `effective_active` on Task (not ActionableEntity) because Project lacks these fields in the bridge script output. Cross-referenced with bridge script flattenedProjects.map() to confirm.
- Perspective inherits from OmniFocusBaseModel (not OmniFocusEntity) because builtin perspectives have `id: null` which violates OmniFocusEntity's `id: str` contract.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Forward reference resolution for Task model_rebuild()**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Task.model_rebuild() failed with `PydanticUserError: Task is not fully defined` because RepetitionRule was a TYPE_CHECKING-only import in ActionableEntity
- **Fix:** Added Task.model_rebuild() call after ActionableEntity.model_rebuild() in __init__.py
- **Files modified:** src/omnifocus_operator/models/__init__.py
- **Verification:** All 39 tests pass
- **Committed in:** 225f5a0

**2. [Rule 3 - Blocking] Ruff TC001/TC002 violations requiring TYPE_CHECKING refactor**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** ruff check flagged 14 TC001/TC002 errors for imports only used in annotations (with `from __future__ import annotations`)
- **Fix:** Moved all type-only imports under TYPE_CHECKING blocks; added `_types_namespace` dict to model_rebuild() calls so Pydantic can resolve string annotations at runtime
- **Files modified:** All 6 entity model files + __init__.py
- **Verification:** ruff check clean, mypy clean, all tests pass
- **Committed in:** 225f5a0

---

**Total deviations:** 2 auto-fixed (2 blocking)
**Impact on plan:** Both fixes necessary for correctness with project linting config. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Complete models package ready: all entity types + DatabaseSnapshot
- Factory functions available for all entity types (from Plan 01)
- All models round-trip from bridge JSON (camelCase) to Python (snake_case) and back
- Phase 02 (Data Models) fully complete -- ready for Phase 03 (Bridge)

## Self-Check: PASSED

All 9 created/modified files verified on disk. All 2 task commits verified in git log.

---
*Phase: 02-data-models*
*Completed: 2026-03-01*
