---
phase: 260424-kd0
plan: 01
subsystem: service
tags: [warnings, list_tasks, agent-ux, cleanup, simplification]
duration_minutes: ~15
completed: 2026-04-24
commits:
  - 74fbf6ad  # refactor(260424-kd0): collapse empty-result warning to static constant
diff_stats:
  files_changed: 8
  insertions: 88
  deletions: 277
  net_loc: -189
supersedes:
  - 260424-j63 (parameterized EMPTY_RESULT_WARNING_{SINGLE,MULTI} surface)
requires:
  - Phase 57 parent-filter pipeline scaffolding (unchanged)
  - `_is_empty_scope_query` short-circuit (unchanged; unrelated to warning surface)
provides:
  - EMPTY_RESULT_WARNING (single static constant)
  - Simplified `_ListTasksPipeline._emit_empty_result_warning` (2-line body)
  - 3-case `TestEmptyResultWarning` matrix
affects:
  - src/omnifocus_operator/agent_messages/warnings.py
  - src/omnifocus_operator/service/service.py
  - src/omnifocus_operator/service/domain.py
  - tests/test_list_pipelines.py
  - tests/test_service_domain.py
  - .planning/quick/260424-j63-unify-empty-result-warning-surface/260424-j63-SUMMARY.md
  - .planning/phases/57-parent-filter-filter-unification/57-UAT.md
  - .planning/todos/completed/2026-04-24-simplify-empty-result-warning-to-single-static-message.md (moved from pending/)
decisions:
  - Text locked: "The filters you selected didn't yield any results. Try widening the search."
  - Unconditional fire on empty (no filter-activity predicate, no zero-filter skip).
  - Deliberate loosening: zero-filter + empty DB now gets the nudge too.
  - `is_non_default` predicate itself stays (still live in `check_filtered_subtree`).
  - Fold old Cases 1+2 into single composition test (kept PARENT_PROJECT composition lock).
---

# Phase 260424-kd0 Plan 01: Simplify Empty-Result Warning to Single Static Message Summary

Collapsed the parameterized `EMPTY_RESULT_WARNING_{SINGLE,MULTI}` surface (shipped in 260424-j63) to a single static `EMPTY_RESULT_WARNING` — removed ~70 LOC of filter enumeration, camelCase alias lookups, alphabetical sort, and zero-filter skip logic that the agent never semantically parsed. Net -189 LOC.

## What Shipped

### Source changes

- **`warnings.py`** — `EMPTY_RESULT_WARNING_SINGLE` + `EMPTY_RESULT_WARNING_MULTI` replaced by one static `EMPTY_RESULT_WARNING`. Six-line header comment condensed to two lines referencing kd0.
- **`service.py`** — Imports updated (removed both retired constants, added `EMPTY_RESULT_WARNING`; removed `is_non_default` from `contracts.base` import line). `_active_filter_names` helper deleted entirely (~18 LOC). `_emit_empty_result_warning` rewritten to a 2-line body: return unchanged if non-empty, else append the static constant.
- **`domain.py`** — `check_filter_resolution` docstring stripped of `260424-j63` references; behavioral description preserved intact.

### Test changes

- **`test_list_pipelines.py`**
  - Added `EMPTY_RESULT_WARNING` to the warnings import block.
  - 4 collateral assertions (lines 149, 250, 1918, 2650-2653) now assert `EMPTY_RESULT_WARNING` via the imported constant; surrounding docstrings reworded to describe the static-nudge contract.
  - `TestEmptyResultWarning` class collapsed 9→3 methods:
    1. `test_empty_with_filters_fires_static_warning_and_composes_with_parent_project` — folds old Cases 1+2, locks both firing and `PARENT_PROJECT_COMBINED_WARNING` composition on a disjoint project+parent snapshot.
    2. `test_non_empty_result_does_not_fire_warning` — new regression guard.
    3. `test_empty_composes_with_dym_warning` — adapted from old Case 8, locks DYM standalone composition.
  - Deleted outright (per plan + CONTEXT.md): `test_pruning_empty_fires_single_filter_warning`, `test_no_match_name_fires_single_filter_warning_with_dym`, `test_no_match_name_no_suggestion_fires_only_unified`, `test_three_plus_active_filters_alphabetical`, `test_default_availability_does_not_count_as_filter`, `test_zero_filters_empty_result_no_warning` (deleted, not inverted — Flo's explicit call).
- **`test_service_domain.py`** — `260424-j63` references stripped from `test_no_match_with_suggestion` (line 1120) and `test_no_match_no_suggestion` (line 1132) docstrings; behavioral descriptions preserved.

### Planning artifact annotations

- **`260424-j63-SUMMARY.md`** — Prepended `⚠ SUPERSEDED by quick task 260424-kd0 (2026-04-24)` header note at top. Follow-up #1 ("Extend unified warning to list_projects/list_folders/list_tags") wrapped in `~~...~~` strikethrough with `*(obsolete under kd0 — parameterization deleted)*` suffix.
- **`57-UAT.md`** — New `### G2 — Second iteration (2026-04-24, kd0)` subsection appended under Post-Resolution Gap Audit. Records live-probe finding (`limit`/`offset`/`include`/`only` being enumerated as filters), decision rationale, full list of second-pass retirements, and the deliberate loosening of the zero-filter case.

### Todo

- `git mv .planning/todos/pending/2026-04-24-simplify-empty-result-warning-to-single-static-message.md .planning/todos/completed/` — history preserved per `feedback_use-git-mv-for-todos`.

## Net LOC Delta

Commit stats: 88 insertions, 277 deletions, **-189 net LOC**.

Plan target was `~70 LOC smaller than the shipped j63 version`. Actual delta is larger because the test-matrix collapse (262-line replacement of `TestEmptyResultWarning`) removed 6 tests plus their snapshot decorators, and the 4 collateral docstrings shed their j63 explanations. Source-layer alone accounts for roughly the ~70 LOC target:

- `warnings.py`: ~5 LOC (header comment + 2 constants → 2-line comment + 1 constant)
- `service.py`: ~30 LOC (`_active_filter_names` deletion + `_emit_empty_result_warning` simplification + one import line shrunk)
- `domain.py`: ~4 LOC (docstring bullets condensed)

## Verification Results

All green, single atomic commit (`74fbf6ad`):

```
uv run pytest tests/test_list_pipelines.py tests/test_service_domain.py -x -q
→ 328 passed in 0.97s

uv run mypy src/omnifocus_operator/service/service.py src/omnifocus_operator/agent_messages/warnings.py
→ Success: no issues found in 2 source files

grep -rn "EMPTY_RESULT_WARNING_SINGLE|EMPTY_RESULT_WARNING_MULTI|_active_filter_names" src/ tests/
→ zero hits

grep -n "260424-j63" src/omnifocus_operator/service/domain.py tests/test_service_domain.py
→ zero hits

Todo file: pending/ cleared ✓, completed/ present ✓
```

Pre-commit hooks (ruff check, ruff format, mypy) all passed.

## Decisions Made Under Claude's Discretion

Per CONTEXT.md §"Claude's Discretion":

1. **Test method names (3-case rewrite)** chosen as:
   - `test_empty_with_filters_fires_static_warning_and_composes_with_parent_project`
   - `test_non_empty_result_does_not_fire_warning`
   - `test_empty_composes_with_dym_warning`
   Names are explicit about the behavior each test locks — no decorative suffixes, no j63/kd0 archaeology.

2. **Reworded comment header in `warnings.py`** kept at exactly 2 lines (from the original 6) with a single `EMPTY_RESULT_WARNING` constant beneath.

3. **Fold vs. keep Cases 1+2** — folded per plan guidance. The folded test uses Case 2's disjoint project+parent snapshot so it locks BOTH the static warning firing AND PARENT_PROJECT_COMBINED_WARNING composition in one assertion block. Case 1's single-filter angle is now implicitly covered (static fires regardless of filter count).

4. **Collateral docstring rewording** — kept the pre-57-04/57-04-G3 archaeology where it was load-bearing for the test's intent ("why this test exists"), stripped the j63 parameterization-specific prose ("unified warning with alphabetical camelCase names" → "static empty-result warning").

5. **Docstring on `_emit_empty_result_warning`** — used the exact suggested shape from the plan (3 lines, references kd0, explicit "zero-filter empty DB is no longer special-cased" to lock the behavioral loosening).

## Deviations from Plan

None — plan executed exactly as written, including all 4 collateral assertion updates (RESEARCH.md-surfaced) and both planning artifact annotations. No auto-fixes required; no scope expansion.

## Self-Check: PASSED

**Files modified (verified on disk):**
- `src/omnifocus_operator/agent_messages/warnings.py` — FOUND, contains `EMPTY_RESULT_WARNING`
- `src/omnifocus_operator/service/service.py` — FOUND, imports `EMPTY_RESULT_WARNING`, no `is_non_default` or `_active_filter_names`
- `src/omnifocus_operator/service/domain.py` — FOUND, no `260424-j63` refs
- `tests/test_list_pipelines.py` — FOUND, 3-method `TestEmptyResultWarning`, 4 collateral assertions updated
- `tests/test_service_domain.py` — FOUND, no `260424-j63` refs at lines 1120/1132
- `.planning/quick/260424-j63-unify-empty-result-warning-surface/260424-j63-SUMMARY.md` — FOUND, SUPERSEDED header present, follow-up #1 struck through
- `.planning/phases/57-parent-filter-filter-unification/57-UAT.md` — FOUND, `G2 — Second iteration` subsection present
- `.planning/todos/completed/2026-04-24-simplify-empty-result-warning-to-single-static-message.md` — FOUND (renamed from pending/)

**Commit verified:**
- `74fbf6ad` — FOUND in `git log --oneline -5`

## TDD Gate Compliance

N/A — this is a `type: execute` refactor plan, not a `type: tdd` plan. No RED/GREEN/REFACTOR gate sequence required. The atomic single-commit approach was mandated by the plan because intermediate states have red tests by design (constants retired before import sites updated).
