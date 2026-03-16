---
phase: 16-task-editing
plan: 02
subsystem: api
tags: [repository, service, validation, cycle-detection, patch-semantics]

# Dependency graph
requires:
  - phase: 16-task-editing (plan 01)
    provides: "TaskEditSpec, TaskEditResult, MoveToSpec, UNSET sentinel, bridge edit_task handler"
provides:
  - "Repository.edit_task on protocol + 3 implementations"
  - "Service.edit_task with full validation, tag resolution, moveTo, cycle detection"
  - "20 service-layer edit tests covering EDIT-01 through EDIT-08"
affects: [16-task-editing plan 03 (MCP tool)]

# Tech tracking
tech-stack:
  added: []
  patterns: [UNSET-aware payload construction, assert-based type narrowing for mypy]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/protocol.py
    - src/omnifocus_operator/repository/hybrid.py
    - src/omnifocus_operator/repository/bridge.py
    - src/omnifocus_operator/repository/in_memory.py
    - src/omnifocus_operator/service.py
    - tests/test_service.py

key-decisions:
  - "Repository.edit_task takes pre-built dict payload (not TaskEditSpec) -- service does intelligence, repo does transport"
  - "InMemoryRepository edit_task mutates snapshot in-place with simplified tag/moveTo handling for testing"
  - "Cycle detection walks parent chain from container upward via get_all task map"
  - "Assert isinstance(spec.X, list) for mypy type narrowing after boolean has_X checks"

patterns-established:
  - "UNSET-aware payload builder: manually build dict skipping _Unset fields, preserving None for clears"
  - "Educational warnings: non-error feedback for no-op operations (tag not on task)"

requirements-completed: [EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-07, EDIT-08]

# Metrics
duration: 5min
completed: 2026-03-08
---

# Phase 16 Plan 02: Service & Repository edit_task Summary

**Repository edit_task on protocol + 3 implementations, service layer with patch validation, tag resolution (4 modes), moveTo with cycle detection, and 20 tests**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-08T03:17:18Z
- **Completed:** 2026-03-08T03:22:40Z
- **Tasks:** 2
- **Files modified:** 6

## Accomplishments
- edit_task added to Repository protocol and all 3 implementations (Hybrid, Bridge, InMemory)
- Service.edit_task with full validation: task exists, name non-empty, tag exclusivity, parent resolution, cycle detection
- Payload construction skips UNSET but preserves None (clear) -- no model_dump shortcut
- 4 tag modes: replace, add, remove, add_remove with resolved IDs
- Educational warnings for no-op tag removals
- 20 tests covering all EDIT requirements, cycle detection, and edge cases

## Task Commits

Each task was committed atomically:

1. **Task 1: Repository protocol + implementations** - `05909c8` (feat)
2. **Task 2: Service layer edit_task + tests** - `1c2bd5a` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/protocol.py` - Added edit_task method signature
- `src/omnifocus_operator/repository/hybrid.py` - edit_task delegates to bridge + marks stale
- `src/omnifocus_operator/repository/bridge.py` - edit_task delegates to bridge + invalidates cache
- `src/omnifocus_operator/repository/in_memory.py` - edit_task mutates snapshot in-place (tags, moveTo, fields)
- `src/omnifocus_operator/service.py` - edit_task with validation, tag resolution, moveTo, cycle detection
- `tests/test_service.py` - 20 new TestEditTask tests

## Decisions Made
- Repository.edit_task takes pre-built dict payload (consistent with add_task taking resolved_tag_ids)
- InMemoryRepository edit_task simplified mutation -- full OmniJS behavior tested via Vitest
- Cycle detection uses get_all() to build task map and walks parent chain
- Assert isinstance for mypy type narrowing after boolean UNSET checks

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- Ruff format and mypy pre-commit hooks caught style issues and type narrowing needs on first commit attempt -- fixed by combining if statements (SIM102) and adding assert isinstance for mypy

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Repository and service layers complete for edit_task
- Ready for Plan 03: MCP tool registration (edit_tasks tool)

---
*Phase: 16-task-editing*
*Completed: 2026-03-08*
