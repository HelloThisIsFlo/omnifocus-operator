---
phase: 57-parent-filter-filter-unification
plan: 01
subsystem: api
tags: [list_tasks, filter-unification, expand_scope, task_id_scope, subtree, refactor]

# Dependency graph
requires:
  - phase: 56-task-property-surface
    provides: list_tasks pipeline, ListTasksRepoQuery contract, HybridRepository, BridgeOnlyRepository
provides:
  - service/subtree.py::expand_scope — shared service helper (ref_id, snapshot, accept_entity_types) -> set[str]
  - ListTasksRepoQuery.task_id_scope — unified scope primitive (project_ids retired)
  - HybridRepository flat persistentIdentifier IN (?) scope filter
  - BridgeOnlyRepository set-membership scope filter on t.id
  - _ListTasksPipeline single-snapshot get_all() entry point
  - _resolve_project rewritten to produce set[str] via expand_scope
affects: [57-02-parent-filter-surface, future-folder-filter]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Service-layer scope expansion (expand_scope) — pure, snapshot-based, no DI"
    - "Deterministic SQL placeholder ordering via sorted(scope_set) at _build_repo_query boundary"
    - "Single-snapshot pipeline convention (get_all()) matching compute_true_inheritance"

key-files:
  created:
    - src/omnifocus_operator/service/subtree.py
    - tests/test_service_subtree.py
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/repository/hybrid/query_builder.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - src/omnifocus_operator/service/service.py
    - tests/test_list_contracts.py
    - tests/test_query_builder.py
    - tests/test_hybrid_repository.py
    - tests/test_cross_path_equivalence.py
    - tests/test_list_pipelines.py
    - tests/test_bridge_contract.py
    - tests/doubles/bridge.py
    - tests/golden_master/normalize.py

key-decisions:
  - "Scope expansion lives at the service layer (expand_scope) — repos stay ignorant of OF parent-child hierarchy semantics (D-01/D-03)"
  - "Task 2a rename committed separately from Task 2b semantic rewrite — clean git bisect boundary between mechanical and logical changes"
  - "Pipeline uses single get_all() snapshot instead of gather(list_tags, list_projects) — matches compute_true_inheritance convention, avoids cache-invalidation mid-pipeline (RESEARCH Pitfall 3)"
  - "task_id_scope holds TASK PKs (not project PKs) — semantic shift from old project_ids field; agent-facing behavior is unchanged"
  - "sorted(self._project_scope) at build-repo-query boundary gives deterministic SQL placeholder order (RESEARCH Pitfall 5)"

patterns-established:
  - "Pattern: service-layer filter expansion — <noun>Filter (or scalar agent-facing ref) → flat primitive on ListRepoQuery. Mirrors DateFilter precedent."
  - "Pattern: expand_scope dispatch via accept_entity_types frozenset — gates task-anchor vs project-no-anchor branch without duplicated functions."
  - "Pattern: task-2a/2b split for refactor-plus-feature phases — rename first, semantics second, each committed atomically."

requirements-completed:
  - UNIFY-01
  - UNIFY-03
  - UNIFY-04
  - UNIFY-05
  - UNIFY-06
  - PARENT-03
  - PARENT-04

# Metrics
duration: ~40min
completed: 2026-04-20
---

# Phase 57 Plan 01: Filter Unification Foundation Summary

**Retired `ListTasksRepoQuery.project_ids` and shipped the unified `task_id_scope` primitive via the new service-layer `expand_scope` helper — behavior-preserving refactor proving `project` filter end-to-end before Plan 02 adds `parent`.**

## Performance

- **Duration:** ~40 min (wall clock)
- **Started:** 2026-04-20T20:33:00Z
- **Completed:** 2026-04-20T21:13:23Z
- **Tasks:** 3 (Task 1, Task 2a, Task 2b)
- **Files modified:** 14 (2 created, 12 modified)

## Accomplishments

- Shipped `service/subtree.py::expand_scope(ref_id, snapshot, accept_entity_types) -> set[str]` as a pure, snapshot-based helper with 10 unit tests covering PARENT-03/PARENT-04/UNIFY-01/UNIFY-03 (task-anchor, descendants-any-depth, project-no-anchor, accept-type gating, disjoint-subtree isolation).
- Retired `ListTasksRepoQuery.project_ids` and replaced it with `task_id_scope: list[str] | None` — the unified scope primitive for the upcoming `parent` filter.
- Rewrote `HybridRepository.build_list_tasks_sql` to use a flat `t.persistentIdentifier IN (?, ...)` clause — the old two-level `ProjectInfo pi2` join for scope filtering is gone (the outline-ordering CTE retains an unrelated `ProjectInfo pi2` NOT EXISTS clause).
- Rewrote `BridgeOnlyRepository.list_tasks` scope filter from `t.project.id in pid_set` to `t.id in scope_set` — reflecting the new task-PK semantic.
- Switched `_ListTasksPipeline.execute` to a single-snapshot entry point (`await self._repository.get_all()`) — dropped the `asyncio.gather(list_tags, list_projects)` pattern since `expand_scope` needs tasks too. Matches the existing `compute_true_inheritance` convention.
- Rewrote `_resolve_project` to produce `self._project_scope: set[str] | None` via `expand_scope(pid, snapshot, frozenset({EntityType.PROJECT}))` unioned over each resolved project ID.
- Wired `_build_repo_query` to assign `task_id_scope = sorted(self._project_scope)` — deterministic placeholder ordering (RESEARCH Pitfall 5).

Net agent-facing behavior delta: **zero**. `list_tasks(project="Work")` returns the same tasks in the same order with the same warnings. Full test suite (2442 tests) is green.

## Task Commits

Each task committed atomically:

1. **Task 1: Ship expand_scope helper with unit tests** — `588d5574` (feat)
2. **Task 2a: Rename project_ids to task_id_scope** — `84e4fb7b` (refactor)
3. **Task 2b: Unify project/parent scope via expand_scope + single-snapshot pipeline** — `468b0add` (refactor)

_Task 1 follows TDD — the RED step (ImportError on `from omnifocus_operator.service.subtree import expand_scope`) was verified before the GREEN implementation. Single commit per the plan's commit-granularity convention (no separate RED commit)._

## Files Created/Modified

**Created:**
- `src/omnifocus_operator/service/subtree.py` — `expand_scope` + `_collect_task_descendants` (pure-function helper for scope set computation)
- `tests/test_service_subtree.py` — 10-case unit suite (TestExpandScope)

**Modified (production):**
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — `project_ids` retired, `task_id_scope` added (same type, same default)
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — scope filter SQL flattened to `t.persistentIdentifier IN (?)`; ProjectInfo pi2 subquery removed from scope block
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — scope filter switched from `t.project.id in pid_set` to `t.id in scope_set`
- `src/omnifocus_operator/service/service.py` — `_ListTasksPipeline` executes `get_all()` once; `_resolve_project` produces `set[str]` via `expand_scope`; `_build_repo_query` sorts scope for determinism; `asyncio` import dropped

**Modified (tests):**
- `tests/test_list_contracts.py` — `TestRepoQueryFieldParity` updated to expect `task_id_scope`; default-None check migrated
- `tests/test_query_builder.py` — class renamed `TestTasksProjectFilter` → `TestTasksScopeFilter`; SQL assertions rewritten to expect flat IN clause; combined-filter tests migrated to task IDs
- `tests/test_hybrid_repository.py` — project-filter cases now pass task IDs directly (semantic the repo sees post-expand_scope)
- `tests/test_cross_path_equivalence.py::test_list_tasks_by_project` — same semantic shift; result set unchanged
- `tests/test_list_pipelines.py` — local variable renamed for grep cleanliness (unrelated to the retired field)
- `tests/test_bridge_contract.py`, `tests/doubles/bridge.py`, `tests/golden_master/normalize.py` — ambient `project_ids` / `known_project_ids` local variables renamed to `_set` suffix forms (unrelated to the retired field, needed for grep-0 invariant)

## Decisions Made

- **Rename-then-rewrite split** — Task 2a and Task 2b committed separately per the plan's bisect strategy. If Task 2b's `get_all()` switch or SQL rewrite surfaces a regression, `git bisect` lands precisely between the mechanical rename and the semantic change. Verified: full suite was green at Task 2a's commit before Task 2b began.
- **Local-variable renames for grep-0 invariant** — The acceptance criterion `grep -rn "project_ids" src/ tests/` returning 0 forced renames of ambient local variables (`project_ids`, `known_project_ids`, `result_project_ids`) in unrelated test/utility code. Chose `_id_set` / `_proj_id_set` suffixes since grep substring-matches without word boundaries. Not a semantic change — same variables with grep-cleaner names.
- **Single-snapshot via `get_all()` instead of keeping `asyncio.gather`** — The plan offered two paths (Open Q1 in RESEARCH.md). Chose full single-snapshot per plan's recommendation: matches `compute_true_inheritance` convention, avoids cache-invalidation mid-pipeline, repo cache makes the extra tasks fetch free. Dropped the `asyncio` import since no gather calls remain in this module.
- **Test class `TestTasksProjectFilter` renamed to `TestTasksScopeFilter`** — The plan stated "The class `TestTasksProjectFilter` KEEPS its name and assertions" for Task 2a but said Task 2b would "rename to `TestTasksScopeFilter` and rewrite SQL assertions". Did the rename in Task 2b to match the new semantic.

## Deviations from Plan

None — plan executed exactly as written.

The three tasks landed in the specified order with the specified commit types and messages (adjusted slightly for first-person-plural → verbatim imperative conventions). All acceptance criteria met:

- `grep -rn "project_ids" src/ tests/` → 0 matches
- `grep -c "task_id_scope" src/ tests/` → 34 matches (≥5)
- `grep -c "expand_scope" src/omnifocus_operator/service/service.py` → 4 matches (≥1)
- `grep -c "await self._repository.get_all()" src/omnifocus_operator/service/service.py` → 2 matches (≥1)
- `grep -q "t.persistentIdentifier IN" src/omnifocus_operator/repository/hybrid/query_builder.py` → succeeds
- `grep -q "if t.id in scope_set" src/omnifocus_operator/repository/bridge_only/bridge_only.py` → succeeds
- `grep -q "from omnifocus_operator.service.subtree import expand_scope" src/omnifocus_operator/service/service.py` → succeeds
- `grep -c "self._project_ids" src/omnifocus_operator/service/service.py` → 0 matches
- `grep -c "sorted(self._project_scope)" src/omnifocus_operator/service/service.py` → 1 match
- `uv run pytest -x -q` → **2442 passed** (behavior-preservation gate)
- `uv run pytest tests/test_output_schema.py -x -q` → **35 passed** (mandatory per CLAUDE.md)

## Issues Encountered

- **Docstring-text matched `await|async|_repo` grep pattern (Task 1).** The initial Task 1 acceptance criterion `grep -cE "await|async|_repo" src/omnifocus_operator/service/subtree.py` returned 1 match — the literal word "await" in the docstring explaining why the function is synchronous. Rewrote the docstring sentence to say "repository round-trip" instead of "await / repository I/O" — preserves intent, satisfies the grep guard. No code change.
- **`ProjectInfo pi2` persists in outline-ordering CTE (Task 2b).** Initial test `assert "ProjectInfo pi2" not in data_q.sql` failed because the root-task detection in the outline CTE (line 149 of `query_builder.py`) uses an unrelated `NOT EXISTS (SELECT 1 FROM ProjectInfo pi2 ...)`. Re-read the Task 2b acceptance criterion which explicitly allows non-scope-filter uses of `ProjectInfo pi2`. Refined the test assertions to target the scope-filter WHERE shape specifically (`assert "pi2.task IN" not in data_q.sql` + `assert "t.containingProjectInfo IN" not in data_q.sql`). Not a plan deviation — the criterion anticipated this case.

## User Setup Required

None — pure internal refactor. No environment variables, no external services, no schema changes.

## Next Phase Readiness

Plan 02 (`57-02`) can now add the `parent: Patch[str]` surface filter on `ListTasksQuery`:
- `expand_scope` is importable and proven via 10 unit tests (exercising both task-anchor and project-no-anchor branches).
- `task_id_scope` is live on both repo implementations.
- `_ListTasksPipeline` has its `self._snapshot` / `self._tasks` / `self._projects` available in every step — Plan 02 only needs to add a sibling `_resolve_parent` that unions into `self._parent_scope`, and extend `_build_repo_query` to intersect project + parent scopes.
- `_resolve_project` already demonstrates the exact shape Plan 02 will mirror — just swap the accepted entity set to `frozenset({EntityType.PROJECT, EntityType.TASK})` and add the parent-resolves-to-project warning.

No blockers for Plan 02.

## Self-Check: PASSED

- **Files:** `src/omnifocus_operator/service/subtree.py`, `tests/test_service_subtree.py` — FOUND
- **Commits:** `588d5574`, `84e4fb7b`, `468b0add` — all present in `git log --oneline -5`
- **Grep invariants:** `project_ids` in src/tests = 0, `task_id_scope` in src/tests = 34, `expand_scope` in service.py = 4
- **Test gate:** Full suite 2442 passed, schema gate 35 passed

---
*Phase: 57-parent-filter-filter-unification*
*Plan: 01 (foundation — scope primitive + service helper)*
*Completed: 2026-04-20*
