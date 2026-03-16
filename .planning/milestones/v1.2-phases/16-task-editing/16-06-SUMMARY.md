---
phase: 16-task-editing
plan: 06
subsystem: api
tags: [validation, error-messages, timezone, no-op-detection, warnings]

requires:
  - phase: 16-task-editing
    provides: "edit_tasks implementation with tag/move/no-op logic"
provides:
  - "Filtered _Unset from ValidationError messages"
  - "UTC-normalized date comparison for timezone-aware no-op detection"
  - "Improved tag warning messages with resolved IDs"
  - "Same-container move detection with advisory warning"
affects: []

tech-stack:
  added: []
  patterns:
    - "_to_utc_ts helper for timezone-normalized datetime comparison"
    - "Same-container move detection via parent.id comparison"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/server.py"
    - "src/omnifocus_operator/service.py"
    - "tests/test_server.py"
    - "tests/test_service.py"

key-decisions:
  - "UTC timestamp comparison (float) for date no-op detection instead of ISO string comparison"
  - "Same-container move detection only for beginning/ending positions (before/after lack sibling data)"

patterns-established:
  - "_to_utc_ts: normalize datetime/string/None to UTC float timestamp for comparison"

requirements-completed: [EDIT-01, EDIT-02, EDIT-03, EDIT-04, EDIT-05, EDIT-06, EDIT-07, EDIT-08, EDIT-09]

duration: 3min
completed: 2026-03-09
---

# Phase 16 Plan 06: UAT Gap Closure Summary

**Fix 5 UAT minor issues: _Unset filtering, timezone no-op, tag ID in warnings, same-container move detection**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-09T18:29:41Z
- **Completed:** 2026-03-09T18:33:27Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Filtered _Unset Pydantic internals from ValidationError messages in both add/edit catch blocks
- UTC-normalized date comparison prevents false changes when same time given in different timezone
- Tag warnings now include resolved ID in parentheses and use present tense
- Same-container move (beginning/ending) produces advisory "already in this location" warning
- 3 new tests + 4 updated test assertions covering all 5 UAT gaps

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix ValidationError filtering and tag/move warning messages** - `e2c2504` (fix)
2. **Task 2: Update and add tests for all 5 UAT fixes** - `1ebdf26` (test)

## Files Created/Modified
- `src/omnifocus_operator/server.py` - Filtered _Unset from ValidationError join in both catch blocks
- `src/omnifocus_operator/service.py` - UTC date comparison, tag ID in warnings, same-container move detection
- `tests/test_server.py` - Added _Unset assertion to moveTo multi-key error test
- `tests/test_service.py` - Updated 4 tag warning assertions, added 3 new tests (timezone, same-container, different-container)

## Decisions Made
- UTC timestamp (float) comparison chosen over ISO string normalization -- handles all timezone offsets correctly with minimal code
- Same-container detection limited to beginning/ending positions -- before/after requires sibling order data we don't have

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 16 gap closure complete with all UAT issues resolved
- Ready for phase 17

---
*Phase: 16-task-editing*
*Completed: 2026-03-09*
