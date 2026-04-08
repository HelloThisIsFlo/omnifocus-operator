---
phase: 47-cross-path-equivalence-breaking-changes
plan: 02
subsystem: tests, cross-path-equivalence
tags: [date-filters, cross-path, inherited-dates, TDD]
dependency_graph:
  requires: [47-01]
  provides: [date-filter-cross-path-proof, inherited-effective-date-coverage]
  affects: [tests/test_cross_path_equivalence.py]
tech_stack:
  added: []
  patterns: [neutral-date-fields, integer-effective-dates, inherited-effective-date-testing]
key_files:
  created: []
  modified:
    - tests/test_cross_path_equivalence.py
decisions:
  - "datePlanned stored as TEXT (naive ISO) not REAL -- matches actual OmniFocus SQLite format"
  - "effectiveDateDue/ToStart/Planned schema corrected from TEXT to INTEGER -- matches FINDINGS.md column type map"
  - "effectiveDatePlanned stored as INTEGER (truncated CF epoch) not REAL -- consistent with other effective date columns"
metrics:
  duration: 9m
  completed: 2026-04-09
---

# Phase 47 Plan 02: Date Filter Cross-Path Equivalence Tests Summary

10 parametrized cross-path tests (20 total across bridge/sqlite) proving SQL and bridge paths produce identical date filter results, including inherited effective dates from parent projects.

## What Changed

### Test Data Expansion (Task 1)
- Added 5 date filter reference datetimes: `_DUE_DATE`, `_DEFER_DATE`, `_PLANNED_DATE`, `_COMPLETED_DATE`, `_DROPPED_DATE`
- Added 10 date fields (direct + effective) to all 4 existing tasks and 3 existing projects
- Added 3 new tasks: task-5 (completed), task-6 (dropped), task-7 (inherited due from proj-due)
- Added proj-due project for inheritance testing (D-16): has due date that propagates to task-7
- Updated bridge seed adapter with all 10 date field translations per task/project
- Updated SQLite seed adapter with correct column types and date column inserts
- Updated existing test assertions for expanded data (5 available tasks, 4 projects)

### Date Filter Tests (Task 2 -- TDD)
- Added `TestDateFilterCrossPath` class with 10 test methods covering all 7 date field families
- **Inherited effective date proof**: task-7 has `due=None, effective_due=_DUE_DATE` -- included by due_before filter on both paths
- **Lifecycle inclusion**: completed/dropped date filters with explicit availability include lifecycle tasks on both paths
- **Combined filters**: due + flagged produces identical AND-combined results
- **Null exclusion**: tasks with NULL date fields excluded from date filter results on both paths
- **Boundary tests**: exact match (due_after=_DUE_DATE), beyond range (due_after=_DUE_DATE+1d)

### Schema Correction
- Fixed SQLite schema: `effectiveDateDue`, `effectiveDateToStart`, `effectiveDatePlanned` declared as INTEGER (was TEXT/REAL)
- Fixed `datePlanned` declared as TEXT (was REAL) to match actual OmniFocus SQLite format per FINDINGS.md

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 444b144 | feat(47-02): extend cross-path test data with date fields and inherited effective dates |
| 2 | dbf7598 | test(47-02): add date filter cross-path equivalence tests |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] datePlanned column type incorrect in plan**
- **Found during:** Task 1
- **Issue:** Plan specified datePlanned as REAL CF epoch, but FINDINGS.md shows it's TEXT (naive ISO), same as dateDue and dateToStart
- **Fix:** Used TEXT format with naive ISO string for datePlanned in both task and project SQLite inserts
- **Files modified:** tests/test_cross_path_equivalence.py

**2. [Rule 1 - Bug] effectiveDatePlanned type incorrect in plan**
- **Found during:** Task 2
- **Issue:** Plan specified effectiveDatePlanned as REAL CF epoch, but FINDINGS.md shows it's INTEGER (truncated), same as effectiveDateDue and effectiveDateToStart
- **Fix:** Used `int(_to_cf_epoch(...))` for effectiveDatePlanned, consistent with other effective date columns
- **Files modified:** tests/test_cross_path_equivalence.py

**3. [Rule 1 - Bug] SQLite schema declared effectiveDateDue/ToStart as TEXT**
- **Found during:** Task 2 (test_due_after_exact_match failed on sqlite path)
- **Issue:** Existing CREATE TABLE schema had `effectiveDateDue TEXT, effectiveDateToStart TEXT` causing text vs numeric comparison failures. FINDINGS.md confirms these are INTEGER columns
- **Fix:** Changed schema to `effectiveDateDue INTEGER, effectiveDateToStart INTEGER, effectiveDatePlanned INTEGER`
- **Files modified:** tests/test_cross_path_equivalence.py

## Verification

- `uv run pytest tests/test_cross_path_equivalence.py -x -q` exits 0: 66 passed
- `uv run pytest tests/test_cross_path_equivalence.py -x -q -k "DateFilter"` exits 0: 20 passed (10 tests x 2 paths)
- `uv run pytest -x -q` exits 0: 1907 passed, 97.77% coverage
- `grep "TestDateFilterCrossPath" tests/test_cross_path_equivalence.py` returns 1 match
- `grep "effective_due.*_DUE_DATE" tests/test_cross_path_equivalence.py` returns 4 matches (inherited date coverage)

## Self-Check: PASSED

All files verified present. All 2 commit hashes verified in git log.
