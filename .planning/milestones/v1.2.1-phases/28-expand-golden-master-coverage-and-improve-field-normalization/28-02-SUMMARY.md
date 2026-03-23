---
phase: 28-expand-golden-master-coverage-and-improve-field-normalization
plan: 02
subsystem: testing
tags: [golden-master, capture-script, contract-tests, UAT]

# Dependency graph
requires:
  - phase: 27-repository-contract-tests-for-behavioral-equivalence
    provides: golden master capture script, contract test infrastructure, normalize.py
provides:
  - Rewritten capture script with 43 scenarios across 7 numbered categories
  - Subfolder fixture layout (01-add/ through 07-inheritance/)
  - Extended manual setup for 3 projects + 2 tags
  - Anchor-based move scenarios (before/after)
  - Inheritance scenarios (effective fields from parent chain)
  - README documenting new layout and normalization tiers
affects: [28-03, 28-04, golden-master, contract-tests]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Subfolder fixture layout: numbered subfolders encode execution order without manifest"
    - "Followup add_task support: followup operations can be add_task (not just edit_task)"

key-files:
  created: []
  modified:
    - uat/capture_golden_master.py
    - tests/golden_master/README.md

key-decisions:
  - "43 scenarios total (6+11+7+5+4+3+7) matching CONTEXT.md categories closely"
  - "Scenario 02-edit/11 is set-only for plannedDate (clear covered by 08_clear_dates pattern)"
  - "07-inheritance/03 uses followup add_task to create child under parent (not edit_task)"
  - "GM-Cleanup task created in inbox (not under project) per D-07"

patterns-established:
  - "Subfolder fixture routing: scenario dicts carry folder/file keys for _write_fixture"
  - "Followup add_task tracking: _capture_scenario handles add_task followups with ID capture"

requirements-completed: [GOLD-01, GOLD-02]

# Metrics
duration: 4min
completed: 2026-03-22
---

# Phase 28 Plan 02: Capture Script Rewrite Summary

**43-scenario capture script across 7 numbered categories (01-add through 07-inheritance) with subfolder fixture layout, 3-project setup, and anchor/inheritance coverage**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-22T17:56:11Z
- **Completed:** 2026-03-22T18:00:11Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- Rewrote capture script from 20 flat scenarios to 43 scenarios in 7 numbered subfolders
- Extended manual setup to verify 3 projects (GM-TestProject, GM-TestProject2, GM-TestProject-Dated) and 2 tags
- Added anchor-based moves (before/after), inheritance scenarios, and combined operation coverage
- Updated README with subfolder layout, field normalization tiers (VOLATILE/PRESENCE_CHECK/UNCOMPUTED), and extended prerequisites

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite capture script with 43 scenarios in 7 categories** - `d2c9b85` (feat)
2. **Task 2: Update golden master README for subfolder layout** - `a2ff45a` (docs)

## Files Created/Modified
- `uat/capture_golden_master.py` - Rewritten with 43 scenarios, subfolder fixture layout, 3-project setup, inheritance scenarios
- `tests/golden_master/README.md` - Updated to document subfolder structure, normalization tiers, extended prerequisites

## Decisions Made
- 43 total scenarios (slightly above CONTEXT.md's ~41 due to deep nesting having 3 sub-scenarios: 05a, 05b, 05c)
- Scenario 02-edit/11 only sets plannedDate (clear pattern already demonstrated by 08_clear_dates)
- Inheritance scenario 03_flagged_chain uses followup add_task (creates child under parent task) -- extended _capture_scenario to handle add_task followups with ID tracking
- GM-Cleanup task is created in inbox (not under project) for easy discoverability, per D-07

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 2 - Missing Critical] Extended _capture_scenario for add_task followups**
- **Found during:** Task 1 (writing inheritance scenarios)
- **Issue:** Original _capture_scenario only tracked IDs from the primary operation's add_task. Inheritance chain scenarios (03_flagged_chain) use add_task as the followup operation, whose response ID wasn't captured.
- **Fix:** Added ID tracking for followup add_task responses, including capture_id_as support on followup dicts.
- **Files modified:** uat/capture_golden_master.py
- **Verification:** Syntax check passes, flag_chain_child ID is properly captured via followup
- **Committed in:** d2c9b85 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 missing critical)
**Impact on plan:** Essential for inheritance chain scenarios to capture followup task IDs. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Capture script ready for human execution against real OmniFocus
- README documents the expected subfolder layout for contract test discovery
- Plan 03 (contract test infrastructure updates) and Plan 04 (normalization + InMemoryBridge) can proceed

## Self-Check: PASSED

- uat/capture_golden_master.py: FOUND
- tests/golden_master/README.md: FOUND
- 28-02-SUMMARY.md: FOUND
- Commit d2c9b85: FOUND
- Commit a2ff45a: FOUND

---
*Phase: 28-expand-golden-master-coverage-and-improve-field-normalization*
*Completed: 2026-03-22*
