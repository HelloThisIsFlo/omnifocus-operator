---
phase: 10-model-overhaul
plan: 02
subsystem: models
tags: [pydantic, strenum, two-axis-status, urgency, availability, model-migration]

# Dependency graph
requires:
  - phase: 10-01
    provides: Urgency and Availability enums, bridge adapter module
provides:
  - Two-axis status model (urgency + availability) on ActionableEntity
  - Simplified OmniFocusEntity without active/effective_active
  - Simplified ActionableEntity without completed/sequential/etc
  - TaskStatus and ProjectStatus enums deleted
  - All remaining enums use snake_case values
affects: [10-03, 11, 12, 13]

# Tech tracking
tech-stack:
  added: []
  patterns: [two-axis-status-model, snake-case-enum-values]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/enums.py
    - src/omnifocus_operator/models/base.py
    - src/omnifocus_operator/models/task.py
    - src/omnifocus_operator/models/project.py
    - src/omnifocus_operator/models/tag.py
    - src/omnifocus_operator/models/folder.py
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/bridge/factory.py
    - src/omnifocus_operator/simulator/data.py
    - tests/conftest.py
    - tests/test_models.py
    - tests/test_server.py
    - tests/test_adapter.py

key-decisions:
  - "Tasks 1+2 committed together to keep tests green at every commit"
  - "Adapter tests use local old-format factory functions, decoupled from shared conftest factories"
  - "InMemoryBridge seed data and simulator data updated to new shape (adapter not yet wired)"

patterns-established:
  - "Two-axis status: urgency (time pressure) + availability (work readiness) replaces old single-enum status"
  - "All enum values are snake_case strings (active, on_hold, due_soon, etc.)"

requirements-completed: [MODEL-03, MODEL-04, MODEL-05, MODEL-06]

# Metrics
duration: 6min
completed: 2026-03-07
---

# Phase 10 Plan 02: Model Migration Summary

**Two-axis status model (urgency + availability) replacing old TaskStatus/ProjectStatus enums, with 7 deprecated fields removed across all entity types**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-07T03:09:03Z
- **Completed:** 2026-03-07T03:15:00Z
- **Tasks:** 2
- **Files modified:** 13

## Accomplishments
- Migrated Task and Project from single-enum status to two-axis model (urgency + availability)
- Removed 7+ deprecated fields across base/entity hierarchy (active, effective_active, completed, completed_by_children, sequential, should_use_floating_time_zone, allows_next_action, contains_singleton_actions)
- Deleted TaskStatus and ProjectStatus enum classes entirely
- Switched all remaining enum values to snake_case (TagStatus, FolderStatus, ScheduleType, AnchorDateKey)
- All 227 tests pass with 98% coverage

## Task Commits

Tasks 1 and 2 committed together (as specified by plan to keep tests green):

1. **Task 1+2: Model migration + test updates** - `4331376` (feat)

## Files Created/Modified
- `src/omnifocus_operator/models/enums.py` - Deleted TaskStatus/ProjectStatus, snake_case values on all remaining enums
- `src/omnifocus_operator/models/base.py` - Removed active/effective_active from OmniFocusEntity; removed completed/sequential/etc from ActionableEntity; added urgency/availability
- `src/omnifocus_operator/models/task.py` - Removed status field, simplified docstring
- `src/omnifocus_operator/models/project.py` - Removed status/task_status/contains_singleton_actions
- `src/omnifocus_operator/models/tag.py` - Removed allows_next_action
- `src/omnifocus_operator/models/folder.py` - Updated docstring
- `src/omnifocus_operator/models/__init__.py` - Removed TaskStatus/ProjectStatus from namespace; added Urgency/Availability
- `src/omnifocus_operator/bridge/factory.py` - InMemoryBridge seed data updated to new model shape
- `src/omnifocus_operator/simulator/data.py` - Simulator snapshot updated to new model shape
- `tests/conftest.py` - All factories updated to new-shape dicts (27/29/8/7 field counts)
- `tests/test_models.py` - All assertions updated for new field names and counts
- `tests/test_server.py` - Inline fixture data updated to new shape
- `tests/test_adapter.py` - Decoupled from shared factories; uses local old-format factories

## Decisions Made
- Committed Tasks 1+2 together since models and tests must change atomically
- Adapter tests decoupled from shared conftest factories -- they need old-format data, so they get local `_old_task()` etc. helper functions
- InMemoryBridge seed data and simulator data updated to new shape immediately (adapter wiring in Plan 03 will handle real bridge data)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated InMemoryBridge factory seed data to new shape**
- **Found during:** Task 2 (test execution)
- **Issue:** `create_bridge("inmemory")` in factory.py had hardcoded old-format data; server integration tests failed with validation errors
- **Fix:** Updated all seed data in factory.py to new model shape (urgency/availability, snake_case enums, no deprecated fields)
- **Files modified:** src/omnifocus_operator/bridge/factory.py
- **Verification:** Server integration tests pass
- **Committed in:** 4331376

**2. [Rule 3 - Blocking] Updated simulator data to new shape**
- **Found during:** Task 2 (test execution)
- **Issue:** SIMULATOR_SNAPSHOT in simulator/data.py used old-format data; simulator integration test failed
- **Fix:** Updated all 10 tasks, 3 projects, 4 tags, 2 folders to new model shape
- **Files modified:** src/omnifocus_operator/simulator/data.py
- **Verification:** Simulator integration test passes
- **Committed in:** 4331376

**3. [Rule 3 - Blocking] Decoupled adapter tests from shared factories**
- **Found during:** Task 2 (test execution)
- **Issue:** test_adapter.py imported make_task_dict etc. from conftest, but adapter expects old-format dicts; shared factories now produce new-format
- **Fix:** Created local old-format factory functions (_old_task, _old_project, _old_tag, _old_folder, _old_snapshot) in test_adapter.py
- **Files modified:** tests/test_adapter.py
- **Verification:** All 42 adapter tests pass
- **Committed in:** 4331376

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All fixes necessary for test suite to pass. No scope creep -- just data format propagation.

## Issues Encountered
- Plan estimated field counts as Task:25, Project:28 but actual counts are Task:27, Project:29 (plan missed counting tags + repetition_rule on ActionableEntity). Updated all assertions accordingly.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All models use new two-axis status shape -- ready for Plan 03 (adapter wiring into repository)
- Adapter module exists but is not wired into any code path
- All 227 tests green, 98% coverage maintained

## Self-Check: PASSED
