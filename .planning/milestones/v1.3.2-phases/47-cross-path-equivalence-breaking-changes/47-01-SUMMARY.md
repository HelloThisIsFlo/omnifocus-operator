---
phase: 47-cross-path-equivalence-breaking-changes
plan: 01
subsystem: contracts, service, agent-messages
tags: [enum-refactor, descriptions, defer-hints, breaking-changes]
dependency_graph:
  requires: [phase-45-date-models, phase-46-date-filtering]
  provides: [trimmed-availability-enum, remaining-shorthand, defer-hint-detection, d17-descriptions]
  affects: [list_tasks, list_projects, all-test-suites]
tech_stack:
  added: []
  patterns: [REMAINING-expansion, defer-hint-detection, local-import-for-formatter]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/_enums.py
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/projects.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/resolve_dates.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - src/omnifocus_operator/agent_messages/errors.py
    - tests/test_service_domain.py
    - tests/test_list_contracts.py
    - tests/test_date_filter_contracts.py
    - tests/test_list_pipelines.py
    - tests/test_resolve_dates.py
    - tests/test_errors.py
decisions:
  - "REMAINING shorthand follows OmniFocus UI vocabulary for available+blocked"
  - "AVAILABILITY_MIXED_ALL kept for tag/folder filters which still have ALL"
  - "AVAILABILITY_EMPTY kept in errors.py for tag/folder empty-list rejection"
  - "Defer hint detection uses local imports to avoid formatter removing unused top-level imports"
  - "Tags and folders added as error consumer modules for AST enforcement test"
metrics:
  duration: 15m
  completed: 2026-04-08
---

# Phase 47 Plan 01: Enum Trimming, Defer Hints & Description Updates Summary

AvailabilityFilter trimmed to 3 values (AVAILABLE, BLOCKED, REMAINING), LifecycleDateShortcut renamed ANY->ALL, defer hint detection for after/before "now", all 7 per-field descriptions updated to D-17 verbatim text, full suite green (1887 tests, 97.77% coverage).

## What Changed

### Enum Refactoring
- **AvailabilityFilter**: Removed COMPLETED, DROPPED, ALL. Added REMAINING="remaining" (expands to AVAILABLE+BLOCKED at service layer)
- **LifecycleDateShortcut**: Renamed ANY="any" to ALL="all" -- completed/dropped lifecycle state is now solely gated by date filters
- Default availability on ListTasksQuery and ListProjectsQuery changed from [AVAILABLE, BLOCKED] to [REMAINING]
- Empty availability [] now accepted on tasks and projects (validator removed) -- enables "only completed tasks" queries via `availability: [], completed: "all"`

### Expansion Logic Rewrite
- `expand_task_availability` rewritten: REMAINING expands to {AVAILABLE, BLOCKED}, with redundancy warnings for [AVAILABLE, REMAINING] and [BLOCKED, REMAINING]
- `resolve_date_filters` shortcut check updated from `"any"` to `"all"`
- `resolve_dates.py` guard updated from `"any"` to `"all"`

### Defer Hint Detection
- New warning constants: DEFER_AFTER_NOW_HINT, DEFER_BEFORE_NOW_HINT
- Detection in `resolve_date_filters`: when defer field is a DateFilter with after="now" or before="now", educational hint appended to warnings
- Hints are non-blocking -- query still resolves normally

### Description Updates (D-17 Verbatim)
- All 7 per-field date filter descriptions replaced with D-17b text (effective/inherited, semantic guidance)
- LIST_TASKS_TOOL_DOC appended with D-17a text (effective values, lifecycle expansion, availability vs defer)
- LIST_PROJECTS_TOOL_DOC appended with effective-date note
- AVAILABILITY_DOC updated to D-17c text (remaining default, empty list semantics)
- LIFECYCLE_DATE_SHORTCUT_DOC updated to reference "all" instead of "any"

### Test Updates
- 14 test files modified across 4 commits (TDD red/green for each task)
- TestExpandTaskAvailability rewritten: 7 new tests for REMAINING expansion, redundancy warnings, empty list, lifecycle merge
- TestDeferHintDetection: 6 new tests for defer hint detection
- All LifecycleDateShortcut.ANY -> .ALL references updated across test_date_filter_contracts, test_list_pipelines, test_resolve_dates, test_service_domain
- TestEmptyAvailabilityRejection -> TestEmptyAvailabilityAcceptance (tasks/projects accept [])
- test_errors.py: added tags and folders as error consumer modules

## Commits

| # | Hash | Message |
|---|------|---------|
| 1 | 022ef19 | test(47-01): add failing tests for enum trimming and expansion rewrite |
| 2 | 995540e | feat(47-01): trim AvailabilityFilter enum, rename ANY->ALL, rewrite expansion |
| 3 | a542c56 | test(47-01): add failing tests for defer hints and ANY->ALL rename |
| 4 | e36d500 | feat(47-01): add defer hints, update descriptions to D-17 verbatim, fix ANY->ALL |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] AVAILABILITY_MIXED_ALL still needed for tag/folder pipelines**
- **Found during:** Task 1
- **Issue:** Plan said to remove AVAILABILITY_MIXED_ALL from warnings.py, but service.py uses it for tag and folder availability expansion (which still have ALL)
- **Fix:** Kept AVAILABILITY_MIXED_ALL in warnings.py alongside the new REMAINING-specific constants
- **Files modified:** src/omnifocus_operator/agent_messages/warnings.py

**2. [Rule 3 - Blocking] AVAILABILITY_EMPTY still needed for tag/folder validators**
- **Found during:** Task 1
- **Issue:** Plan said to delete AVAILABILITY_EMPTY from errors.py, but tags.py and folders.py still use it for empty-list rejection
- **Fix:** Kept AVAILABILITY_EMPTY in errors.py
- **Files modified:** src/omnifocus_operator/agent_messages/errors.py

**3. [Rule 1 - Bug] AST enforcement test failed: AVAILABILITY_EMPTY unreferenced in consumers**
- **Found during:** Task 2
- **Issue:** test_errors.py AST enforcement test checks all error constants are referenced in consumer modules. tags.py and folders.py (which use AVAILABILITY_EMPTY) were not in the consumer list
- **Fix:** Added contracts_list_tags and contracts_list_folders to _ERROR_CONSUMERS list
- **Files modified:** tests/test_errors.py

**4. [Rule 3 - Blocking] Formatter removes unused top-level imports**
- **Found during:** Task 1 & 2
- **Issue:** Project formatter (isort/ruff) removes imports that appear unused at the point of edit. New warning constants added to top-level import block were stripped
- **Fix:** Used local imports inside methods where constants are first used (expand_task_availability, resolve_date_filters)
- **Files modified:** src/omnifocus_operator/service/domain.py

## Verification

- `uv run pytest -x -q` exits 0: 1887 passed, 97.77% coverage
- AvailabilityFilter has exactly 3 members: AVAILABLE, BLOCKED, REMAINING
- LifecycleDateShortcut uses ALL="all" (not ANY)
- Empty availability [] accepted on both query models
- REMAINING expansion produces correct availability sets and redundancy warnings
- Defer {after/before: "now"} hints flow through ListResult.warnings
- All 7 per-field descriptions match D-17b verbatim
- LIST_TASKS_TOOL_DOC and LIST_PROJECTS_TOOL_DOC include effective-date notes
- No LifecycleDateShortcut.ANY references remain in any test file

## Self-Check: PASSED

All 14 modified files verified present. All 4 commit hashes verified in git log.
