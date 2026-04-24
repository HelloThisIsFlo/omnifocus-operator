# Quick Task 260424-kd0: Simplify empty-result warning to single static message - Context

**Gathered:** 2026-04-24
**Status:** Ready for planning

<domain>
## Task Boundary

Collapse the parameterized `EMPTY_RESULT_WARNING_{SINGLE,MULTI}` surface (shipped in quick task 260424-j63) to a single static constant. Remove all filter-name enumeration, `is_non_default` iteration, camelCase alias lookups, alphabetical sorting, and zero-filter skip logic. Fires the static warning unconditionally when `list_tasks` returns zero items.

Source todo: `.planning/todos/pending/2026-04-24-simplify-empty-result-warning-to-single-static-message.md`

Dead-code sweep research: `260424-kd0-RESEARCH.md` (same directory) — the planner MUST read this; it surfaces 4 collateral test assertions + stale docstring trails that the source todo missed.

</domain>

<decisions>
## Implementation Decisions

### Warning wording
- Final text: `"The filters you selected didn't yield any results. Try widening the search."`
- Single constant named `EMPTY_RESULT_WARNING` in `src/omnifocus_operator/agent_messages/warnings.py`.
- No placeholders, no `.format()` call site.

### Emit semantics
- `_emit_empty_result_warning` fires the warning unconditionally when `result.items == []`.
- No filter-activity check. No zero-filter skip. The "zero filters + empty DB" edge case gets the generic warning too — deliberate loosening, judged acceptable (near-impossible in practice).
- Warning is APPENDED to `result.warnings`; existing warnings (PARENT_PROJECT_COMBINED_WARNING, FILTERED_SUBTREE_WARNING, DYM, etc.) continue to compose.

### `is_non_default` disposition
- Keep the predicate + its test class (`TestIsNonDefault` in `test_service_domain.py`) — still used by `service/domain.py::check_filtered_subtree` for subtree pruning.
- Only `service.py`'s import of it becomes dead. Drop from the import line, keep `UNSET`, `_Unset`, `is_set`, `unset_to_none`.

### Test matrix collapse
- 9-case `TestEmptyResultWarning` matrix → 3 cases.
- Keep (likely names after rewrite):
  1. Empty + filter active → warning present verbatim. Either fold Case 1 (single-filter scope empty) and Case 2 (project ∩ parent intersection empty) into a single "empty fires static warning" test, OR keep Case 2 separately to lock PARENT_PROJECT_COMBINED_WARNING composition. Planner's call — whichever is cleaner.
  2. Non-empty → no warning (regression guard).
  3. Empty + DYM trigger → both warnings compose (fuzzy candidate exists).
- Delete outright:
  - `test_pruning_empty_fires_single_filter_warning` (redundant with case 1 after static collapse)
  - `test_no_match_name_fires_single_filter_warning_with_dym` (subsumed by DYM composition case)
  - `test_no_match_name_no_suggestion_fires_only_unified` (redundant)
  - `test_three_plus_active_filters_alphabetical` (alphabetical lock — rationale gone)
  - `test_default_availability_does_not_count_as_filter` (is_non_default-zero-filter skip — gone)
  - `test_zero_filters_empty_result_no_warning` — **DELETE** (not invert). Flo's call: simplest path, matches "don't care about edge case."

### Collateral test updates (OUTSIDE the main matrix — from RESEARCH.md §6)
Four assertions in `tests/test_list_pipelines.py` currently assert the retired parameterized text. ALL must shift to `EMPTY_RESULT_WARNING`:
- Line 149 — `test_unresolved_project_returns_empty_with_warning`
- Line 250 — `test_single_match_no_multi_match_warning`
- Line 1918 — `test_list_tasks_parent_filter_no_match_returns_empty`
- Lines 2650–2653 — `test_parent_anchor_outside_project_scope_not_preserved`

The planner MUST include these in the plan — the source todo missed them.

### Stale docstring cleanup
- Remove (not reword) `260424-j63` quick-task references from:
  - `src/omnifocus_operator/service/domain.py:567,571` (`check_filter_resolution` docstring)
  - `tests/test_service_domain.py:1120,1132` (docstring refs inside DYM-related tests)
- Reword the comment header in `src/omnifocus_operator/agent_messages/warnings.py:198-203` to describe the single static constant (not the retired 2-constant parameterized design).
- Test docstrings inside `tests/test_list_pipelines.py` for the 4 collateral tests (+ the surviving 3 matrix tests) should be updated to not reference the retired design.

### Planning-artifact annotations
- `.planning/quick/260424-j63-unify-empty-result-warning-surface/260424-j63-SUMMARY.md`: add "SUPERSEDED by quick task 260424-kd0" header at the top. Strikethrough follow-up #1 ("Extend unified warning to list_projects/list_folders/list_tags") — architecturally obsolete under kd0.
- `.planning/phases/57-parent-filter-filter-unification/57-UAT.md`: append a second-iteration entry to the "Post-Resolution Gap Audit" section recording the live-probe that surfaced the `limit`/`offset` bug and the decision to collapse to static.

### Explicitly NOT doing
- No CHANGELOG entry. Agent-facing behavior change is small (live behavior equivalent to the agent; only the wording and one edge case shift). Flo declined.
- No change to `_is_empty_scope_query` short-circuit logic — that's a separate correctness fix (Phase 57-04 G2/G3), unrelated.
- No change to `FILTER_DID_YOU_MEAN`, `PARENT_PROJECT_COMBINED_WARNING`, `FILTERED_SUBTREE_WARNING`, `LIST_TASKS_INBOX_PROJECT_WARNING`, `PARENT_RESOLVES_TO_PROJECT_WARNING`.
- No touch to golden master snapshots (none capture the warning text).
- No touch to `docs/` or `README.md` (zero hits).

### Claude's Discretion
- Exact rewritten test method names and docstrings after the matrix collapse.
- Exact rewritten comment header in `warnings.py` (1-2 lines describing the static constant + kd0 reference).
- Whether to fold Case 1 and Case 2 or keep them separate for PARENT_PROJECT composition explicitness.

</decisions>

<specifics>
## Specific Ideas

- Net LOC delta from source todo: ~70 LOC smaller than the shipped j63 version.
- Scope: service layer only. No contract changes, no repo-layer changes.
- Test verification: run `uv run pytest tests/test_list_pipelines.py tests/test_service_domain.py -x -q` after edits. All pass → commit.
- Single logical commit preferred (code + tests + docs annotations together) — this is a tightly-coupled simplification where intermediate states leave tests red.

</specifics>

<canonical_refs>
## Canonical References

- Source todo (full design): `.planning/todos/pending/2026-04-24-simplify-empty-result-warning-to-single-static-message.md`
- Dead-code research (MUST READ): `.planning/quick/260424-kd0-simplify-empty-result-warning-to-single-/260424-kd0-RESEARCH.md`
- Prior quick task (superseded): `.planning/quick/260424-j63-unify-empty-result-warning-surface/`
- Phase 57-04 UAT trail: `.planning/phases/57-parent-filter-filter-unification/57-UAT.md`

</canonical_refs>
