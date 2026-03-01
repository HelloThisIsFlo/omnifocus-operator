---
phase: 02-data-models
plan: 01
subsystem: models
tags: [pydantic, strenum, camelcase, alias-generator, data-models]

# Dependency graph
requires:
  - phase: 01-project-scaffolding
    provides: "Package structure, pyproject.toml with pydantic mypy plugin"
provides:
  - "OmniFocusBaseModel with camelCase alias config"
  - "OmniFocusEntity (id, name) and ActionableEntity (shared task/project fields)"
  - "TaskStatus (7 members) and EntityStatus (3 members) StrEnums"
  - "RepetitionRule and ReviewInterval standalone models"
  - "Factory functions for bridge-format JSON dicts (all entity types)"
affects: [02-data-models, 03-bridge, 04-repository, 05-mcp-server]

# Tech tracking
tech-stack:
  added: [pydantic.alias_generators.to_camel, pydantic.AwareDatetime, enum.StrEnum]
  patterns: [OmniFocusBaseModel ConfigDict, TYPE_CHECKING forward reference with model_rebuild]

key-files:
  created:
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/models/_base.py
    - src/omnifocus_operator/models/_enums.py
    - src/omnifocus_operator/models/_common.py
    - tests/test_models.py
  modified:
    - tests/conftest.py

key-decisions:
  - "Used TYPE_CHECKING import + model_rebuild() to break circular import between _base.py and _common.py"
  - "Fail-fast on unknown enum values (Pydantic default ValidationError, no fallback)"
  - "Field ordering: identity -> lifecycle -> flags -> dates -> metadata -> relationships"

patterns-established:
  - "OmniFocusBaseModel: ConfigDict(alias_generator=to_camel, validate_by_name=True, validate_by_alias=True)"
  - "Factory functions in conftest.py return bridge-format dicts with camelCase keys and exact field counts"
  - "Forward references resolved via model_rebuild() in __init__.py after all modules imported"

requirements-completed: [MODL-07]

# Metrics
duration: 4min
completed: 2026-03-01
---

# Phase 02 Plan 01: Base Models Summary

**Pydantic v2 base model hierarchy with camelCase aliases, StrEnum statuses, and factory fixtures for all OmniFocus entity types**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-01T22:35:57Z
- **Completed:** 2026-03-01T22:40:15Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- OmniFocusBaseModel -> OmniFocusEntity -> ActionableEntity inheritance chain with full camelCase alias config
- TaskStatus (7 values) and EntityStatus (3 values) StrEnums matching bridge script exactly
- RepetitionRule and ReviewInterval standalone Pydantic models
- Factory functions for all 5 entity types + snapshot with exact bridge field counts
- 22 tests passing, 92% coverage, mypy strict clean, ruff clean

## Task Commits

Each task was committed atomically:

1. **Task 1: Create enums, base model hierarchy, and common models**
   - `60ea517` (test) - TDD RED: failing tests for base models, enums, common models
   - `180bc74` (feat) - TDD GREEN: implement base models, enums, common models

2. **Task 2: Create test fixtures and tests**
   - `3366269` (test) - TDD RED: failing tests for factory functions
   - `ea4b2ff` (feat) - TDD GREEN: factory functions and additional tests

_Note: TDD tasks have RED (test) + GREEN (feat) commits_

## Files Created/Modified
- `src/omnifocus_operator/models/__init__.py` - Public API re-exports with model_rebuild()
- `src/omnifocus_operator/models/_base.py` - OmniFocusBaseModel, OmniFocusEntity, ActionableEntity
- `src/omnifocus_operator/models/_enums.py` - TaskStatus (7 members), EntityStatus (3 members)
- `src/omnifocus_operator/models/_common.py` - RepetitionRule, ReviewInterval
- `tests/test_models.py` - 22 tests covering MODL-07, enums, common models, factories
- `tests/conftest.py` - Factory functions for all bridge entity types

## Decisions Made
- Used TYPE_CHECKING import + model_rebuild() to break circular import between _base.py (ActionableEntity references RepetitionRule) and _common.py (RepetitionRule inherits OmniFocusBaseModel). This is a standard Pydantic pattern for forward references.
- Fail-fast on unknown enum values: Pydantic's default behavior raises ValidationError with clear error listing valid values. No fallback needed.
- Field ordering follows: identity -> lifecycle -> flags -> dates -> metadata -> relationships.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import between _base.py and _common.py**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** _base.py imported RepetitionRule from _common.py, and _common.py imported OmniFocusBaseModel from _base.py, causing circular import at runtime
- **Fix:** Used TYPE_CHECKING guard in _base.py for RepetitionRule import, added model_rebuild() call in __init__.py after both modules are loaded
- **Files modified:** src/omnifocus_operator/models/_base.py, src/omnifocus_operator/models/__init__.py
- **Verification:** All imports work, tests pass, mypy clean
- **Committed in:** 180bc74

**2. [Rule 1 - Bug] AwareDatetime import inside Pydantic model class body**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Test defined `from pydantic import AwareDatetime` inside a BaseModel subclass body, which Pydantic treated as a field definition
- **Fix:** Moved import above the class definition in the test method
- **Files modified:** tests/test_models.py
- **Verification:** Test passes correctly
- **Committed in:** 180bc74

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Base model hierarchy ready for Task, Project, Tag, Folder, Perspective models (Plan 02)
- Factory functions ready for reuse across all subsequent test modules
- ConfigDict pattern established: all models inherit camelCase alias config automatically

## Self-Check: PASSED

All 6 created/modified files verified on disk. All 4 task commits verified in git log.

---
*Phase: 02-data-models*
*Completed: 2026-03-01*
