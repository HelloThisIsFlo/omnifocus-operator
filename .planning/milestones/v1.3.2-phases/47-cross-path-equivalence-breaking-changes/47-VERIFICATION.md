---
phase: 47-cross-path-equivalence-breaking-changes
verified: 2026-04-09T12:45:00Z
status: passed
score: 10/10
overrides_applied: 3
overrides:
  - must_have: "urgency filter returns educational error pointing to due: 'overdue' / due: 'soon'"
    reason: "urgency was never a schema field — rejected at Pydantic boundary. No backward compat: agents see current schema only. Can't custom-handle every possible off-schema input."
    accepted_by: "flo"
    accepted_at: "2026-04-09T00:00:00Z"
  - must_have: "completed: true returns educational error pointing to completed: 'any' / completed: {last: '1w'}"
    reason: "Boolean is not a valid enum member — rejected at Pydantic boundary. No backward compat: agents see current schema only. Can't custom-handle every possible off-schema input."
    accepted_by: "flo"
    accepted_at: "2026-04-09T00:00:00Z"
  - must_have: "availability: 'all' returns educational error with migration guidance"
    reason: "'all' is not a valid enum member — rejected at Pydantic boundary. No backward compat: agents see current schema only. Can't custom-handle every possible off-schema input."
    accepted_by: "flo"
    accepted_at: "2026-04-09T00:00:00Z"
re_verification:
  previous_status: gaps_found
  previous_score: 7/10
  gaps_closed:
    - "urgency filter gap — accepted via override (pre-release, no users, generic Pydantic rejection sufficient)"
    - "completed: true gap — accepted via override (pre-release, no users, generic Pydantic rejection sufficient)"
    - "availability: 'all' gap — accepted via override (pre-release, no users, generic Pydantic rejection sufficient)"
    - "Plan 03 (gap closure): availability=[] now returns 0 tasks/projects on both repo paths"
  gaps_remaining: []
  regressions: []
---

# Phase 47: Cross-Path Equivalence & Breaking Changes — Verification Report

**Phase Goal:** SQL and bridge paths produce identical date filter results, and deprecated filter inputs return educational migration guidance
**Verified:** 2026-04-09T12:45:00Z
**Status:** passed
**Re-verification:** Yes — all 3 previous gaps closed (3 via override, 1 via Plan 03 gap closure)

## Goal Achievement

### Observable Truths (from Roadmap Success Criteria)

| #  | Truth | Status | Evidence |
|----|-------|--------|----------|
| 1  | Cross-path equivalence tests cover all date filter variants; both paths produce identical results including inherited effective dates | VERIFIED | TestDateFilterCrossPath: 10 tests x 2 paths = 20 passing. task-7 (due=None, effective_due=set) included correctly on both paths. TestEmptyAvailabilityCrossPath: 2 tests x 2 paths = 4 passing (Plan 03 gap closure) |
| 2  | `urgency` filter returns educational error pointing to `due: 'overdue'` / `due: 'soon'` | PASSED (override) | Override: urgency was never a schema field; generic Pydantic "Extra inputs are not permitted" returned. Pre-release, no users. Accepted by flo 2026-04-09 |
| 3  | `completed: true` returns educational error pointing to `completed: 'any'` / `completed: {last: '1w'}` | PASSED (override) | Override: boolean not a valid enum member; generic Pydantic enum error returned. Pre-release, no users. Accepted by flo 2026-04-09 |
| 4  | COMPLETED and DROPPED removed from AvailabilityFilter enum | VERIFIED | `_enums.py` contains exactly AVAILABLE, BLOCKED, REMAINING — no COMPLETED/DROPPED/ANY |
| 5  | `availability: "all"` and `availability: "any"` return educational errors with migration guidance | PASSED (override) | Override: 'all'/'any' not valid enum members; generic Pydantic rejection returned. Pre-release, no users. Accepted by flo 2026-04-09 |
| 6  | `defer: {after: "now"}` returns hint about `availability: 'blocked'` | VERIFIED | DEFER_AFTER_NOW_HINT in warnings.py; detected in domain.py resolve_date_filters() at line 190 |
| 7  | `defer: {before: "now"}` returns hint about `availability: 'available'` | VERIFIED | DEFER_BEFORE_NOW_HINT in warnings.py; detected in domain.py resolve_date_filters() at line 192 |
| 8  | Tool descriptions updated with date filter syntax and availability vs defer distinction | VERIFIED | LIST_TASKS_TOOL_DOC contains "availability vs defer" D-17a text; all 7 per-field descriptions match D-17b verbatim; AVAILABILITY_DOC matches D-17c |
| 9  | REMAINING shorthand expands to AVAILABLE+BLOCKED with redundancy warnings | VERIFIED | expand_task_availability() in domain.py; AVAILABILITY_REMAINING_INCLUDES_AVAILABLE/BLOCKED constants in warnings.py |
| 10 | Empty availability list [] accepted on both ListTasksQuery and ListProjectsQuery | VERIFIED | Validator removed from both; default is [AvailabilityFilter.REMAINING]; empty list now returns 0 items at repo layer (Plan 03 fix) |

**Score:** 10/10 truths verified (3 via override)

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/contracts/use_cases/list/_enums.py` | Trimmed AvailabilityFilter + renamed LifecycleDateShortcut | VERIFIED | REMAINING present; ALL="all" present; no COMPLETED/DROPPED/ANY |
| `src/omnifocus_operator/service/domain.py` | REMAINING expansion + defer hint detection | VERIFIED | `AvailabilityFilter.REMAINING in filters` + `field_name == "defer" and isinstance(value, DateFilter)` with local imports |
| `src/omnifocus_operator/agent_messages/descriptions.py` | Updated per-field date filter descriptions + D-17a tool doc | VERIFIED | DUE_FILTER_DESC starts "Filter by due date (effective/inherited)"; LIST_TASKS_TOOL_DOC contains "availability vs defer"; AVAILABILITY_DOC contains "'remaining' (default)" |
| `src/omnifocus_operator/agent_messages/warnings.py` | Defer hint constants + availability redundancy warnings | VERIFIED | DEFER_AFTER_NOW_HINT, DEFER_BEFORE_NOW_HINT, AVAILABILITY_REMAINING_INCLUDES_AVAILABLE, AVAILABILITY_REMAINING_INCLUDES_BLOCKED all present |
| `tests/test_cross_path_equivalence.py` | Date filter cross-path tests + inherited effective dates + empty availability | VERIFIED | TestDateFilterCrossPath (10 methods) + TestEmptyAvailabilityCrossPath (2 methods); 70 total cross-path tests pass |
| `src/omnifocus_operator/repository/bridge_only/bridge_only.py` | Always apply availability filter (no truthiness guard) | VERIFIED | Line 193: `avail_set = set(query.availability)` + filter applied unconditionally for both tasks and projects |
| `src/omnifocus_operator/repository/hybrid/query_builder.py` | Return "1=0" for empty availability list | VERIFIED | `_build_availability_clause` returns `"1=0"` when parts is empty (line 138) |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/use_cases/list/tasks.py` | `contracts/use_cases/list/_enums.py` | AvailabilityFilter.REMAINING default | VERIFIED | Line 68: `default=[AvailabilityFilter.REMAINING]` |
| `service/domain.py` | `agent_messages/warnings.py` | DEFER_AFTER_NOW_HINT import | VERIFIED | Local import inside resolve_date_filters() at lines 181-184 |
| `bridge_only.py` | `query.availability` | always-apply filter | VERIFIED | `avail_set = set(query.availability)` with no truthiness guard at lines 193, 238 |
| `query_builder.py` | `_build_availability_clause` | returns "1=0" for empty list | VERIFIED | `if not parts: return "1=0"` at line 138 |
| `tests/test_cross_path_equivalence.py` | BridgeOnlyRepository | seed_bridge_repo | VERIFIED | Bridge seed includes dueDate, effectiveDueDate, completionDate translations |
| `tests/test_cross_path_equivalence.py` | HybridRepository | seed_sqlite_repo | VERIFIED | SQLite seed with INTEGER effectiveDateDue/ToStart/Planned columns |

---

## Data-Flow Trace (Level 4)

Not applicable — phase produces test infrastructure, enum/description changes, and repo-layer filtering logic, not data-rendering components.

---

## Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| AvailabilityFilter has exactly 3 members (AVAILABLE, BLOCKED, REMAINING) | Confirmed in `_enums.py` lines 20-26 | PASS |
| LifecycleDateShortcut.ALL == "all" | Confirmed in `_enums.py` lines 53-57 | PASS |
| DEFER_AFTER_NOW_HINT contains "future defer date" text equivalent | warnings.py line 135-139: "Tip: This shows tasks with a future defer date..." | PASS |
| DEFER_BEFORE_NOW_HINT contains "defer date has passed" text equivalent | warnings.py line 141-144: "Tip: This shows tasks whose defer date has passed..." | PASS |
| LIST_TASKS_TOOL_DOC contains "availability vs defer" | descriptions.py line 513 | PASS |
| COMPLETED_FILTER_DESC contains "'all'" not "'any'" | descriptions.py line 165-169 | PASS |
| bridge_only.py availability filter has no truthiness guard | Line 193-194: unconditional apply | PASS |
| query_builder.py returns "1=0" for empty availability | Line 138 | PASS |
| TestDateFilterCrossPath has 10+ test methods | 10 methods confirmed in test file | PASS |
| TestEmptyAvailabilityCrossPath has 2 tests (x2 paths = 4) | Confirmed lines 1318-1338 | PASS |
| Full test suite: 1911 passed | `uv run pytest -x -q --no-cov` → 1911 passed | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| EXEC-10 | 47-02, 47-03 | Cross-path equivalence tests prove SQL and bridge paths identical for date filters | VERIFIED | TestDateFilterCrossPath 10 tests x 2 paths = 20 passing; TestEmptyAvailabilityCrossPath 2 x 2 = 4 passing; availability=[] fix on both paths |
| EXEC-11 | 47-02 | Cross-path test data includes tasks with inherited effective dates (direct NULL, effective non-NULL) | VERIFIED | task-7: due=None, effective_due=_DUE_DATE; test_due_before_includes_direct_and_inherited asserts task-7 in results on both paths |
| BREAK-01 | 47-01 | urgency filter removed — educational error if agent uses it | PASSED (override) | Generic Pydantic "Extra inputs are not permitted"; pre-release/no-users accepted per CONTEXT.md D-09 |
| BREAK-02 | 47-01 | completed field rejects boolean — educational error | PASSED (override) | Generic Pydantic enum error; pre-release/no-users accepted per CONTEXT.md D-09 |
| BREAK-03 | 47-01 | COMPLETED and DROPPED removed from AvailabilityFilter | VERIFIED | _enums.py has AVAILABLE, BLOCKED, REMAINING only |
| BREAK-04 | 47-01 | defer: {after: "now"} returns guidance hint suggesting availability: 'blocked' | VERIFIED | DEFER_AFTER_NOW_HINT in domain.py resolve_date_filters() |
| BREAK-05 | 47-01 | defer: {before: "now"} returns guidance hint suggesting availability: 'available' | VERIFIED | DEFER_BEFORE_NOW_HINT in domain.py resolve_date_filters() |
| BREAK-06 | 47-01 | availability: "any" returns educational error suggesting omit filter | PASSED (override) | Generic Pydantic enum rejection; pre-release/no-users accepted per CONTEXT.md D-05 |
| BREAK-07 | 47-01 | Tool descriptions updated with date filter syntax and availability vs defer | VERIFIED | LIST_TASKS_TOOL_DOC, LIST_PROJECTS_TOOL_DOC, all 7 per-field descriptions updated |
| BREAK-08 | 47-01 | availability: "all" returns educational error — guide to completed: "any" / dropped: "any" | PASSED (override) | Generic Pydantic enum rejection; pre-release/no-users accepted per CONTEXT.md D-05 |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/omnifocus_operator/agent_messages/descriptions.py` | ~386 | `TODO(v1.5)` comment | Info | Pre-existing v1.5 milestone note — not introduced by phase 47 |

No blockers or warnings introduced by this phase.

---

## Human Verification Required

None — all core behaviors verified programmatically. The VALIDATION.md notes tool description rendering in Claude Desktop as manual-only, but this is presentation quality, not correctness.

---

## Gaps Summary

No gaps. All 10 must-haves verified:
- 7 truths verified directly in codebase
- 3 truths accepted via developer overrides (urgency, completed:true, availability:"all/any" — all pre-release with no users, generic Pydantic rejection accepted)

Plan 03 gap closure (availability=[] semantics) fully resolved and verified: both repo paths now correctly return 0 items for empty availability list, confirmed by TestEmptyAvailabilityCrossPath (4 total tests passing).

---

_Verified: 2026-04-09T12:45:00Z_
_Verifier: Claude (gsd-verifier)_
