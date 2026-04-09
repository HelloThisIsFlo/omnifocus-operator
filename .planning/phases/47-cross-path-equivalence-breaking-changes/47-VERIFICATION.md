---
phase: 47-cross-path-equivalence-breaking-changes
verified: 2026-04-08T23:16:03Z
status: gaps_found
score: 7/10
gaps:
  - truth: "urgency filter returns educational error pointing to due: 'overdue' / due: 'soon'"
    status: failed
    reason: "urgency field never existed as a query parameter; extra='forbid' produces generic Pydantic error rather than educational migration guidance. CONTEXT.md D-09 and discussion log explicitly chose no interception."
    artifacts:
      - path: "src/omnifocus_operator/contracts/use_cases/list/tasks.py"
        issue: "No custom educational message for urgency — generic 'Extra inputs are not permitted' error"
    missing:
      - "Custom educational error guiding agent to use due: 'overdue' or due: 'soon'"
  - truth: "completed: true returns educational error pointing to completed: 'any' / completed: {last: '1w'}"
    status: failed
    reason: "completed boolean was never accepted; generic Pydantic enum error returned rather than educational migration guidance. CONTEXT.md D-09 explicitly chose no interception."
    artifacts:
      - path: "src/omnifocus_operator/contracts/use_cases/list/tasks.py"
        issue: "No custom educational message for completed=True — generic enum validation error"
    missing:
      - "Custom educational error guiding agent to use completed: 'all' or completed: {last: '1w'}"
  - truth: "availability: 'all' returns educational error with migration guidance"
    status: failed
    reason: "Generic Pydantic enum rejection ('Input should be available, blocked or remaining') not a custom educational error. CONTEXT.md D-05 explicitly chose no interception."
    artifacts:
      - path: "src/omnifocus_operator/contracts/use_cases/list/_enums.py"
        issue: "No custom educational message for 'all' — generic enum error"
    missing:
      - "Custom error guiding agent to omit the filter or use remaining"
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
---

# Phase 47: Cross-Path Equivalence & Breaking Changes — Verification Report

**Phase Goal:** SQL and bridge paths produce identical date filter results, and deprecated filter inputs return educational migration guidance
**Verified:** 2026-04-08T23:16:03Z
**Status:** gaps_found
**Re-verification:** No — initial verification

---

## Goal Achievement

### Observable Truths (from Roadmap Success Criteria)

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | Cross-path equivalence tests cover all date filter variants; both paths produce identical results including inherited effective dates | VERIFIED | TestDateFilterCrossPath: 10 tests x 2 paths = 20 passing. task-7 (due=None, effective_due=set) included correctly on both paths |
| 2 | `urgency` filter returns educational error pointing to `due: 'overdue'` / `due: 'soon'` | FAILED | Generic Pydantic "Extra inputs are not permitted" — no educational guidance. CONTEXT.md D-09 explicitly chose no interception |
| 3 | `completed: true` returns educational error pointing to `completed: 'any'` / `completed: {last: '1w'}` | FAILED | Generic Pydantic enum error — no educational guidance. CONTEXT.md D-09 explicitly chose no interception |
| 4 | COMPLETED and DROPPED removed from AvailabilityFilter enum | VERIFIED | `_enums.py` contains exactly AVAILABLE, BLOCKED, REMAINING; no COMPLETED/DROPPED |
| 5 | `availability: "all"` and `availability: "any"` return educational errors with migration guidance | FAILED | Generic Pydantic enum rejection ("Input should be 'available', 'blocked' or 'remaining'") not educational guidance. CONTEXT.md D-05 chose no custom interception |
| 6 | `defer: {after: "now"}` returns hint about availability: 'blocked' | VERIFIED | DEFER_AFTER_NOW_HINT in warnings.py; detect in domain.py resolve_date_filters() |
| 7 | `defer: {before: "now"}` returns hint about availability: 'available' | VERIFIED | DEFER_BEFORE_NOW_HINT in warnings.py; detected in domain.py resolve_date_filters() |
| 8 | Tool descriptions updated with date filter syntax and availability vs defer distinction | VERIFIED | LIST_TASKS_TOOL_DOC contains D-17a text; all 7 per-field descriptions match D-17b verbatim; AVAILABILITY_DOC matches D-17c |
| 9 | REMAINING shorthand expands to AVAILABLE+BLOCKED with redundancy warnings | VERIFIED | expand_task_availability() in domain.py; 7 new tests in test_service_domain.py passing |
| 10 | Empty availability list [] accepted on both ListTasksQuery and ListProjectsQuery | VERIFIED | Validator removed from both; default is [REMAINING] |

**Score:** 7/10 truths verified

---

## Note on Intentional Deviations (Truths 2, 3, 5)

The 3 failed truths share a common root: CONTEXT.md D-09 and D-05, recorded before planning, explicitly decided that no custom educational error interception was needed. The developer confirmed in the discussion log:

> "User pointed out the project is unreleased with zero external users. The urgency filter never existed as a parameter. No migration paths needed — just make changes directly."

The PLAN frontmatter (must_haves) for plan 01 does NOT include BREAK-01 or BREAK-02 as must-haves, and the BREAK-06/08 treatment (Pydantic rejection counts) was the developer's explicit decision. The behaviors ARE rejected — just with generic Pydantic messages rather than custom educational ones.

The gaps report these as failures because they conflict with the roadmap Success Criteria. If the developer wants to formally accept these deviations, they can add overrides to this VERIFICATION.md (see suggestion below).

**This looks intentional.** To accept these deviations, add to VERIFICATION.md frontmatter:

```yaml
overrides:
  - must_have: "urgency filter returns educational error pointing to due: 'overdue' / due: 'soon'"
    reason: "urgency filter never existed; project pre-release with zero users. Generic Pydantic rejection sufficient. CONTEXT.md D-09."
    accepted_by: "flo"
    accepted_at: "2026-04-08T23:16:03Z"
  - must_have: "completed: true returns educational error pointing to completed: 'any' / completed: {last: '1w'}"
    reason: "completed boolean never accepted; project pre-release with zero users. Generic Pydantic enum error sufficient. CONTEXT.md D-09."
    accepted_by: "flo"
    accepted_at: "2026-04-08T23:16:03Z"
  - must_have: "availability: 'all' returns educational error with migration guidance"
    reason: "Generic Pydantic rejection acceptable for pre-release project. No users to migrate. CONTEXT.md D-05."
    accepted_by: "flo"
    accepted_at: "2026-04-08T23:16:03Z"
```

---

## Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/contracts/use_cases/list/_enums.py` | Trimmed AvailabilityFilter + renamed LifecycleDateShortcut | VERIFIED | REMAINING present; ALL="all" present; no COMPLETED/DROPPED/ANY |
| `src/omnifocus_operator/service/domain.py` | REMAINING expansion + defer hint detection | VERIFIED | `AvailabilityFilter.REMAINING in filters` + `field_name == "defer" and isinstance(value, DateFilter)` |
| `src/omnifocus_operator/agent_messages/descriptions.py` | Updated per-field date filter descriptions + D-17a tool doc | VERIFIED | DUE_FILTER_DESC starts "Filter by due date (effective/inherited)"; LIST_TASKS_TOOL_DOC contains "availability vs defer" |
| `src/omnifocus_operator/agent_messages/warnings.py` | Defer hint constants + availability redundancy warnings | VERIFIED | DEFER_AFTER_NOW_HINT, DEFER_BEFORE_NOW_HINT, AVAILABILITY_REMAINING_INCLUDES_AVAILABLE, AVAILABILITY_REMAINING_INCLUDES_BLOCKED all present |
| `tests/test_cross_path_equivalence.py` | Date filter cross-path tests with inherited effective date coverage | VERIFIED | TestDateFilterCrossPath at line 1209; 10 test methods; task-7 (due=None, effective_due=_DUE_DATE) tested on both paths |

---

## Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/use_cases/list/tasks.py` | `contracts/use_cases/list/_enums.py` | AvailabilityFilter.REMAINING default | VERIFIED | Line 68: `default=[AvailabilityFilter.REMAINING]` |
| `service/domain.py` | `agent_messages/warnings.py` | DEFER_AFTER_NOW_HINT import | VERIFIED | Local import inside resolve_date_filters() at line 182-185 |
| `tests/test_cross_path_equivalence.py` | `BridgeOnlyRepository` | seed_bridge_repo | VERIFIED | `seed_bridge_repo` function with date fields: dueDate, effectiveDueDate, completionDate etc. |
| `tests/test_cross_path_equivalence.py` | `HybridRepository` | seed_sqlite_repo | VERIFIED | `seed_sqlite_repo` with INTEGER effectiveDateDue/ToStart/Planned columns |

---

## Data-Flow Trace (Level 4)

Not applicable — phase produces test infrastructure and enum/description changes, not data-rendering components.

---

## Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| AvailabilityFilter has exactly 3 members | `python3 -c "from omnifocus_operator.contracts.use_cases.list._enums import AvailabilityFilter; print(list(AvailabilityFilter))"` | [AVAILABLE, BLOCKED, REMAINING] | PASS |
| LifecycleDateShortcut.ALL == "all" | `python3 -c "from omnifocus_operator.contracts.use_cases.list._enums import LifecycleDateShortcut; print(LifecycleDateShortcut.ALL)"` | all | PASS |
| urgency rejected (not educational) | `ListTasksQuery(urgency='overdue')` | "Extra inputs are not permitted" (generic) | PASS (rejected) |
| availability="any" rejected (not educational) | `ListTasksQuery(availability=['any'])` | "Input should be 'available', 'blocked' or 'remaining'" (generic) | PASS (rejected) |
| Cross-path date filter tests pass | `uv run pytest tests/test_cross_path_equivalence.py -k "DateFilter" -q` | 20 passed | PASS |
| Full suite | `uv run pytest -x -q` | 1907 passed, 97.77% coverage | PASS |

---

## Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|---------|
| EXEC-10 | 47-02 | Cross-path equivalence tests prove SQL and bridge paths identical for date filters | VERIFIED | TestDateFilterCrossPath 10 tests x 2 paths = 20 passing |
| EXEC-11 | 47-02 | Cross-path test data includes tasks with inherited effective dates (direct NULL, effective non-NULL) | VERIFIED | task-7: due=None, effective_due=_DUE_DATE; test_due_before_includes_direct_and_inherited asserts task-7 in results |
| BREAK-01 | 47-01 | urgency filter removed — educational error if agent uses it | FAILED | Generic Pydantic "Extra inputs are not permitted"; no educational guidance. Intentional per CONTEXT.md D-09 |
| BREAK-02 | 47-01 | completed field rejects boolean — educational error | FAILED | Generic Pydantic enum error; no educational guidance. Intentional per CONTEXT.md D-09 |
| BREAK-03 | 47-01 | COMPLETED and DROPPED removed from AvailabilityFilter | VERIFIED | _enums.py has AVAILABLE, BLOCKED, REMAINING only |
| BREAK-04 | 47-01 | defer: {after: "now"} returns guidance hint suggesting availability: 'blocked' | VERIFIED | DEFER_AFTER_NOW_HINT in domain.py resolve_date_filters() |
| BREAK-05 | 47-01 | defer: {before: "now"} returns guidance hint suggesting availability: 'available' | VERIFIED | DEFER_BEFORE_NOW_HINT in domain.py resolve_date_filters() |
| BREAK-06 | 47-01 | availability: "any" returns educational error suggesting omit filter | FAILED | Generic Pydantic enum rejection. Intentional per CONTEXT.md D-05 |
| BREAK-07 | 47-01 | Tool descriptions updated with date filter syntax and availability vs defer | VERIFIED | LIST_TASKS_TOOL_DOC, LIST_PROJECTS_TOOL_DOC, all 7 per-field descriptions updated |
| BREAK-08 | 47-01 | availability: "all" returns educational error — guide to completed: "any" / dropped: "any" | FAILED | Generic Pydantic enum rejection. Intentional per CONTEXT.md D-05 |

---

## Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `src/omnifocus_operator/agent_messages/descriptions.py` | 386 | `TODO(v1.5)` comment | Info | Pre-existing v1.5 milestone note — not introduced by phase 47 |

No blockers or warnings introduced by this phase.

---

## Human Verification Required

None — all core behaviors are verifiable programmatically. The VALIDATION.md notes tool description rendering in Claude Desktop as manual-only, but this is informational/presentation quality, not correctness.

---

## Gaps Summary

Three failures share the same root cause: the developer explicitly rejected custom educational error interception before planning (CONTEXT.md D-09, D-05), based on the project being pre-release with zero users. The behaviors ARE rejected — just with generic Pydantic validation messages rather than rich educational errors.

The roadmap Success Criteria (SC-2, SC-4) were drafted using the "breaking changes" framing from the milestone spec. The developer subsequently recognized this framing doesn't apply to a pre-release project and overrode the intent during the context session. The PLAN frontmatter did not include BREAK-01 or BREAK-02 in must_haves, and BREAK-06/08 treatment (generic Pydantic counts) was the developer's explicit choice.

**To clear these gaps:** Either add overrides (see suggestion above) or implement custom educational error messages for urgency, completed=True, availability="any", and availability="all".

---

_Verified: 2026-04-08T23:16:03Z_
_Verifier: Claude (gsd-verifier)_
