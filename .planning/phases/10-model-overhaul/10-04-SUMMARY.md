---
phase: 10-model-overhaul
plan: 04
subsystem: models
tags: [pydantic, enums, adapter, bridge]

# Dependency graph
requires:
  - phase: 10-model-overhaul (plans 01-03)
    provides: two-axis status model, adapter pipeline, bridge wiring
provides:
  - effectiveCompletionDate removed from Project (Task-only)
  - ScheduleType reduced to 2 values (no "none")
  - TagAvailability / FolderAvailability enums with unified vocabulary
  - Adapter guardrail for scheduleType "None" -> repetitionRule null
affects: [11-datasource-protocol, 12-sqlite-reader, test-omnifocus-operator skill]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Adapter nullifies parent entity field when bridge sends sentinel value"
    - "Availability enum unification across all entity types"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/enums.py
    - src/omnifocus_operator/models/base.py
    - src/omnifocus_operator/models/task.py
    - src/omnifocus_operator/models/tag.py
    - src/omnifocus_operator/models/folder.py
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/bridge/adapter.py
    - src/omnifocus_operator/bridge/factory.py
    - src/omnifocus_operator/simulator/data.py
    - tests/conftest.py
    - tests/test_models.py
    - tests/test_adapter.py

key-decisions:
  - "Move effective_completion_date from ActionableEntity to Task rather than using Pydantic exclude -- cleaner inheritance"
  - "Adapter nullifies entire repetitionRule when scheduleType is 'None' rather than mapping to an enum value"
  - "Adapter pops bridge 'status' and writes 'availability' for tags/folders -- field rename happens at adapter boundary"

patterns-established:
  - "Availability vocabulary unified: all entity types use 'available/blocked/dropped' consistently"

requirements-completed: [MODEL-04, MODEL-05, MODEL-06]

# Metrics
duration: 7min
completed: 2026-03-07
---

# Phase 10 Plan 04: UAT Gap Closure Summary

**Removed dead Project field, eliminated ScheduleType.none, unified tag/folder vocabulary to TagAvailability/FolderAvailability**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-07T13:14:59Z
- **Completed:** 2026-03-07T13:22:30Z
- **Tasks:** 2
- **Files modified:** 12

## Accomplishments
- effectiveCompletionDate moved from ActionableEntity to Task -- Project no longer exposes it
- ScheduleType enum reduced from 3 to 2 values; bridge "None" now nullifies entire repetitionRule
- TagStatus -> TagAvailability (available/blocked/dropped), FolderStatus -> FolderAvailability (available/dropped)
- Tag.status -> Tag.availability, Folder.status -> Folder.availability across entire codebase
- 233 Python tests + 26 Vitest tests pass at 98.52% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Remove effectiveCompletionDate from Project + remove ScheduleType.none + add adapter guardrail** - `15513f3` (feat)
2. **Task 2: Rename TagStatus/FolderStatus to TagAvailability/FolderAvailability with unified values** - `c7bb564` (feat)

## Files Created/Modified
- `src/omnifocus_operator/models/enums.py` - TagAvailability/FolderAvailability enums, ScheduleType reduced
- `src/omnifocus_operator/models/base.py` - Removed effective_completion_date from ActionableEntity
- `src/omnifocus_operator/models/task.py` - Added effective_completion_date as Task-only field
- `src/omnifocus_operator/models/tag.py` - status -> availability with TagAvailability type
- `src/omnifocus_operator/models/folder.py` - status -> availability with FolderAvailability type
- `src/omnifocus_operator/models/__init__.py` - Updated exports and namespace
- `src/omnifocus_operator/bridge/adapter.py` - New availability maps, scheduleType None guardrail
- `src/omnifocus_operator/bridge/factory.py` - Updated InMemoryBridge seed data
- `src/omnifocus_operator/simulator/data.py` - Updated simulator snapshot data
- `tests/conftest.py` - Updated factory functions
- `tests/test_models.py` - Updated enum and model tests
- `tests/test_adapter.py` - Updated adapter tests for new field names and values

## Decisions Made
- Move effective_completion_date to Task directly rather than using Pydantic field exclusion -- cleaner inheritance, no runtime overhead
- Adapter nullifies entire repetitionRule dict when bridge sends scheduleType "None" -- maps to Python None rather than a sentinel enum
- Adapter pops bridge "status" key and writes "availability" key for tags/folders -- field rename at adapter boundary

## Deviations from Plan

None - plan executed exactly as written.

## Deferred Items

- **Skill script uses old enum names:** `.claude/skills/test-omnifocus-operator/scripts/analyze_snapshot.py` imports `TagStatus`/`FolderStatus` which no longer exist. Logged to `deferred-items.md`. Out of scope for this plan.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 10 model overhaul is now fully complete (plans 01-04)
- All UAT gaps closed
- Ready for Phase 11 (DataSource Protocol)

---
*Phase: 10-model-overhaul*
*Completed: 2026-03-07*
