---
phase: 57-parent-filter-filter-unification
plan: 03
subsystem: api
tags: [list_tasks, cross-filter-warnings, warn-01, warn-03, warn-04, filtered-subtree, parent-project-combined]

# Dependency graph
requires:
  - phase: 57-parent-filter-filter-unification
    plan: 02
    provides: ListTasksQuery.parent, _ListTasksPipeline._resolve_parent, service/resolve.py 3-arg resolve_inbox
provides:
  - FILTERED_SUBTREE_WARNING — WARN-01 constant with verbatim locked text (em-dash U+2014)
  - PARENT_PROJECT_COMBINED_WARNING — WARN-03 constant
  - DomainLogic.check_filtered_subtree — scope + other-dim predicate, availability excluded
  - DomainLogic.check_parent_project_combined — presence-based both-set check
  - _ListTasksPipeline.execute pipeline-level emission sites (post-resolution, pre-_delegate)
affects: [phase-58-and-beyond, list_tasks end-to-end warning surface]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Domain-layer warning check methods (WARN-04) — DomainLogic owns the predicate; pipeline just extends"
    - "Em-dash U+2014 verbatim-lock gate — byte-level fidelity against source-of-truth spec via grep acceptance criterion"
    - "availability excluded from 'other filter' predicate (D-13) — non-empty default would destroy signal"
    - "Presence-based warning semantics vs emptiness semantics — D-13 PARENT_PROJECT_COMBINED fires regardless of intersection cardinality"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/warnings.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/service/service.py
    - tests/test_service_domain.py
    - tests/test_list_pipelines.py

key-decisions:
  - "Both check methods return list[str] (not bool) — uniform with existing check_filter_resolution shape; pipeline caller does self._warnings.extend(...) without special-casing"
  - "Pipeline does NOT import the warning constants — domain method owns them; pipeline stays agnostic of specific warning text"
  - "Em-dash character written directly in source on first keystroke (not --) — blocking gate from CONTEXT.md line 168 + MILESTONE-v1.4.1.md line 180"
  - "check_filtered_subtree's other-filter predicate is a chain of is_set() calls — explicit list over introspection for readability and locked field set"
  - "test_verbatim_text uses `==` against imported constant (in-module gate) — drift from source-of-truth spec is caught separately by the em-dash grep acceptance criterion"

requirements-completed:
  - WARN-01
  - WARN-03
  - WARN-04

# Metrics
duration: ~25min
completed: 2026-04-20
---

# Phase 57 Plan 03: Cross-Filter Warnings Summary

**Shipped the two remaining pipeline-level warnings: FILTERED_SUBTREE (WARN-01) fires when scope filter combines with any other dimensional filter; PARENT_PROJECT_COMBINED (WARN-03) fires when both project and parent are set. Both live on DomainLogic (WARN-04) — closing all 20 Phase 57 requirements end-to-end.**

## Performance

- **Duration:** ~25 min (wall clock)
- **Started:** 2026-04-20T21:14:00Z (approx)
- **Completed:** 2026-04-20T21:38:33Z
- **Tasks:** 2 (Task 1, Task 2)
- **Files modified:** 5 (3 production + 2 test)

## Accomplishments

- Added `FILTERED_SUBTREE_WARNING` constant to `agent_messages/warnings.py` with the verbatim locked text from `MILESTONE-v1.4.1.md` line 180 — including the em-dash U+2014 character (not `--`). Source-of-truth fidelity enforced via both the in-module `test_verbatim_text` (imported constant equality check) and the em-dash grep acceptance criterion.
- Added `PARENT_PROJECT_COMBINED_WARNING` constant under the same new section header ("Task Tool: Scope Filter Semantics (Phase 57-03)").
- Added `DomainLogic.check_filtered_subtree(query) -> list[str]`: returns `[FILTERED_SUBTREE_WARNING]` iff `(is_set(query.project) or is_set(query.parent)) AND (any of flagged/in_inbox/tags/estimated_minutes_max/search/due/defer/planned/completed/dropped/added/modified is_set)`. `availability` explicitly excluded from the predicate per D-13 (non-empty default would destroy signal).
- Added `DomainLogic.check_parent_project_combined(query) -> list[str]`: returns `[PARENT_PROJECT_COMBINED_WARNING]` iff both `project` and `parent` are set. Presence-based (D-13) — fires regardless of whether the scope-set intersection is empty.
- Wired `_ListTasksPipeline.execute` to call both domain methods after `_build_repo_query()` and before `_delegate()` (RESEARCH Pattern 3 — emission is post-resolution for visibility into all filters). Pipeline does not import the constants; domain owns them.
- 18 new domain-layer tests (`TestCheckFilteredSubtree` + `TestCheckParentProjectCombined`) covering the full trigger matrix for both warnings.
- 12 new pipeline-level tests (`TestListTasksFilteredSubtreeWarning` + `TestListTasksParentProjectCombinedWarning` + `TestListTasksCrossFilterWarningsTogether`) proving the emission sites wire the domain checks into the agent-visible `result.warnings` list.

## Task Commits

Each task committed atomically with `--no-verify` (parallel executor):

1. **Task 1 — add warning constants + DomainLogic check methods:** `c4ee5c2c` (feat)
2. **Task 2 — wire pipeline emission + pipeline-level tests:** `7bf737bf` (feat)

TDD cycle for each task followed the plan: RED (ImportError / AssertionError confirmed) → GREEN (implementation + tests passing). No separate RED commits per the project's commit-granularity convention.

## Files Modified

**Production (3):**
- `src/omnifocus_operator/agent_messages/warnings.py` — two new constants under the "Task Tool: Scope Filter Semantics (Phase 57-03)" section header. Em-dash U+2014 preserved verbatim.
- `src/omnifocus_operator/service/domain.py` — imports extended with the two new constants + `ListTasksQuery` (TYPE_CHECKING block); two new methods adjacent to `check_filter_resolution`.
- `src/omnifocus_operator/service/service.py` — `_ListTasksPipeline.execute` extended with two `self._warnings.extend(self._domain.check_...(self._query))` calls AFTER `_build_repo_query()` and BEFORE `_delegate()`.

**Tests (2):**
- `tests/test_service_domain.py` — imports extended with the two constants + `ListTasksQuery`; two new test classes (`TestCheckFilteredSubtree` 13 cases, `TestCheckParentProjectCombined` 5 cases = 18 new tests).
- `tests/test_list_pipelines.py` — imports extended; three new test classes (`TestListTasksFilteredSubtreeWarning` 7 cases, `TestListTasksParentProjectCombinedWarning` 4 cases, `TestListTasksCrossFilterWarningsTogether` 1 case = 12 new tests) exercising the full trigger matrix end-to-end through `OperatorService`.

## Trigger Matrix Coverage

**WARN-01 FILTERED_SUBTREE (13 domain + 7 pipeline = 20 test cases):**

| Scenario | Domain test | Pipeline test | Fires? |
|----------|-------------|---------------|--------|
| Empty query | test_no_scope_no_other_no_warning | (implicit via no-scope-only test) | NO |
| project only | test_project_only_no_other_no_warning | test_filtered_subtree_warning_project_only_no_other | NO |
| parent only | test_parent_only_no_other_no_warning | test_filtered_subtree_warning_parent_only_no_other | NO |
| project + flagged | test_project_with_flagged_fires | test_filtered_subtree_warning_project_and_flagged | YES (1×) |
| parent + flagged | test_parent_with_flagged_fires | (covered by project+flagged symmetry) | YES (1×) |
| project + tags | test_project_with_tags_fires | — | YES |
| parent + tags | — | test_filtered_subtree_warning_parent_and_tags | YES (1×) |
| project + search | test_project_with_search_fires | — | YES |
| project + due filter | test_project_with_due_filter_fires | — | YES |
| parent + due filter | — | test_filtered_subtree_warning_parent_and_due_filter | YES (1×) |
| project + completed filter | test_project_with_completed_filter_fires | — | YES |
| project + availability only | test_project_with_availability_does_not_fire | test_filtered_subtree_warning_availability_only_does_not_fire | NO (D-13) |
| availability only (no scope) | test_availability_only_does_not_fire | — | NO |
| flagged only (no scope) | — | test_filtered_subtree_warning_no_scope_only_dimensional | NO |
| project+parent + flagged | test_both_project_and_parent_with_flagged_fires_once | test_both_warnings_together (fires once) | YES (1×) |
| verbatim-text lock | test_verbatim_text | — | N/A |

**WARN-03 PARENT_PROJECT_COMBINED (5 domain + 4 pipeline = 9 test cases):**

| Scenario | Domain test | Pipeline test | Fires? |
|----------|-------------|---------------|--------|
| Empty query | test_neither_set_no_warning | — | NO |
| project only | test_project_only_no_warning | test_parent_project_combined_project_only | NO |
| parent only | test_parent_only_no_warning | test_parent_project_combined_parent_only | NO |
| Both set (different values) | test_both_set_fires | test_parent_project_combined_both_set_fires | YES (1×) |
| Both set (same value) | test_both_set_different_filters_still_fires | test_parent_project_combined_both_same_value_still_fires | YES (1×) — D-13 |
| Both set + other filter | — | test_both_warnings_together | YES (1×) alongside WARN-01 |

## Verbatim-Text Gate Result

- **In-module check:** `test_verbatim_text` — PASS. Asserts the returned warning equals the imported `FILTERED_SUBTREE_WARNING` constant byte-for-byte.
- **Em-dash positive gate (U+2014 fidelity):** `grep -F $'true parent \xe2\x80\x94 fetch separately' src/omnifocus_operator/agent_messages/warnings.py` — PASS (exit 0, match found).
- **Em-dash negative gate (no double-hyphen drift):** `grep -F 'true parent -- fetch separately' src/omnifocus_operator/agent_messages/warnings.py` — PASS (exit 1, no match).

Both verbatim-lock gates pass. The constant is byte-identical to `MILESTONE-v1.4.1.md` line 180.

## Decisions Made

- **Task 1 committed as a single feat commit** — the plan allowed separate RED/GREEN commits but the project's commit-granularity convention is one commit per task, matching Plan 01 and Plan 02 precedent. The TDD cycle still ran: RED verified with an `ImportError`, then the implementation landed and tests passed.
- **Em-dash character written directly, not copy-pasted from plan description** — the plan file escaped the em-dash in code blocks, but the `MILESTONE-v1.4.1.md` line 180 quote used the actual character. Wrote U+2014 directly on first keystroke per the "critical reminder" in the executor prompt. Both grep gates pass on the first attempt.
- **ListTasksQuery imported under TYPE_CHECKING in domain.py** — matches the file's existing convention for model imports used only in type annotations. Runtime dispatch uses `is_set()` which is already a runtime import at line 61.
- **Test fixture fixes (minor)** — two pipeline tests needed corrections: `tags=["tag-1"]` → `tags=[{"id": "tag-1", "name": "Urgent"}]` (task tags need TagRef dicts at model-validate time); `dueDate="2020-01-01T12:00:00"` → `dueDate="2020-01-01T12:00:00.000Z"` (Pydantic requires timezone-aware datetime for dueDate). Both are mechanical fixes, not deviations — the test intent (task with tag, task with past due date) is unchanged.

## Deviations from Plan

None — plan executed exactly as written. All acceptance criteria met:

### Task 1 acceptance
- `grep -q "^FILTERED_SUBTREE_WARNING" src/omnifocus_operator/agent_messages/warnings.py` → PASS
- `grep -q "^PARENT_PROJECT_COMBINED_WARNING" src/omnifocus_operator/agent_messages/warnings.py` → PASS
- `grep -q "Filtered subtree: resolved parent tasks are always included" src/omnifocus_operator/agent_messages/warnings.py` → PASS
- `grep -q "still references its true parent" src/omnifocus_operator/agent_messages/warnings.py` → PASS
- **Em-dash positive gate**: `grep -F $'true parent \xe2\x80\x94 fetch separately' src/omnifocus_operator/agent_messages/warnings.py` exits 0 → PASS
- **Em-dash negative gate**: `grep -F 'true parent -- fetch separately' src/omnifocus_operator/agent_messages/warnings.py` exits 1 → PASS
- `grep -q "def check_filtered_subtree" src/omnifocus_operator/service/domain.py` → PASS
- `grep -q "def check_parent_project_combined" src/omnifocus_operator/service/domain.py` → PASS
- `availability` not referenced in `check_filtered_subtree` code body (only in docstring explaining the exclusion) → PASS
- Test case count: 18 collected (need ≥ 13) → PASS
- `test_verbatim_text` passes → PASS

### Task 2 acceptance
- `grep -q "self._domain.check_filtered_subtree(self._query)" src/omnifocus_operator/service/service.py` → PASS
- `grep -q "self._domain.check_parent_project_combined(self._query)" src/omnifocus_operator/service/service.py` → PASS
- Emission ordering: lines 419–420 (AFTER `_build_repo_query()` at line 411, BEFORE `_delegate()` at line 422) → PASS
- Pipeline-level test count: 12 collected (need ≥ 12) → PASS
- `test_both_warnings_together` passes → PASS
- `test_filtered_subtree_warning_availability_only_does_not_fire` passes → PASS

### Overall
- `uv run pytest -x -q` full suite → **2506 passed** (97.59% coverage)
- `uv run pytest tests/test_output_schema.py -x -q` → **35 passed** (MANDATORY per CLAUDE.md)
- Quick-suite per VALIDATION.md → **728 passed** (3.91s)

## Behaviour Deltas

Pipeline-level warnings are now emitted from `_ListTasksPipeline.execute` for every agent call to `list_tasks`:

- `list_tasks(project="Work", flagged=True)` — NEW warning `FILTERED_SUBTREE_WARNING` surfaces in `result.warnings`. Purely additive — the task list itself is unchanged.
- `list_tasks(project="Work", parent="Review")` — NEW warning `PARENT_PROJECT_COMBINED_WARNING` surfaces in `result.warnings`. Intersection behavior is unchanged from Plan 02.
- `list_tasks(project="Work", parent="Review", flagged=True)` — BOTH warnings surface, each exactly once.
- `list_tasks(project="Work")` or `list_tasks(project="Work", availability=[...])` — no new warnings (scope-only with default-compatible filters stays silent).

Agents should interpret both warnings as pedagogical guidance, not as error signals — the results are still correct; the warnings help agents understand why a filtered result set may look incomplete (WARN-01) or help them choose a single scope filter when both are set (WARN-03).

## Issues Encountered

None material. Two minor test-fixture fixes surfaced during the GREEN run (TagRef shape + timezone-aware datetime) — both mechanical, both fixed inline without changing test intent.

## User Setup Required

None — pure internal domain + pipeline wiring. No environment variables, no external services, no schema changes. `test_output_schema.py` confirms the contract shape is unchanged.

## Phase 57 Closure Readiness

All 20 Phase 57 requirements now covered end-to-end across Plans 01/02/03:

**PARENT-01..09** — parent filter surface, resolution, subtree retrieval, anchor injection, no-match, multi-match, pagination, `$inbox` consumption, PARENT-09 null-rejection (Plan 02).
**UNIFY-01..06** — shared expansion function, byte-identical cross-filter equivalence, service-layer placement, repo-level primitive field, retired `project_ids` (Plans 01/02).
**WARN-01..05** — filtered-subtree (this plan), parent-resolves-to-project (Plan 02), parent+project combined (this plan), domain-layer placement (this plan), multi-match + inbox-substring reuse (Plan 02).

Recommended next action: `/gsd-verify-work 57`.

## Self-Check: PASSED

- **Files:** all 5 modified files exist on disk:
  - `src/omnifocus_operator/agent_messages/warnings.py` — FOUND
  - `src/omnifocus_operator/service/domain.py` — FOUND
  - `src/omnifocus_operator/service/service.py` — FOUND
  - `tests/test_service_domain.py` — FOUND
  - `tests/test_list_pipelines.py` — FOUND
- **Commits:** `c4ee5c2c`, `7bf737bf` — both present in `git log --oneline -5`
- **Grep invariants:**
  - `FILTERED_SUBTREE_WARNING` in warnings.py = 1 definition
  - `PARENT_PROJECT_COMBINED_WARNING` in warnings.py = 1 definition
  - `def check_filtered_subtree` in domain.py = 1
  - `def check_parent_project_combined` in domain.py = 1
  - Em-dash positive gate: exits 0
  - Em-dash negative gate: exits 1
- **Test gate:** full suite 2506 passed, output-schema 35 passed, quick-suite 728 passed.

---
*Phase: 57-parent-filter-filter-unification*
*Plan: 03 (pipeline cross-filter warnings — WARN-01 + WARN-03 + WARN-04)*
*Completed: 2026-04-20*
