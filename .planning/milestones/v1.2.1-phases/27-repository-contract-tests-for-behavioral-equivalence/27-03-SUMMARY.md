---
phase: 27-repository-contract-tests-for-behavioral-equivalence
plan: 03
subsystem: testing
tags: [bridge, adapter, raw-format, InMemoryBridge, contract-tests]

# Dependency graph
requires:
  - phase: 27-01
    provides: golden master contract tests infrastructure
  - phase: 27-02
    provides: verification results identifying raw format gap
provides:
  - InMemoryBridge._handle_get_all returns raw bridge format (matching RealBridge)
  - adapt_snapshot actually processes InMemoryBridge output (no more silent no-op)
  - Reverse status/repetition maps for model-to-raw conversion
  - Pre-computed containing-project map avoiding iteration-order bugs
affects: [27-04, contract-tests, golden-master]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Model-to-raw reverse conversion with pre-computed parent chain walk"
    - "Graceful degradation in _to_raw_format for invalid data types"

key-files:
  created: []
  modified:
    - tests/doubles/bridge.py
    - tests/test_stateful_bridge.py
    - tests/test_service.py

key-decisions:
  - "Pre-compute containing_project_map before task conversion to avoid iteration-order bug"
  - "test_move_to_project_ending asserts parent.type=='task' matching golden master scenario_16"

patterns-established:
  - "Raw format output from InMemoryBridge: internal model-format storage, raw bridge-format output via _handle_get_all"

requirements-completed: [INFRA-13, INFRA-14]

# Metrics
duration: 6min
completed: 2026-03-22
---

# Phase 27 Plan 03: Raw Bridge Format Conversion Summary

**InMemoryBridge._handle_get_all returns raw bridge format with reverse status maps, parent chain walk for containing-project reconstruction, and adapter round-trip verification**

## Performance

- **Duration:** 6 min
- **Started:** 2026-03-22T09:54:41Z
- **Completed:** 2026-03-22T10:01:13Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments

- InMemoryBridge._handle_get_all now returns raw bridge format (status strings, parent/project as string IDs) matching RealBridge output
- adapt_snapshot actually processes InMemoryBridge data (no more silent no-op from missing "status" key)
- All 4 containing-project cases handled: inbox, direct project child, sub-task in project, sub-task in inbox
- test_move_to_project_ending fixed to assert parent.type=="task" matching golden master scenario_16
- 648 tests pass (contract tests deferred to Plan 27-04 for raw format alignment)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add raw format conversion to InMemoryBridge._handle_get_all** - `a3ce01a` (feat)
2. **Task 2: Update tests for raw format output + fix service regression** - `f4b2a8c` (fix)

## Files Created/Modified

- `tests/doubles/bridge.py` - Added reverse status maps, _to_raw_format method with containing-project pre-computation, repetition rule reversal, graceful invalid-data handling
- `tests/test_stateful_bridge.py` - Updated test_get_all_parseable_by_all_entities to apply adapt_snapshot before validation
- `tests/test_service.py` - Fixed test_move_to_project_ending assertion from type=="project" to type=="task"

## Decisions Made

- **Pre-compute containing_project_map:** Walk parent chains while dicts are still intact, before in-place conversion to strings. Avoids iteration-order bug where converting parent A before child B breaks B's chain walk.
- **parent.type=="task" for project parents:** Golden master scenario_16 confirms OmniFocus sets both `parent` and `project` to the project ID. The adapter's `_adapt_parent_ref` sees `parent` is not None and produces type="task". This is correct real-world behavior.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added reverse repetition rule maps**
- **Found during:** Task 2 (running full test suite)
- **Issue:** Tests seeding tasks with model-format repetitionRule (snake_case `"regularly"`, `"due_date"`) caused adapter to fail with "Unknown scheduleType: 'regularly'" after raw conversion
- **Fix:** Added `_REVERSE_SCHEDULE_TYPE` and `_REVERSE_ANCHOR_DATE_KEY` maps, called from `_task_to_raw` and `_project_to_raw` via shared `_repetition_rule_to_raw` method
- **Files modified:** tests/doubles/bridge.py
- **Verification:** All 3 repetition-related tests pass
- **Committed in:** f4b2a8c (Task 2 commit)

**2. [Rule 1 - Bug] Guard _to_raw_format against invalid data types**
- **Found during:** Task 2 (running full test suite)
- **Issue:** test_validation_error_propagates passes `{"tasks": "not-a-list"}` causing TypeError in _to_raw_format before Pydantic could report the real validation error
- **Fix:** Added isinstance guards at the top of _to_raw_format to skip conversion for non-list/non-dict data
- **Files modified:** tests/doubles/bridge.py
- **Verification:** test_validation_error_propagates passes (Pydantic ValidationError propagated correctly)
- **Committed in:** f4b2a8c (Task 2 commit)

---

**Total deviations:** 2 auto-fixed (1 blocking, 1 bug)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered

None beyond the auto-fixed deviations.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- InMemoryBridge now returns raw format matching RealBridge, enabling Plan 27-04 to update contract tests for raw format comparison
- Contract tests (test_bridge_contract.py) currently fail because they compare against model-format golden master expectations -- Plan 27-04 will re-capture golden masters in raw format

---
## Self-Check: PASSED

- All 3 modified files exist on disk
- Both task commits (a3ce01a, f4b2a8c) found in git log

---
*Phase: 27-repository-contract-tests-for-behavioral-equivalence*
*Completed: 2026-03-22*
