---
phase: 57-parent-filter-filter-unification
plan: 02
subsystem: api
tags: [list_tasks, parent-filter, filter-unification, resolve_inbox, warn-02, cross-filter-equivalence]

# Dependency graph
requires:
  - phase: 57-parent-filter-filter-unification
    plan: 01
    provides: service/subtree.py::expand_scope, ListTasksRepoQuery.task_id_scope, single-snapshot pipeline
provides:
  - ListTasksQuery.parent — agent-facing Patch[str] filter with FILTER_NULL rejection
  - PARENT_FILTER_DESC — agent-facing description disclosing descendant-subtree semantic
  - Resolver.resolve_inbox 3-arg signature — single consolidation point for $inbox across project + parent
  - PARENT_RESOLVES_TO_PROJECT_WARNING — WARN-02 pedagogical hint
  - _ListTasksPipeline._check_inbox_parent_warning — mirrors project-side warning via reused constant (D-14)
  - _ListTasksPipeline._resolve_parent — scope-set producer via expand_scope with {PROJECT, TASK} accept set
  - _build_repo_query project ∩ parent intersection — AND semantics at service layer, flat task_id_scope at repo
affects: [57-03-pipeline-warnings, future-folder-filter]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "3-arg resolve_inbox as single consolidation point for $inbox semantics (D-09)"
    - "Entity-type introspection at _resolve_parent for WARN-02 (all-projects-only check)"
    - "Scope-set intersection at _build_repo_query before flattening to task_id_scope"
    - "Regression-test pattern: explicit test_*_existing_* cases locking pre-existing error contracts verbatim via re.escape on imported constants"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - src/omnifocus_operator/service/resolve.py
    - src/omnifocus_operator/service/service.py
    - tests/test_list_contracts.py
    - tests/test_service_resolve.py
    - tests/test_list_pipelines.py

key-decisions:
  - "Post-consumption contradiction gate in 3-arg resolve_inbox unifies cross-side cases (e.g. project='$inbox' + parent='SomeTask' now raises correctly) — small behavioural shift from the 2-arg form that returned early on consumption"
  - "Reused LIST_TASKS_INBOX_PROJECT_WARNING verbatim for parent (D-14), keeping the 'project=\"...\"' wording — documented agent-UX wart accepted in trade for the no-new-code path"
  - "WARN-02 fires only when EVERY resolved match is a project — mixed project+task resolutions stay silent (not a code smell, still a valid 'parent' use)"
  - "Cross-filter equivalence test (D-15) compares task payload byte-identically via model_dump(mode='json', by_alias=True); warnings surface differs (parent path fires WARN-02) and is orthogonal to the D-15 contract"

requirements-completed:
  - PARENT-01
  - PARENT-02
  - PARENT-05
  - PARENT-06
  - PARENT-07
  - PARENT-08
  - PARENT-09
  - UNIFY-02
  - WARN-02
  - WARN-05

# Metrics
duration: ~20min
completed: 2026-04-20
---

# Phase 57 Plan 02: Parent Filter Agent Surface Summary

**Shipped the agent-visible `parent` filter end-to-end — `ListTasksQuery.parent: Patch[str]`, 3-arg `resolve_inbox` consolidating `$inbox` semantics across both surface filters, `_resolve_parent` pipeline step with scope-set intersection into `task_id_scope`, WARN-02 pedagogical hint, and the D-15 cross-filter equivalence contract gate.**

## Performance

- **Duration:** ~20 min (wall clock)
- **Started:** 2026-04-20T21:07Z (approx — from branch base)
- **Completed:** 2026-04-20T21:27:24Z
- **Tasks:** 2 (Task 1, Task 2)
- **Files modified:** 8 (4 production + 4 test)

## Accomplishments

- Added `parent: Patch[str]` to `ListTasksQuery` with `PARENT_FILTER_DESC` agent-facing description disclosing the descendant-subtree semantic. `_PATCH_FIELDS` gained `"parent"` so the existing `reject_null_filters` validator fires `FILTER_NULL` for `parent=None` without new code.
- Extended `Resolver.resolve_inbox` to a 3-arg signature `(in_inbox, project, parent) -> (in_inbox, project, parent)`. `$inbox` on either side consumes into `in_inbox=True`; contradictions raise symmetrically. Post-consumption contradiction gate unifies cross-side cases.
- Added `PARENT_RESOLVES_TO_PROJECT_WARNING` (WARN-02). Fires exactly when every resolved match is a project — mixed project+task resolutions stay silent.
- Added `_ListTasksPipeline._check_inbox_parent_warning` (reuses `LIST_TASKS_INBOX_PROJECT_WARNING` verbatim per D-14).
- Added `_ListTasksPipeline._resolve_parent`: resolves against `[*projects, *tasks]` (D-11), calls `expand_scope(rid, snapshot, frozenset({EntityType.PROJECT, EntityType.TASK}))` (D-12), and sets `self._parent_scope: set[str] | None`.
- Extended `_build_repo_query` to intersect `self._project_scope & self._parent_scope` when both are present (D-05), flattening into the single `task_id_scope` repo primitive (sorted for deterministic placeholder order, Pitfall 5).
- 15 new pipeline tests (`TestListTasksParentFilter` + `TestListTasksParentProjectEquivalence`) covering resolve-by-name/ID, project-no-anchor behaviour, deep-descendant collection, no-match, multi-match (WARN-05 reuse), `$inbox` sentinel equivalence (PARENT-07), `$inbox + inInbox=false` contradiction (PARENT-08), inbox-substring warning reuse, tag AND-composition (PARENT-05), WARN-02 positive and negative cases, pagination (PARENT-06), project ∩ parent intersection (D-05), and the D-15 byte-identicality contract gate.
- 7 new contract tests in `TestListTasksParentField` covering the four PARENT-09 validation layers (`Patch[T]` string-only, `reject_null_filters`, `extra="forbid"`, MCP output schema) plus basic acceptance and `_PATCH_FIELDS` parity.
- 10 new `resolve_inbox` 3-arg test cases in `TestResolveInbox3Arg` covering the full matrix, including two explicit `test_resolve_inbox_3arg_existing_*` regression tests locking the pre-existing `CONTRADICTORY_INBOX_FALSE` and `CONTRADICTORY_INBOX_PROJECT` error contracts verbatim via `re.escape` on the imported constants.
- Existing `TestResolveInbox` 2-arg tests migrated mechanically to the 3-arg form (passing `parent=None`); all 12 existing cases still pass with identical assertions.

## Task Commits

Each task committed atomically:

1. **Task 1 — add parent field to ListTasksQuery + PARENT_FILTER_DESC:** `51948e52` (feat)
2. **Task 2a (intermediate) — resolve_inbox extended to 3-arg:** `8fa25062` (feat)
3. **Task 2b — add _resolve_parent + WARN-02 + cross-filter equivalence:** `41e10460` (feat)

_Task 2 was split across two commits for a clean git-bisect boundary: the signature change (2a) lands first with the existing 2-arg call pattern migrated and all resolve tests green; the pipeline wiring (2b) lands next with the new pipeline tests. This mirrors the Task 2a / Task 2b split Plan 01 used for the project-scope rewrite — precedent established in phase 57-01-SUMMARY.md._

## Files Modified

**Production (4):**
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — `parent: Patch[str]` field with `PARENT_FILTER_DESC`, `"parent"` added to `_PATCH_FIELDS`, import extended.
- `src/omnifocus_operator/agent_messages/descriptions.py` — new `PARENT_FILTER_DESC` constant adjacent to `PROJECT_FILTER_DESC`.
- `src/omnifocus_operator/agent_messages/warnings.py` — new `PARENT_RESOLVES_TO_PROJECT_WARNING` under a new "Task Tool: Parent Filter (Phase 57-02)" section header.
- `src/omnifocus_operator/service/resolve.py` — `resolve_inbox` rewritten to 3-arg (single consolidation point). Parent side uses `[EntityType.PROJECT, EntityType.TASK]` for `$`-prefix lookup.
- `src/omnifocus_operator/service/service.py` — `_ListTasksPipeline.execute` migrated to 3-arg `resolve_inbox` call; `_check_inbox_parent_warning` + `_resolve_parent` methods added; `_build_repo_query` extended with project ∩ parent intersection.

**Tests (4):**
- `tests/test_list_contracts.py` — new `TestListTasksParentField` class (7 cases). `TestRepoQueryFieldParity::test_tasks_shared_fields_match` updated to treat `parent` as query-only.
- `tests/test_service_resolve.py` — `TestResolveInbox` migrated to 3-arg (12 cases); new `TestResolveInbox3Arg` class (10 cases, including 2 regression tests).
- `tests/test_list_pipelines.py` — new `TestListTasksParentFilter` (14 cases) + `TestListTasksParentProjectEquivalence` (1 case).

## Decisions Made

- **Task 2 split into commits 2a + 2b** — the `resolve_inbox` signature change is self-contained (touching resolve.py + service.py execute site + resolve tests) and lands green on its own; the pipeline wiring (warning + `_resolve_parent` + `_build_repo_query` + pipeline tests) lands as a follow-up commit. This gives a clean git-bisect boundary between the mechanical signature migration and the new feature logic, matching the 2a/2b precedent established by Plan 01. Not a deviation — the plan's commit instructions allow atomic per-step commits, and each commit leaves the suite green.
- **Inline imports inside the regression tests** — the two `test_resolve_inbox_3arg_existing_*` tests import `CONTRADICTORY_INBOX_FALSE` / `CONTRADICTORY_INBOX_PROJECT` locally so the test file doesn't acquire new module-level imports and diff cleanly. If either constant is ever renamed in a future phase, these tests fail loudly on ImportError — which is the behaviour the plan's acceptance-criterion note called for ("if someone later renames `CONTRADICTORY_INBOX_FALSE`, the import fails loudly and these tests flag the drift").
- **WARN-02 negative assertion shape** — `test_list_tasks_parent_resolves_mixed_no_project_warning` uses `if result.warnings is not None: assert not any(...)` rather than asserting `warnings is None` outright. Multi-match + no-match emit other warnings, and the test's contract is specifically "WARN-02 does not fire in mixed mode" — not "no warnings at all." This keeps the assertion narrowly scoped to the requirement.
- **Cross-filter equivalence asserts task payload only** — the D-15 contract is "byte-identical task list when the ref resolves to the same project." WARN-02 fires only on the parent path, so the warning surface is not byte-identical by design. The test documents this with a comment and asserts on `model_dump`, `total`, and `has_more` — not `warnings`.

## Deviations from Plan

None — plan executed exactly as written. Every acceptance-criterion grep + test assertion landed on the first green run:

- `grep -q "PARENT_FILTER_DESC" src/omnifocus_operator/agent_messages/descriptions.py` → succeeds
- `grep -q 'parent: Patch\[str\] = Field(default=UNSET, description=PARENT_FILTER_DESC)' src/omnifocus_operator/contracts/use_cases/list/tasks.py` → succeeds
- `grep -q "def resolve_inbox" src/omnifocus_operator/service/resolve.py` → succeeds; signature line contains `parent: str | None`
- `grep -c "in_inbox = True" src/omnifocus_operator/service/resolve.py` → **2** (one per consumption branch)
- `grep -q "def _check_inbox_parent_warning" src/omnifocus_operator/service/service.py` → succeeds
- `grep -q "def _resolve_parent" src/omnifocus_operator/service/service.py` → succeeds (2 matches — `_AddTaskPipeline` has a method of the same name for the write-side; expected and not a conflict)
- `grep -q "PARENT_RESOLVES_TO_PROJECT_WARNING" src/omnifocus_operator/service/service.py` → succeeds
- `grep -q "self._project_scope & self._parent_scope" src/omnifocus_operator/service/service.py` → succeeds
- `grep -q "frozenset({EntityType.PROJECT, EntityType.TASK})" src/omnifocus_operator/service/service.py` → succeeds
- `grep -q "^PARENT_RESOLVES_TO_PROJECT_WARNING" src/omnifocus_operator/agent_messages/warnings.py` → succeeds
- `grep -c "test_resolve_inbox_3arg_existing_" tests/test_service_resolve.py` → **3** (2 test definitions + 1 docstring reference; ≥2 required)
- `grep -c "test_parent_and_project_byte_identical" tests/test_list_pipelines.py` → **1** (the D-15 gate exists)
- `uv run pytest -x -q` full suite → **2476 passed**
- `uv run pytest tests/test_output_schema.py -x -q` → **35 passed**

## Regression-Test Presence Confirmation

Per Plan 02 Task 2 acceptance-gate:

- `test_resolve_inbox_3arg_existing_project_inbox_in_inbox_false_still_raises` — **PRESENT** and **PASS**. Locks `CONTRADICTORY_INBOX_FALSE` verbatim via `re.escape(CONTRADICTORY_INBOX_FALSE)` on the imported constant.
- `test_resolve_inbox_3arg_existing_in_inbox_true_real_project_still_raises` — **PRESENT** and **PASS**. Locks `CONTRADICTORY_INBOX_PROJECT` verbatim via `re.escape(CONTRADICTORY_INBOX_PROJECT)` on the imported constant.

The pre-existing 2-arg error contracts survive the mechanical migration to 3-arg. No silent drift possible; any future rename of those constants will fail the regression tests at import time.

## Cross-Filter Equivalence (D-15) Result

`test_parent_and_project_byte_identical_for_same_project` — **PASS**. Proves UNIFY-02 end-to-end: `list_tasks(project="Work Projects")` and `list_tasks(parent="Work Projects")` produce byte-identical task lists (verified via `model_dump(mode="json", by_alias=True)`) plus identical `total` and `has_more`.

## Full-Suite Test Result

`uv run pytest -x -q` → **2476 passed** (33.17s). `uv run pytest tests/test_output_schema.py -x -q` → **35 passed**.

## Behaviour Deltas

The only user-visible semantic shift sits at the service layer:

- **3-arg `resolve_inbox`** now flows through a unified post-consumption contradiction gate. The old 2-arg form returned `(True, None)` directly on `$inbox` consumption; the new form flows through the final gate so e.g. `project="$inbox", parent="SomeTask"` correctly raises `CONTRADICTORY_INBOX_PROJECT`. This was explicitly called out in the plan's Task 2 Step 1 reasoning — the 2-arg cases that were already raising still raise the same constants verbatim (locked by the two regression tests), but the new cross-side cases now raise where the 2-arg form had no opinion (because it couldn't represent them).

Agent-facing API is purely additive — `parent` is a new optional field; no existing call shape changed.

## Issues Encountered

None. Every step of the TDD cycle (RED → GREEN) landed cleanly on the first attempt:

- Task 1 RED: `ListTasksQuery(parent="Work")` failed with `extra_forbidden` as expected — confirmed the field didn't exist.
- Task 1 GREEN: 8 new tests + 146 contract/schema tests pass.
- Task 2 RED: `resolver.resolve_inbox(None, None, None)` failed with TypeError (3 pos args but 4 given) as expected — confirmed the old 2-arg signature.
- Task 2 GREEN (intermediate, 8fa25062): all 80 resolve tests pass including the two regression cases.
- Task 2 GREEN (pipeline, 41e10460): 15 new pipeline tests + 311 core tests + 2476 full-suite pass.

The service.py 2-arg call site was migrated inline with the signature change, so no intermediate state where tests failed because of a caller mismatch.

## User Setup Required

None — pure internal wiring. No environment variables, no external services, no schema changes.

## Next Phase Readiness

Plan 03 (`57-03`) can now add the pipeline-level warnings:

- `FILTERED_SUBTREE_WARNING` — fires when scope filter (`project` or `parent`) is combined with any other filter dimension. Conditions already computable from the `ListTasksQuery` — no new pipeline state needed.
- `PARENT_PROJECT_COMBINED_WARNING` — fires when both `project` and `parent` are set. Same — query-level check only.

Both warnings are pure query inspections (no dependence on resolved IDs), so they slot into `_ListTasksPipeline.execute` post-`_build_repo_query` and pre-`_delegate`. `DomainLogic` is the natural home per WARN-04 ("warnings live in the domain layer, not projection").

No blockers for Plan 03.

## Self-Check: PASSED

- **Files:** all 8 modified files exist on disk:
  - `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — FOUND
  - `src/omnifocus_operator/agent_messages/descriptions.py` — FOUND
  - `src/omnifocus_operator/agent_messages/warnings.py` — FOUND
  - `src/omnifocus_operator/service/resolve.py` — FOUND
  - `src/omnifocus_operator/service/service.py` — FOUND
  - `tests/test_list_contracts.py` — FOUND
  - `tests/test_service_resolve.py` — FOUND
  - `tests/test_list_pipelines.py` — FOUND
- **Commits:** `51948e52`, `8fa25062`, `41e10460` — all present in `git log --oneline -5`.
- **Grep invariants:** see "Deviations from Plan" acceptance-criteria block above — all pass.
- **Test gate:** full suite 2476 passed, schema gate 35 passed, output-schema gate 35 passed.

---
*Phase: 57-parent-filter-filter-unification*
*Plan: 02 (parent filter agent surface — end-to-end)*
*Completed: 2026-04-20*
