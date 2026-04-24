---
phase: 57-parent-filter-filter-unification
plan: 04
subsystem: api
tags: [list-tasks, parent-filter, name-resolution, repo-layer, service-layer, agent-warnings]

# Dependency graph
requires:
  - phase: 57-parent-filter-filter-unification
    provides: "Unified service-layer subtree expansion (get_tasks_subtree), single repo primitive for scope filtering, pipeline-level cross-filter warnings (FILTERED_SUBTREE / PARENT_PROJECT_COMBINED)"
provides:
  - "Contract rename: ListTasksRepoQuery.task_id_scope → candidate_task_ids"
  - "New repo primitive: ListTasksRepoQuery.pinned_task_ids (Option A for G1 anchor preservation)"
  - "Service-layer empty-scope short-circuit (G2) + no-match semantic flip (G3) + parent anchor tracking (G1)"
  - "Repo-layer OR-with-pinned WHERE clause, symmetric across hybrid SQL + bridge_only Python"
  - "New agent warning: EMPTY_SCOPE_INTERSECTION_WARNING (fires alongside PARENT_PROJECT_COMBINED when scopes disjoint)"
  - "FILTER_NO_MATCH + FILTER_DID_YOU_MEAN reworded — 'This filter was skipped.' trailing text dropped; did-you-mean suggestions preserved"
  - "Cross-path equivalence (D-15) restored for empty-scope case and locked by explicit pinned-IDs equivalence tests"
affects: ["57-05 (G4 availability under-alerting — orthogonal)", "v1.4.1 gap closure", "35.2 D-02e superseded"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Two-field scope primitive at repo layer: candidate_task_ids (filterable pool, other predicates apply) + pinned_task_ids (unconditionally included, bypasses pruning)"
    - "OR-with-pinned WHERE shape in SQL and Python: `(t.id IN pinned) OR (t.id IN candidate AND <other predicates>)`"
    - "Service-layer empty-scope short-circuit before repo delegation when both primitives resolve to empty"
    - "Name-resolver no-match returns empty result (not silent fallback to full set)"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/contracts/use_cases/list/tasks.py — ListTasksRepoQuery: task_id_scope → candidate_task_ids + new pinned_task_ids"
    - "src/omnifocus_operator/service/service.py — _resolve_scope_filter/_resolve_tags/_resolve_parent/_build_repo_query, + new _is_empty_scope_query + _emit_empty_intersection_warning_if_applicable, short-circuit in execute()"
    - "src/omnifocus_operator/service/subtree.py — docstring primitive rename"
    - "src/omnifocus_operator/repository/hybrid/query_builder.py — OR-with-pinned WHERE clause + rename"
    - "src/omnifocus_operator/repository/bridge_only/bridge_only.py — pinned union after sequential filter chain + rename"
    - "src/omnifocus_operator/agent_messages/warnings.py — FILTER_NO_MATCH/FILTER_DID_YOU_MEAN reworded + EMPTY_SCOPE_INTERSECTION_WARNING"
    - "tests/test_list_pipelines.py — 2 tests flipped, 11 new tests (TestEmptyScopeShortCircuit, TestFilterNoMatchWarningText, TestParentAnchorPreservation), xfail marker removed from the pinned-preservation test, 1 pre-G1 test flipped"
    - "tests/test_query_builder.py — 5 new TestTasksPinnedFilter tests + mechanical rename"
    - "tests/test_hybrid_repository.py — 2 new pinned tests + mechanical rename"
    - "tests/test_bridge_only_repository.py — 2 new TestPinnedTaskIds tests"
    - "tests/test_cross_path_equivalence.py — 2 new pinned equivalence tests + mechanical rename"
    - "tests/test_list_contracts.py — TestRepoQueryFieldParity updated + 2 new tests (pinned/candidate presence) + negative assertion on old name"
    - "tests/test_service_domain.py — test_no_match_no_suggestion flipped to assert 'skipped' NOT in warning"
    - ".planning/milestones/v1.3-phases/35.2-.../35.2-CONTEXT.md — D-02e SUPERSEDED note referencing 57-04-SUMMARY.md"

key-decisions:
  - "Rename repo-facing field from task_id_scope → candidate_task_ids. The repo layer has no 'anchor' concept; the new two-field shape (candidate + pinned) describes the two logical roles."
  - "Option A for G1: OR-with-pinned at the repo layer. Alternatives (service post-assembles result; repo UNION) were rejected — OR keeps pagination/count/ordering honest by construction."
  - "Short-circuit at the service layer when (candidate=[] AND pinned empty) OR tag_ids=[]. Prevents hybrid's 'len > 0' guard from treating empty-list as no-filter (G2 root cause)."
  - "EMPTY_SCOPE_INTERSECTION_WARNING fires only when BOTH project AND parent were set by the caller. Single-scope-resolves-to-empty doesn't get an extra warning — the 0-item result speaks for itself."
  - "Parent anchor tracking is task-only. When parent resolves to a project, no anchor is injected (projects aren't list_tasks rows). Task-type anchors are filtered through project_scope when both are set (D-05 AND semantics)."
  - "Reword FILTER_NO_MATCH / FILTER_DID_YOU_MEAN to drop 'This filter was skipped.' — with the new contract, the filter is NOT skipped; the result is empty. Did-you-mean suggestions are preserved."
  - "Phase 35.2 D-02e ('skip the filter' fallback) marked SUPERSEDED. It bundled two UX choices into one option; unbundling lets did-you-mean live alongside empty-on-no-match."

patterns-established:
  - "OR-with-pinned repo-layer composition: when an anchor-style primitive exists alongside a filterable pool, compose as OR at the WHERE level rather than post-assembling. Keeps pagination/count correct by construction."
  - "Empty-vs-None distinction in service scope returns: None = 'filter not set'; set() = 'filter set but resolved to zero'. The downstream short-circuit catches the latter before repo dispatch."
  - "Cross-path symmetry: any new primitive on ListTasksRepoQuery must ship equivalent wiring in hybrid SQL + bridge_only Python and be locked by at least one cross_path_equivalence test."

requirements-completed: [UNIFY-02, UNIFY-07, UNIFY-08, PARENT-04, PARENT-05, WARN-01, WARN-05, WARN-06]

# Metrics
duration: 16min
completed: 2026-04-24
---

# Phase 57-04: G1/G2/G3 Gap Closure Summary

**Atomic closure of UAT-57 gaps G1 (anchor preservation), G2 (empty-scope cross-path divergence), G3 (no-match resolver fallback) — via a `pinned_task_ids` primitive and repo-layer OR-with-pinned semantic, plus a service-layer short-circuit that restores D-15 cross-path equivalence by construction.**

## Performance

- **Duration:** ~16 min
- **Started:** 2026-04-24T00:18:53Z
- **Completed:** 2026-04-24T00:35:08Z
- **Tasks:** 3
- **Files modified:** 13 (+ 1 planning context note)

## Accomplishments

- **G1 closed:** Parent anchors are preserved under AND-composition with subtree-pruning filters (flagged, tags, availability, date filters). The existing strict-xfail test at `tests/test_list_pipelines.py:2058` passes and its marker is removed. 7 new anchor-preservation pipeline tests lock the behavior across single-match, multi-match, multi-project, inside-project-scope, and outside-project-scope cases.
- **G2 closed:** The disjoint-scopes case (`list_tasks(project="P1", parent="T_in_P2")`) now returns 0 items + two warnings (PARENT_PROJECT_COMBINED + EMPTY_SCOPE_INTERSECTION) across BOTH repo paths. Previously returned 1624 items on hybrid vs. 0 on bridge_only — D-15 violation. Fixed at the service layer by construction: both repos never see empty `candidate_task_ids` + no pinned.
- **G3 closed:** Name-resolver no-match produces an empty result + a reworded "no match" warning (the word "skipped" is gone). Did-you-mean suggestions are preserved. Affects `project`, `parent`, and `tags` filters uniformly.
- **Contract rename:** `task_id_scope` → `candidate_task_ids` across src/, tests/. Zero remaining references in src/; the 3 remaining references in tests/ are intentional negative-assertion tests on the old name.
- **Repo symmetry:** Hybrid SQL + bridge_only Python both implement the OR-with-pinned semantic with equivalent results, locked by 2 new cross_path_equivalence tests.
- **Phase 35.2 D-02e superseded:** Context note added pointing at this SUMMARY.

## Task Commits

1. **Task 1: Contract rename + add pinned_task_ids (dormant)** — `5a0b03ec` (refactor)
2. **Task 2: Service short-circuit + anchor tracking + warning rewording** — `2859e13f` (fix)
3. **Task 3: Repo OR-with-pinned WHERE clause + new repo/cross-path tests** — `9fdcbc10` (fix)

## Files Created/Modified

- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` — `ListTasksRepoQuery` gains `candidate_task_ids` (renamed from `task_id_scope`) + new `pinned_task_ids`; both default `None`.
- `src/omnifocus_operator/service/service.py` — `_resolve_scope_filter` returns `(set(), resolved)` on no-match; `_resolve_tags` unconditional assignment; `_resolve_parent` tracks `self._parent_anchor_ids` (task-type only); `_build_repo_query` computes `pinned_task_ids = _parent_anchor_ids ∩ _project_scope`; two new helpers (`_is_empty_scope_query`, `_emit_empty_intersection_warning_if_applicable`); `execute` short-circuits before `_delegate`.
- `src/omnifocus_operator/service/subtree.py` — Docstring primitive-name update.
- `src/omnifocus_operator/repository/hybrid/query_builder.py` — `build_list_tasks_sql` assembles `WHERE ... AND ((t.id IN <pinned>) OR (<AND chain>))` when pinned is set; pinned placeholders come first in params tuple; preserves invariant `WHERE pi.task IS NULL` outside the OR.
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` — `list_tasks` unions pinned tasks from full task list after date filters; preserves deterministic `items.sort(key=lambda t: t.id)`.
- `src/omnifocus_operator/agent_messages/warnings.py` — `FILTER_NO_MATCH` + `FILTER_DID_YOU_MEAN` drop "This filter was skipped." trailing text; `EMPTY_SCOPE_INTERSECTION_WARNING` added.
- `tests/test_list_pipelines.py` — 2 flips (G3), 7 anchor-preservation tests (TestParentAnchorPreservation), 3 empty-scope tests (TestEmptyScopeShortCircuit), 2 warning-text tests (TestFilterNoMatchWarningText), xfail marker removed from `test_list_tasks_parent_with_pruning_filter_preserves_anchor`, and 1 existing pre-G1 test (`test_list_tasks_parent_and_tags_filter_and_composition`) flipped to expect anchor preservation.
- `tests/test_query_builder.py` — 5 new `TestTasksPinnedFilter` tests + mechanical rename.
- `tests/test_hybrid_repository.py` — 2 new pinned tests + mechanical rename.
- `tests/test_bridge_only_repository.py` — 2 new `TestPinnedTaskIds` tests.
- `tests/test_cross_path_equivalence.py` — 2 new pinned equivalence tests + mechanical rename.
- `tests/test_list_contracts.py` — `TestRepoQueryFieldParity` asserts both new fields, + 2 new tests, + negative assertion on old name.
- `tests/test_service_domain.py` — `test_no_match_no_suggestion` asserts `"skipped"` NOT in warning.
- `.planning/milestones/v1.3-phases/35.2-uniform-name-vs-id-resolution-at-service-boundary-for-all-list-filters/35.2-CONTEXT.md` — D-02e SUPERSEDED note.

## Decisions Made

See `key-decisions` in frontmatter. Highlights:

- **Rename: `task_id_scope` → `candidate_task_ids`.** The repo layer has no "anchor" concept; the new two-field pair (`candidate_task_ids` + `pinned_task_ids`) describes the two logical roles (filterable pool + unconditionally-included anchors).
- **Option A for G1 (OR-with-pinned at the repo).** Rejected alternatives: service-layer post-assembly (breaks pagination/count by construction); repo UNION (harder to reason about with ORDER BY).
- **Empty-vs-None return contract.** `None` = "scope not set"; `set()` = "scope set but resolved to zero". Service short-circuit catches the latter.
- **Single-scope-empty gets NO new warning.** `list_tasks(parent="ExistingProjectThatHasZeroTasks")` returns 0 items with no EMPTY_SCOPE_INTERSECTION — the 0-item result is self-explanatory. Only when both `project` and `parent` are set does the warning fire.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Existing pre-G1 test locked the wrong behavior**
- **Found during:** Task 3 (repo OR-with-pinned landing)
- **Issue:** `test_list_tasks_parent_and_tags_filter_and_composition` at `tests/test_list_pipelines.py:2025` asserted the pre-G1 pruning behavior (anchor dropped when tags predicate doesn't match). With the G1 fix, the anchor is now correctly preserved as context.
- **Fix:** Flipped the assertion to `{"anchor", "c1", "c3"}` and added a docstring explaining the G1 semantic.
- **Files modified:** `tests/test_list_pipelines.py`
- **Verification:** `uv run pytest tests/test_list_pipelines.py -q` passes.
- **Committed in:** `9fdcbc10` (Task 3 commit)

**2. [Rule 3 - Blocking] `ListResult[Task]` parameterization failed at runtime**
- **Found during:** Task 2 (execute short-circuit)
- **Issue:** Used `return ListResult[Task](...)` in the short-circuit path; `Task` lives behind `TYPE_CHECKING`, raising `NameError` at runtime.
- **Fix:** Switched to the unparameterized `ListResult(...)` constructor in the short-circuit branch. The function annotation still parameterizes the return type; runtime generic alias is unnecessary.
- **Files modified:** `src/omnifocus_operator/service/service.py`
- **Verification:** `uv run pytest tests/test_list_pipelines.py -q` passes.
- **Committed in:** `2859e13f` (Task 2 commit)

**3. [Rule 1 - Bug] Existing domain test locked the old "skipped" wording**
- **Found during:** Task 2 (warning rewording)
- **Issue:** `tests/test_service_domain.py::TestCheckFilterResolution::test_no_match_no_suggestion` asserted `"skipped" in warnings[0].lower()`, which is the exact wording Phase 57-04 removes.
- **Fix:** Flipped the assertion to `"skipped" not in warnings[0].lower()` with a docstring note.
- **Files modified:** `tests/test_service_domain.py`
- **Verification:** `uv run pytest tests/test_service_domain.py -q` passes.
- **Committed in:** `2859e13f` (Task 2 commit)

### Flagged-to-Orchestrator

**4. ROADMAP.md update not applied (worktree protection)**
- **Plan requirement:** Per `files_modified`, the plan lists `.planning/ROADMAP.md` (lines 65, 75, 83 carried `task_id_scope` references).
- **Worktree rule (per `<parallel_execution>`):** "DO NOT modify ROADMAP.md from this worktree — the orchestrator's post-merge protection restores it from main."
- **What's needed:** After merge, the orchestrator should update ROADMAP.md lines 65, 75, 83 to rename `task_id_scope` → `candidate_task_ids` where the phrasing describes current-state primitives (line 65 "one repo-layer task_id_scope primitive"; line 75 "ListTasksRepoQuery.task_id_scope: list[str]" wire-level primitive; line 83 the retired `project_ids` / added `task_id_scope` bullet should note the rename). The Phase 57 line 85 already mentions the rename in its gap-closure description. Historical mentions in SUMMARYs under `.planning/phases/57-*/` stay as-is per plan (frozen history).
- **Also:** ROADMAP.md line 93 says "G2 — Empty `task_id_scope` cross-path divergence" — should become `candidate_task_ids`.
- **Impact:** Zero functional impact; naming consistency only.

---

**Total deviations:** 3 auto-fixed (2 Rule 1 pre-G1 test locks, 1 Rule 3 runtime import) + 1 flagged to orchestrator (ROADMAP.md in worktree-protected files).
**Impact on plan:** All auto-fixes necessary for correctness; no scope creep. The ROADMAP.md flag is cosmetic/documentation and must be applied by the orchestrator.

## Issues Encountered

- Initial `pinned_task_ids` test params in `test_query_builder.py` assumed a param order (candidate before flagged) that didn't match the actual SQL builder ordering (flagged before candidate). Fixed by re-running the test and correcting the expected param index order — no code change needed.
- Default availability filter contributes OR clauses to the WHERE chain even without any user predicates, so the initial "no OR in SQL when only pinned is set" test invariant was wrong. Adjusted the test to check `"OR" in data_q.sql` + first-param placement instead.

## Threat Flags

None — this plan modifies existing filter composition at the repo layer; no new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Known Stubs

None. All data paths are wired end-to-end.

## TDD Gate Compliance

Task commits follow the RED → GREEN pattern per TDD task:

- **Task 1 (RED/GREEN):** Contract tests added for new fields, then fields added to the model. Single commit because the rename + field addition are coupled mechanical edits; tests flip from RED to GREEN within the same commit.
- **Task 2 (RED/GREEN):** Pipeline tests added first (flips + new tests); these failed against pre-Task-2 code. Service wiring landed alongside, bringing G2+G3 tests to GREEN and leaving G1 tests correctly RED (handoff to Task 3).
- **Task 3 (GREEN):** Repo wiring lands; previously-RED G1 anchor tests + the existing strict-xfail test flip to GREEN; 9 new repo-layer tests land.

Final verification: `uv run pytest -q` → 2537 passed, 0 strict-xfail failures.

## Grep Invariants (Before/After)

| Invariant | Before | After | Target |
|-----------|--------|-------|--------|
| `\btask_id_scope\b` in `src/` | 15 | **0** | 0 |
| `\btask_id_scope\b` in `tests/` | 20 | **3** (intentional negative assertions) | 0 (excluding negatives) |
| `\bcandidate_task_ids\b` in `src/ tests/` | 0 | **56** | ≥ 25 |
| `\bpinned_task_ids\b` in `src/ tests/` | 0 | **38** | ≥ 10 |
| `This filter was skipped` in `src/` | 2 | **0** | 0 |

## Self-Check

Verified via `ls` / `git log`:
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` present, contains `candidate_task_ids`, `pinned_task_ids`.
- `src/omnifocus_operator/service/service.py` present, contains `_is_empty_scope_query`, `_emit_empty_intersection_warning_if_applicable`, `self._parent_anchor_ids`, `pinned_task_ids=pinned_task_ids`.
- `src/omnifocus_operator/repository/hybrid/query_builder.py` present, contains `pinned_task_ids`, `pinned_placeholders`.
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` present, contains `query.pinned_task_ids`.
- `src/omnifocus_operator/agent_messages/warnings.py` present, contains `EMPTY_SCOPE_INTERSECTION_WARNING`.
- `.planning/milestones/v1.3-phases/35.2-.../35.2-CONTEXT.md` contains `SUPERSEDED by Phase 57-04`.
- Commits `5a0b03ec`, `2859e13f`, `9fdcbc10` present in `git log`.

## Self-Check: PASSED

## Next Phase Readiness

- **Plan 57-05 (G4 availability under-alerting)** is orthogonal to this plan and unblocked. G1 availability tests in this plan pass because the anchor-preservation path is independent of the availability-alerting decision.
- The `pinned_task_ids` primitive is available for future extensions (e.g., a user-facing "always include these specific tasks" feature), though no such feature is planned in v1.4.1.
- ROADMAP.md wording update (flagged deviation #4) needed at merge time.

---
*Phase: 57-parent-filter-filter-unification*
*Plan: 04*
*Completed: 2026-04-24*
