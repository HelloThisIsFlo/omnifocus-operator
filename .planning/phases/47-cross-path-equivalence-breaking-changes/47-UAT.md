---
status: complete
phase: 47-cross-path-equivalence-breaking-changes
source: 47-01-SUMMARY.md, 47-02-SUMMARY.md
started: 2026-04-09T12:00:00Z
updated: 2026-04-09T12:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Enum Design — AvailabilityFilter Trimming
expected: AvailabilityFilter has exactly 3 members: AVAILABLE, BLOCKED, REMAINING. REMAINING="remaining" is the default on both query models. COMPLETED/DROPPED/ALL removed — lifecycle is now gated by date filters. Review: does this design align with OmniFocus UI vocabulary?
result: issue
reported: "Enum trimming for tasks is correct, but ListProjectsQuery shares the same AvailabilityFilter — projects lost COMPLETED/DROPPED/ALL with no date filter alternative. Projects can no longer query for completed or dropped projects. Fix: introduce ProjectAvailabilityFilter with AVAILABLE, BLOCKED, COMPLETED, DROPPED, ALL, REMAINING — restoring pre-47 behavior with same warnings, defaults, and validation."
severity: major

### 2. Empty Availability Semantics
expected: availability=[] is now accepted (no validation error). Combined with date filters, this enables queries like "only completed tasks" via `availability: [], completed: "all"`. Review: does the interaction model between empty availability and lifecycle date filters make sense?
result: issue
reported: "availability=[] bypasses the filter instead of meaning 'no remaining tasks'. Live test: availability=[] returns 2958 tasks (all remaining), while availability=['remaining'] returns 1662. Both repo paths skip the filter when list is empty: bridge uses `if query.availability:` (falsy), SQL builder returns empty clause. Combined with completed='all' it appears to work (581 completed + 2958 remaining = still shows completed) but the semantics are wrong — [] should mean zero remaining tasks, not 'no filter'."
severity: major

### 3. REMAINING Expansion & Redundancy Warnings
expected: REMAINING expands to {AVAILABLE, BLOCKED} at the service layer. Providing [AVAILABLE, REMAINING] or [BLOCKED, REMAINING] produces a redundancy warning. Verify by reviewing TestExpandTaskAvailability tests — 7 cases covering expansion, redundancy, empty list, and lifecycle merge.
result: pass

### 4. Defer Hint Detection
expected: When a defer field uses DateFilter with after="now" or before="now", a non-blocking educational hint is appended to warnings. The hint explains that "now" in a defer context means "relative to when the task becomes available." Review TestDeferHintDetection — 6 test cases covering after/before/both/none.
result: pass

### 5. D-17 Description Accuracy
expected: All 7 per-field date filter descriptions updated to D-17b verbatim text (effective/inherited, semantic guidance). LIST_TASKS_TOOL_DOC appended with D-17a text. LIST_PROJECTS_TOOL_DOC includes effective-date note. AVAILABILITY_DOC updated to D-17c text. LIFECYCLE_DATE_SHORTCUT_DOC references "all" not "any". Review: do descriptions accurately describe field behavior?
result: pass (autonomous)
notes: Verified all 7 per-field descriptions in descriptions.py match the tool schema served by MCP. LIST_TASKS_TOOL_DOC has D-17a appendix (effective values, lifecycle expansion, availability vs defer). LIST_PROJECTS_TOOL_DOC has effective-date note. AVAILABILITY_DOC updated to D-17c. LIFECYCLE_DATE_SHORTCUT_DOC says "all" not "any".

### 6. Cross-Path Date Filter Test Walkthrough
expected: 10 parametrized tests (20 total across bridge/sqlite) proving SQL and bridge paths produce identical date filter results. Covers: due_after exact/beyond, defer_before, planned_after, completed_after, dropped_after, combined (due+flagged), null exclusion, inherited effective dates. Review: do these tests exercise real scenarios and cover the right edge cases?
result: pass (autonomous)
notes: Reviewed TestDateFilterCrossPath (test_cross_path_equivalence.py:1209). 10 methods confirmed — covers due_before (direct+inherited), due_after (boundary+beyond), defer_before, planned_before, completed/dropped with lifecycle availability, combined due+flagged (AND logic), added date range, null exclusion. All use cross_repo fixture (parametrized bridge/sqlite). Real scenarios with meaningful assertions.

### 7. Inherited Effective Date Proof
expected: task-7 has due=None but effective_due=_DUE_DATE (inherited from parent proj-due). A due_before filter includes task-7 on both SQL and bridge paths. This proves D-16 inheritance behavior works correctly through date filters. Review the test data setup and assertion.
result: pass (autonomous)
notes: Confirmed task-7 setup at line 362: due=None, effective_due=_DUE_DATE, project_id="proj-due", parent_id="proj-due". proj-due has due=_DUE_DATE. test_due_before_includes_direct_and_inherited asserts task-7 is included alongside task-1 and task-4 (direct due). test_due_after_exact_match also includes task-7. Inheritance proof is solid.

### 8. Full Suite Green
expected: `uv run pytest -x -q` exits 0 with 1907+ passed tests. No regressions from enum trimming, description updates, or test data expansion.
result: pass (autonomous)
notes: 1907 passed in 24.68s, 97.77% coverage. Zero failures.

## Summary

total: 8
passed: 6
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "AvailabilityFilter trimming should not remove lifecycle values from projects"
  status: accepted
  reason: "User reported: ListProjectsQuery shares trimmed AvailabilityFilter — projects lost COMPLETED/DROPPED/ALL with no date filter alternative. Cannot query completed or dropped projects."
  severity: major
  test: 1
  root_cause: "Shared AvailabilityFilter enum trimmed for tasks but projects don't have date filters as replacement path"
  resolution: "Accepted — will be resolved by inserting a new phase to add date filters to list_projects (same approach as tasks). A gap-closure plan to introduce ProjectAvailabilityFilter was considered but discarded as too awkward given the upcoming date filter work."

- truth: "availability=[] should mean 'no remaining tasks' — only lifecycle inclusion filters produce results"
  status: failed
  reason: "User reported: Live test shows availability=[] returns 2958 tasks (all remaining) instead of 0. Both repo paths skip the availability filter when list is empty: bridge uses `if query.availability:` (falsy), SQL builder returns empty clause."
  severity: major
  test: 2
  root_cause: "Bridge path: `if query.availability:` is falsy for empty list — skips filter. SQL path: `_build_availability_clause` returns empty string for empty list — no WHERE clause added."
  artifacts:
    - path: "src/omnifocus_operator/repository/bridge_only/bridge_only.py"
      issue: "Line 193: `if query.availability:` skips filter for empty list"
    - path: "src/omnifocus_operator/repository/hybrid/query_builder.py"
      issue: "Line 137: `if not parts: return ''` produces no WHERE clause for empty list"
  missing:
    - "Both repo paths need explicit handling: empty availability list should match zero remaining tasks (return nothing unless lifecycle filters add rows)"
