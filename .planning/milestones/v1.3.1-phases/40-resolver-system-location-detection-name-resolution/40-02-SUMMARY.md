---
phase: 40-resolver-system-location-detection-name-resolution
plan: 02
subsystem: service
tags: [name-resolution, resolver, write-pipeline, integration-tests]

requires:
  - phase: 40-01
    provides: "Resolver class with resolve_container, resolve_anchor, resolve_tags methods"
provides:
  - "Name resolution wired into all 5 write fields (parent, beginning, ending, before, after)"
  - "10 integration tests proving end-to-end name resolution through add_task and edit_task"
  - "$inbox system location maps to None in both container move and parent resolution"
affects: [service, domain, write-pipeline]

tech-stack:
  added: []
  patterns: ["resolved ID used in return dicts instead of raw user input (T-40-05, T-40-06)"]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/service.py
    - tests/test_service.py

key-decisions:
  - "$inbox maps to container_id=None at service boundary, not passed through to bridge"
  - "resolve_anchor used for before/after (task-only resolution), resolve_container for parent/beginning/ending"
  - "Resolved IDs replace raw input in all return dicts (mitigates T-40-05, T-40-06)"

patterns-established:
  - "Write pipeline always uses resolved IDs from Resolver, never raw user input"

requirements-completed: [NRES-01, NRES-02, NRES-03]

duration: 6min
completed: 2026-04-05
---

# Phase 40 Plan 02: Write Pipeline Name Resolution Integration Summary

**Name resolution wired into all 5 write fields with 10 integration tests proving end-to-end parent/container/anchor resolution through add_task and edit_task pipelines**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-05T19:04:13Z
- **Completed:** 2026-04-05T19:09:54Z
- **Tasks:** 1
- **Files modified:** 3

## Accomplishments
- `_process_anchor_move` now calls `resolve_anchor` (not `lookup_task`), enabling name-to-ID resolution for before/after fields
- `_process_container_move` uses resolved ID from `resolve_container` in return dict and cycle check (not raw user input)
- `_AddTaskPipeline._resolve_parent` captures resolved parent ID and passes it to payload builder
- `$inbox` system location correctly maps to `None` (inbox) in both container move and parent resolution paths
- 10 integration tests cover: parent by name, parent by substring, $inbox, not-found errors, ending/beginning by name, before/after by name, anchor not-found, ending $inbox

## Task Commits

Each task was committed atomically:

1. **Task 1: Wire resolve_anchor into _process_anchor_move and add integration tests** - `e7b57d8` (feat)

## Files Created/Modified
- `src/omnifocus_operator/service/domain.py` - _process_container_move uses resolved ID; _process_anchor_move uses resolve_anchor; $inbox -> None mapping
- `src/omnifocus_operator/service/service.py` - _resolve_parent captures resolved ID; $inbox -> None mapping; passes resolved parent to payload builder
- `tests/test_service.py` - TestNameResolutionIntegration class with 10 end-to-end tests

## Decisions Made
- `$inbox` maps to `container_id=None` at the service boundary rather than flowing `"$inbox"` string to the bridge. This matches the existing `ending=None` convention for inbox moves and avoids bridge-level handling of system locations.
- The anchor not-found error wraps with `ANCHOR_TASK_NOT_FOUND` message (preserving existing error contract) rather than exposing the raw resolver error.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] _AddTaskPipeline._resolve_parent discarded resolved ID**
- **Found during:** Task 1
- **Issue:** Plan focused on domain.py fixes but _resolve_parent in service.py also discarded the resolve_container return value, passing the raw name string to the payload builder
- **Fix:** Stored resolved ID and used model_copy to substitute into command before build_add
- **Files modified:** src/omnifocus_operator/service/service.py
- **Committed in:** e7b57d8

**2. [Rule 2 - Missing Critical] $inbox system location not mapped to None**
- **Found during:** Task 1
- **Issue:** resolve_container("$inbox") returns "$inbox" string, but InMemoryBridge expects container_id=None for inbox. Without mapping, $inbox would cause bridge errors.
- **Fix:** Added SYSTEM_LOCATION_INBOX check in both _process_container_move and _resolve_parent, mapping to None
- **Files modified:** src/omnifocus_operator/service/domain.py, src/omnifocus_operator/service/service.py
- **Committed in:** e7b57d8

---

**Total deviations:** 2 auto-fixed (1 bug, 1 missing critical)
**Impact on plan:** Both fixes necessary for correctness. The plan mentioned fixing _process_container_move but not _resolve_parent or $inbox mapping. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 write fields (parent, beginning, ending, before, after) accept entity names end-to-end
- Full test suite green (1549 tests, 98.24% coverage)
- Ready for downstream phases that build on name resolution

---
*Phase: 40-resolver-system-location-detection-name-resolution*
*Completed: 2026-04-05*
