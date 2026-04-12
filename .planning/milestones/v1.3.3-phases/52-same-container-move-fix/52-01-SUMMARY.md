---
phase: 52-same-container-move-fix
plan: 01
subsystem: service
tags: [move, translation, repository, protocol, sqlite, domain-logic]

# Dependency graph
requires:
  - phase: 51-task-ordering
    provides: "Rank-based CTE ordering, inbox anchor SQL condition"
provides:
  - "get_edge_child_id method on Repository protocol and both implementations"
  - "_process_container_move translation logic (beginning/ending -> before/after)"
  - "No-op detection via anchor_id == task_id for translated moves"
affects: [52-02-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Edge child lookup via SQL ORDER BY rank ASC/DESC LIMIT 1"
    - "Translation pattern: resolve container -> lookup edge child -> translate if present"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/protocols.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - tests/test_service_domain.py
    - tests/test_service.py

key-decisions:
  - "Always translate beginning/ending when container has children (D-06) -- no same-vs-different branching"
  - "Inbox uses SYSTEM_LOCATIONS['inbox'].id as effective_parent_id for get_edge_child_id"
  - "MOVE_SAME_CONTAINER warning removed entirely (D-14) -- this release fixes the limitation it warned about"
  - "No-op detection catches anchor_id == task_id (D-12, D-13) instead of container membership"

patterns-established:
  - "Edge child lookup: SQL rank-based for hybrid, snapshot positional for bridge-only"
  - "Move translation in domain.py per architecture litmus test (product decision, not plumbing)"

requirements-completed: [MOVE-01, MOVE-02, MOVE-03, MOVE-04, MOVE-05, WARN-02, WARN-03]

# Metrics
duration: 10min
completed: 2026-04-12
---

# Phase 52 Plan 01: Repository Edge Child Lookup + Move Translation Summary

**get_edge_child_id on both repo implementations, _process_container_move translates beginning/ending to before/after when container has children, no-op detection via anchor_id == task_id**

## Performance

- **Duration:** 10 min
- **Started:** 2026-04-12T16:03:17Z
- **Completed:** 2026-04-12T16:13:45Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments

- Repository protocol extended with `get_edge_child_id(parent_id, edge)` -- returns first/last child ID
- Hybrid implementation: SQL `ORDER BY rank ASC/DESC LIMIT 1` with inbox condition from Phase 51 CTE
- Bridge-only implementation: filters cached snapshot for direct children by position
- `_process_container_move` translates beginning/ending to before/after when edge child exists
- No-op detection updated: `anchor_id == task_id` catches self-reference for translated moves
- `MOVE_SAME_CONTAINER` warning removed -- the fix it promised is now implemented

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get_edge_child_id to Repository protocol and both implementations** - `9e03780c` (feat)
2. **Task 2 RED: Add failing tests for move translation** - `d6bedd3c` (test)
3. **Task 2 GREEN: Add translation logic to _process_container_move** - `b3feb9c7` (feat)

## Files Created/Modified

- `src/omnifocus_operator/contracts/protocols.py` - Added `get_edge_child_id` to Repository protocol
- `src/omnifocus_operator/repository/hybrid/hybrid.py` - SQL-based edge child lookup with rank ordering
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` - Snapshot-based edge child lookup
- `src/omnifocus_operator/service/domain.py` - Translation logic in `_process_container_move`, updated no-op detection
- `src/omnifocus_operator/agent_messages/warnings.py` - Removed `MOVE_SAME_CONTAINER` constant
- `tests/test_service_domain.py` - 6 new translation tests, StubRepo with `edge_children` dict
- `tests/test_service.py` - Updated same-container move tests to match new translation behavior

## Decisions Made

- Always translate when children exist (D-06) -- no branching on same-vs-different container
- Inbox uses `SYSTEM_LOCATIONS["inbox"].id` as `effective_parent_id` for `get_edge_child_id` (D-02, D-05)
- `MOVE_SAME_CONTAINER` removed entirely (D-14) -- this release fixes the OmniFocus API limitation
- No-op detection via `anchor_id == task_id` (D-12, D-13) replaces container membership comparison
- `Literal["first", "last"]` type annotation on `edge` variable for mypy strict compliance

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated _all_fields_match no-op detection for translated moves**
- **Found during:** Task 2 (translation logic)
- **Issue:** After translation, `_all_fields_match` hit the old `before/after -- can't detect same position` branch and returned `False`, causing the bridge to receive a no-op move
- **Fix:** Added `anchor_id == task_id` check for before/after moves; removed `MOVE_SAME_CONTAINER` warning append from beginning/ending path
- **Files modified:** `src/omnifocus_operator/service/domain.py`
- **Verification:** `test_same_container_move_noop_detected` passes
- **Committed in:** `b3feb9c7` (Task 2 commit)

**2. [Rule 1 - Bug] Removed MOVE_SAME_CONTAINER from warnings.py**
- **Found during:** Task 2 (translation logic)
- **Issue:** AST enforcement test `test_all_warning_constants_referenced_in_consumers` failed because `MOVE_SAME_CONTAINER` was no longer imported anywhere
- **Fix:** Removed the constant entirely per D-14
- **Files modified:** `src/omnifocus_operator/agent_messages/warnings.py`
- **Verification:** `test_all_warning_constants_referenced_in_consumers` passes
- **Committed in:** `b3feb9c7` (Task 2 commit)

**3. [Rule 1 - Bug] Updated service integration tests for new move behavior**
- **Found during:** Task 2 (translation logic)
- **Issue:** `test_same_container_move_warning` and `test_noop_same_container_move_no_spurious_noop_warning` expected old `MOVE_SAME_CONTAINER` warning text
- **Fix:** Updated tests to expect `EDIT_NO_CHANGES_DETECTED` warning for translated self-reference moves
- **Files modified:** `tests/test_service.py`
- **Verification:** All 167 service tests pass
- **Committed in:** `b3feb9c7` (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 bugs caused by behavior change)
**Impact on plan:** All auto-fixes are direct consequences of the translation feature. The no-op detection and warning cleanup were logically required by the translation -- Plan 02 would have redundantly addressed them. No scope creep.

## Issues Encountered

None

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- Repository `get_edge_child_id` method ready for Plan 02 (warning messages, no-op detection refinement)
- Translation logic complete and tested
- Plan 02 can add position-specific warning messages (`MOVE_ALREADY_AT_POSITION`) for the self-reference case

## Self-Check: PASSED

All 7 modified files verified present. All 3 commit hashes verified in git log.

---
*Phase: 52-same-container-move-fix*
*Completed: 2026-04-12*
