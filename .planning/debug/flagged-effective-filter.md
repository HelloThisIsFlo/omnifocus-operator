---
status: resolved
trigger: "flagged filter only returns directly flagged tasks, not effectively flagged"
created: 2026-04-08T00:00:00Z
updated: 2026-04-08T00:00:00Z
---

## Current Focus

hypothesis: Both repository layers filter on `flagged` (direct) instead of `effectiveFlagged`/`effective_flagged` (inherited)
test: Trace filter logic in all three layers (SQL query builder, hybrid row mapper, bridge-only Python filter)
expecting: All filter paths use `flagged` column/field, none use `effectiveFlagged`
next_action: Awaiting human verification of the fix in real OmniFocus workflow

## Symptoms

expected: Filtering by flagged should return all "effectively flagged" tasks -- directly flagged AND those inheriting flagged from parent project/task
actual: Only directly flagged tasks returned. Effectively flagged tasks (inheriting from parent) are missing.
errors: None -- filter works, just incomplete
reproduction: Use list_tasks with flagged=true. Tasks whose parent project is flagged but which are not directly flagged will be absent.
started: Since flagged filter was implemented

## Eliminated

(none needed -- root cause found on first hypothesis)

## Evidence

- timestamp: 2026-04-08T00:01:00Z
  checked: Model layer (models/common.py)
  found: ActionableEntity has BOTH `flagged: bool` (line 103) and `effective_flagged: bool` (line 104). The model correctly distinguishes direct vs inherited flagged.
  implication: The data is available; the filter just doesn't use the right field.

- timestamp: 2026-04-08T00:02:00Z
  checked: Hybrid SQL query builder (repository/hybrid/query_builder.py lines 134-136)
  found: Task filter uses `t.flagged = ?` -- queries the `flagged` column directly
  implication: SQL filters on direct flagged, not `effectiveFlagged` column that exists in the SQLite schema

- timestamp: 2026-04-08T00:03:00Z
  checked: Hybrid SQL query builder for projects (repository/hybrid/query_builder.py lines 223-225)
  found: Project filter also uses `t.flagged = ?`
  implication: Same bug for projects -- filters direct flagged, not effective

- timestamp: 2026-04-08T00:04:00Z
  checked: Bridge-only repository (repository/bridge_only/bridge_only.py lines 163-164)
  found: Task filter uses `t.flagged == query.flagged` -- compares against model's `flagged` field
  implication: Bridge-only path has the SAME bug -- filters on direct flagged, not effective_flagged

- timestamp: 2026-04-08T00:05:00Z
  checked: Bridge-only repository for projects (repository/bridge_only/bridge_only.py lines 213-214)
  found: Project filter uses `p.flagged == query.flagged` -- same pattern
  implication: All four filter paths (task+project x hybrid+bridge) have the same bug

- timestamp: 2026-04-08T00:06:00Z
  checked: Hybrid row mappers (repository/hybrid/hybrid.py lines 354-355, 399-400)
  found: Row mapper reads BOTH `flagged` and `effectiveFlagged` from SQLite and maps to model correctly. The data is there, just not used for filtering.
  implication: The SQLite `effectiveFlagged` column is available and already read -- the fix is just to reference it in the WHERE clause

- timestamp: 2026-04-08T00:07:00Z
  checked: Bridge JS layer (bridge/bridge.js lines 146-147, 182-183)
  found: Bridge sends both `flagged` and `effectiveFlagged` for tasks and projects
  implication: Bridge-only path also has the effective value available on the model via `effective_flagged`

## Resolution

root_cause: All four flagged filter paths (tasks and projects, in both hybrid SQL and bridge-only Python) filter on the direct `flagged` field/column instead of the effective `effectiveFlagged`/`effective_flagged` field. The model, SQLite schema, and bridge all correctly distinguish between direct and effective flagged -- the filter logic simply references the wrong field.
fix: Changed all four flagged filter paths from direct `flagged` to effective `effectiveFlagged`/`effective_flagged`. Updated test helpers (`_minimal_task`, `_minimal_project`, `make_task_dict`, `make_project_dict`) to auto-sync `effectiveFlagged` from `flagged` when not explicitly overridden. Updated query builder test assertions to expect `effectiveFlagged` in SQL.
verification: Full test suite passes (1808 tests, 0 failures, 98% coverage).
files_changed:
  - src/omnifocus_operator/repository/hybrid/query_builder.py
  - src/omnifocus_operator/repository/bridge_only/bridge_only.py
  - tests/test_query_builder.py
  - tests/test_hybrid_repository.py
  - tests/conftest.py
