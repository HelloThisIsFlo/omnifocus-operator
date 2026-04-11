---
phase: 47-cross-path-equivalence-breaking-changes
plan: 04
subsystem: database
tags: [sqlite, plistlib, omnifocus, due-soon]

# Dependency graph
requires:
  - phase: 46-date-filtering-wiring
    provides: "DueSoonSetting enum and _read_due_soon_setting_sync method"
provides:
  - "Fixed _read_due_soon_setting_sync using real OmniFocus Setting table schema (persistentIdentifier + plist-encoded valueData)"
  - "Test infrastructure uses real schema columns and plist encoding"
affects: [47-cross-path-equivalence-breaking-changes]

# Tech tracking
tech-stack:
  added: []
  patterns: ["plist blob decoding for OmniFocus SQLite Setting table"]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - tests/test_due_soon_setting.py

key-decisions:
  - "No new decisions -- followed spike research schema exactly"

patterns-established:
  - "OmniFocus Setting table uses persistentIdentifier/valueData (plist BLOB), not key/value (text)"

requirements-completed: [EXEC-10]

# Metrics
duration: 2min
completed: 2026-04-09
---

# Phase 47 Plan 04: Fix DueSoon Setting SQL Summary

**Fixed "soon" shortcut SQL crash by correcting Setting table query to use real OmniFocus schema (persistentIdentifier + plist-encoded valueData)**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-09T13:57:42Z
- **Completed:** 2026-04-09T14:00:01Z
- **Tasks:** 1
- **Files modified:** 2

## Accomplishments
- Fixed _read_due_soon_setting_sync SQL query: `key`/`value` columns replaced with `persistentIdentifier`/`valueData`
- Added plistlib.loads() decoding for blob values instead of plain text parsing
- Updated test infrastructure to match real OmniFocus SQLite Setting table schema
- All 1911 tests pass, including all 20 DueSoonSetting tests

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1 RED: Update test schema** - `8c92274` (test)
2. **Task 1 GREEN: Fix production code** - `07b0503` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/hybrid/hybrid.py` - Fixed _read_due_soon_setting_sync to use persistentIdentifier/valueData columns with plistlib decoding
- `tests/test_due_soon_setting.py` - Updated fixture schema, helper function, and partial-insert test to use real OmniFocus columns with plist-encoded blobs

## Decisions Made
None - followed plan as specified. Schema details confirmed by spike research.

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- "soon" shortcut no longer crashes on real OmniFocus database
- UAT test 2 and 15 regression resolved
- Ready for plans 05 and 06 to address remaining UAT gaps

---
*Phase: 47-cross-path-equivalence-breaking-changes*
*Completed: 2026-04-09*
