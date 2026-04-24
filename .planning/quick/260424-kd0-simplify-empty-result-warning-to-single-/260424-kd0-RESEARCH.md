# Research: Simplify Empty-Result Warning — Dead Code Sweep

**Mode:** quick-task research
**Generated:** 2026-04-24
**Purpose:** Identify all dead code, stale refs, and orphan helpers that must be deleted atomically alongside the main simplification in todo `2026-04-24-simplify-empty-result-warning-to-single-static-message`.

## TL;DR

- `is_non_default` stays — still live in `service/domain.py` subtree pruning (`_SUBTREE_PRUNING_FIELDS`) and in its own test class `TestIsNonDefault`. Service.py loses its caller, nothing else.
- Service.py import line 34 must drop `is_non_default` (but keep `UNSET`, `_Unset`, `is_set`, `unset_to_none`).
- Service.py import block lines 26–27 must drop `EMPTY_RESULT_WARNING_MULTI` + `EMPTY_RESULT_WARNING_SINGLE` and add `EMPTY_RESULT_WARNING`.
- **Four collateral tests outside `TestEmptyResultWarning`** assert the old parameterized text — they must shift to the new static string (not just the 9-case matrix collapse noted in the todo).
- Stale docstrings in `service/domain.py:567-571`, `tests/test_list_pipelines.py` (4 locations) and `tests/test_service_domain.py` (2 locations) reference retired `FILTER_NO_MATCH` / parameterization — shorten, don't just redirect to `kd0`.
- No golden-master snapshots, no docs, no README, no `__init__.py` re-exports affected. CHANGELOG `[Unreleased]` section exists — candidate for an entry.
- `.planning/quick/260424-j63-.../SUMMARY.md` needs the supersession header; PLAN.md/CONTEXT.md are fine as-is (historical record).

## Findings

### 1. `is_non_default` callers

| Location | Classification |
|---|---|
| `src/omnifocus_operator/contracts/base.py:73` | DEFINITION — keep |
| `src/omnifocus_operator/contracts/base.py:155` (`__all__` export) | KEEP |
| `src/omnifocus_operator/service/domain.py:62` (import) | KEEP — still used |
| `src/omnifocus_operator/service/domain.py:141,607,620` (docstring + `check_filtered_subtree` body) | USED ELSEWHERE — keep (subtree pruning) |
| `src/omnifocus_operator/service/service.py:34` (import) | **DELETE from import** — only `_active_filter_names` uses it |
| `src/omnifocus_operator/service/service.py:645,655` (inside `_active_filter_names`) | DELETE — part of helper body |
| `tests/test_service_domain.py:36` (import) | KEEP — `TestIsNonDefault` tests remain valid (predicate still live for subtree pruning) |
| `tests/test_service_domain.py:1232,1358,1369-1412,1454` (8 tests in `TestIsNonDefault` + docstring mentions) | KEEP — predicate still in production use |
| `tests/test_list_pipelines.py:2407` (docstring in `test_default_availability_does_not_count_as_filter`) | DELETE — test itself is deleted in the matrix collapse |
| `tests/test_list_pipelines.py:2906,2934` | KEEP — unrelated subtree-pruning tests |

**Verdict:** `is_non_default` itself stays. Only service.py's usage is dead.

### 2. Service.py imports that become unused

File: `src/omnifocus_operator/service/service.py`

- **Line 26:** `EMPTY_RESULT_WARNING_MULTI` — REMOVE
- **Line 27:** `EMPTY_RESULT_WARNING_SINGLE` — REMOVE
- **Add:** `EMPTY_RESULT_WARNING` to the import list (lines 24–32, keep alphabetical)
- **Line 34:** `is_non_default` — REMOVE from the import list; `UNSET`, `_Unset`, `is_set`, `unset_to_none` all stay (verified via `grep -n "is_set\|unset_to_none\|_Unset\|UNSET" src/omnifocus_operator/service/service.py` — each has live callers outside `_active_filter_names`).
- **Line 57:** `ListTasksQuery` — KEEP (used at lines 232, 384, plus several other `ListTasksQuery.model_fields` uses remain — verified).
- **`.model_fields[...].alias` pattern:** the specific alias-lookup pattern only exists at lines 653–654 (inside `_active_filter_names`). Nothing else in `service.py` uses `.alias` on `model_fields`. No import change (it's attribute access), but flag: after this task, that pattern is gone from `service.py` entirely.

### 3. Dead constants / stale re-exports

- **`src/omnifocus_operator/agent_messages/warnings.py:204,206–208`** — `EMPTY_RESULT_WARNING_SINGLE` and `EMPTY_RESULT_WARNING_MULTI` definitions. DELETE per todo.
- **`src/omnifocus_operator/agent_messages/__init__.py`** — uses `from .warnings import *` (wildcard). No explicit re-export list to update. Wildcard will naturally pick up the new `EMPTY_RESULT_WARNING` and drop the retired pair.
- **`contracts/base.py:155` (`__all__`)** — only lists `is_non_default` (and friends). No `EMPTY_RESULT_WARNING*` entries. No change needed.
- **String literal `"resolved to zero tasks"`** — every hit in live code (`src/` and `tests/`, excluding `.claude/worktrees/`) is in the two retired constants + test assertions tied to them. No external helper constructs this text manually. Full active-code list:
  - `src/omnifocus_operator/agent_messages/warnings.py:204,207` — the two constants (deleted).
  - `src/omnifocus_operator/service/service.py:626` — *docstring* inside `_is_empty_scope_query` (phrase "single scope that resolved to zero tasks"). Not a format string; describes the short-circuit semantics. Flag for re-read but probably stays — it's describing the concept, not a template. **Recommend: leave it; it's about scope resolution, not the warning text.**
  - `tests/test_list_pipelines.py:149, 250, 1918, 2251, 2280, 2305, 2327, 2357, 2391, 2414, 2432, 2458, 2651` — assertions. Addressed in §6.

### 4. Stale docstrings / comments

**`src/omnifocus_operator/agent_messages/warnings.py:198–203`** — the 6-line header comment above the retired constants references `260424-j63`, "parameterized", "camelCase aliases", "alphabetically sorted", "two-layer model", "8-case test matrix". ALL of this is wrong after kd0. Replace with a 1–2 line header for the single constant, e.g.:

```python
# Quick task 260424-kd0 (2026-04-24): collapses the parameterized
# EMPTY_RESULT_WARNING_{SINGLE,MULTI} surface to one static nudge.
# Fires whenever list_tasks resolves to zero items; no filter enumeration.
EMPTY_RESULT_WARNING = "The filters you selected didn't yield any results. Try widening the search."
```

**`src/omnifocus_operator/service/service.py`:**
- **Lines 641–650** — entire `_active_filter_names` docstring: deleted with the helper. No follow-up.
- **Lines 660–665** — `_emit_empty_result_warning` docstring: references 260424-j63, "active filter", "zero-filter empty results are skipped per CONTEXT.md §zero-filter case". Rewrite to describe the static-append behavior per todo:
  ```
  """Append EMPTY_RESULT_WARNING when items == [].

  Quick task 260424-kd0 (2026-04-24): zero-filter empty DB is no longer
  special-cased — the agent already sees items=[] and the generic nudge
  costs nothing. See .planning/quick/260424-kd0-... for the rationale.
  """
  ```

**`src/omnifocus_operator/service/domain.py:563–572`** — `check_filter_resolution` docstring mentions `260424-j63` twice (lines 567, 571) as the "reworded" / "retires FILTER_NO_MATCH" justification. After kd0 the rewording still holds; the unified warning now happens unconditionally. Update wording to keep the operational description but point the quick-task reference at the new task or drop the trail entirely (Flo's call):
- Minimum: s/260424-j63/260424-kd0/ is **not** correct — the DYM-standalone rewording was genuinely a j63 decision. kd0 doesn't revisit it. **Recommend: shorten these docstring lines to describe the current behavior without a quick-task reference at all.**

**`tests/test_list_pipelines.py`** — 4 docstrings referencing j63/retired designs:
- **Line 138–140** (`test_unresolved_project_returns_empty_with_warning` docstring) — assertion at line 149 also updates (§6).
- **Line 239–243** (`test_single_match_no_multi_match_warning` docstring) — assertion at line 250 also updates (§6).
- **Line 526–535** (`test_unresolved_folder_no_suggestions_silent` docstring) — explains why `list_projects` is silent. Still accurate under kd0 (service-layer only, list_projects unaffected). **Flag but likely no change.**
- **Line 1907–1911** (`test_list_tasks_parent_filter_no_match_returns_empty` docstring) — assertion at line 1918 also updates (§6).
- **Lines 2634–2642** (`test_parent_anchor_outside_project_scope_not_preserved` docstring) — references "unified EMPTY_RESULT_WARNING" + "EMPTY_SCOPE_INTERSECTION_WARNING". Wording reword; assertion at 2650–2653 updates (§6).

**`tests/test_service_domain.py:1118–1135`** — 2 docstrings (lines 1120, 1132) referencing j63. The actual assertions (DYM text + `[]` return) are unaffected by kd0. Optional cleanup — either drop quick-task refs or leave as archaeological record. **Low priority — flag only.**

### 5. Planning artifacts (`.planning/quick/260424-j63-unify-empty-result-warning-surface/`)

- **`260424-j63-SUMMARY.md`** — per todo, add a "SUPERSEDED by quick task 260424-kd0" header at the top. Follow-ups §1 ("Extend unified warning to list_projects / list_folders / list_tags") is now moot — kd0 deletes the whole parameterization machinery the follow-up would have extended. Flag for cross-out in the supersession note.
- **`260424-j63-CONTEXT.md`** — describes decisions for the parameterized design. No header needed; it's a design record. Fine as-is.
- **`260424-j63-PLAN.md`** — describes implementation plan for the superseded design. Historical. Fine as-is.
- **No `REVIEW.md` / `VERIFICATION.md`** in that directory (only CONTEXT, PLAN, SUMMARY).

Additional planning artifact to update:

- **`.planning/phases/57-parent-filter-filter-unification/57-UAT.md`** — per the todo, append to the "Post-Resolution Gap Audit" section (lines 328+) recording the kd0 iteration. Existing G2 subsection (lines 350–365) describes the j63 unification; add a sibling "G2 — Second iteration (2026-04-24, kd0)" subsection noting the live-probe bug that surfaced `limit`/`offset`/`include`/`only` being listed as filters, and the decision to collapse to a static nudge.
- **`.planning/STATE.md`** — line 67 still describes item #15 (j63) as current; line 68 (#16 = kd0) is already queued. Once kd0 ships, line 67 may want a "✅ superseded by #16" flag (parallel to how j63 itself linked to 57-04). Flag only; Flo's call.

### 6. Test helpers / fixtures / imports (in `tests/test_list_pipelines.py`)

**Test-file imports (lines 20–23):**
```python
from omnifocus_operator.agent_messages.warnings import (
    FILTERED_SUBTREE_WARNING,
    PARENT_PROJECT_COMBINED_WARNING,
)
```
Neither is `EMPTY_RESULT_WARNING_*` — already clean. No import update needed. The test uses inline string literals for warning-text assertions, so no new `EMPTY_RESULT_WARNING` import is strictly required either, but the planner may want to import it for `assert x in result.warnings` precision.

**`class TestEmptyResultWarning` (lines 2220–2466):**

- No class-scoped fixtures. Each test uses its own `@pytest.mark.snapshot(...)` decorator.
- No helper functions outside the class exclusive to the to-be-deleted cases.
- No `@pytest.mark.parametrize` — each case is a distinct method.
- **9 methods present** (CONTEXT.md's 8-case matrix + 4a/4b split). The todo says keep 3 — recommendation for which 3 to keep (planner's call):
  - `test_scope_empty_fires_single_filter_warning` (2246) → rename/reword to `test_empty_result_fires_static_warning` or similar (empty + filter case).
  - `test_intersection_empty_fires_two_filter_warning` (2267) → could fold into the above, OR keep separately to lock that `PARENT_PROJECT_COMBINED_WARNING` still composes — may be cleaner to keep as a separate "composition" test.
  - `test_dym_standalone_with_unified_warning` (2450) → keep as the DYM-composition case.
  - `test_zero_filters_empty_result_no_warning` (2425) → **INVERT** under kd0: the todo says the static warning fires even in the zero-filter + empty-DB case now. This test's current assertion (`not any("resolved to zero tasks" in w ...)`) directly contradicts kd0 behavior. DELETE or REWRITE to assert the warning DOES fire.
  - **Delete outright:** `test_three_plus_active_filters_alphabetical` (alphabetical lock — whole justification gone), `test_default_availability_does_not_count_as_filter` (is_non_default-zero-filter skip gone), `test_no_match_name_fires_single_filter_warning_with_dym` vs. `..._no_suggestion_fires_only_unified` (redundant with the DYM composition case + the main empty case), `test_pruning_empty_fires_single_filter_warning` (redundant with main empty case).

**Assertions OUTSIDE the `TestEmptyResultWarning` class that assert the retired text** (these are *not* in the main matrix and were missed by the todo's "~5 of the 9" scope note — IMPORTANT for the planner):

| File:Line | Test | Current assertion (retired text) | Required update |
|---|---|---|---|
| `tests/test_list_pipelines.py:149` | `TestListTasksResolution::test_unresolved_project_returns_empty_with_warning` | `result.warnings == ["The 'project' filter resolved to zero tasks. No results."]` | Replace with `[EMPTY_RESULT_WARNING]` |
| `tests/test_list_pipelines.py:250` | `TestListTasksResolution::test_single_match_no_multi_match_warning` | Same pattern | Same update |
| `tests/test_list_pipelines.py:1918` | `TestListTasksParentFilter::test_list_tasks_parent_filter_no_match_returns_empty` | `assert "The 'parent' filter resolved to zero tasks. No results." in result.warnings` | Replace with `assert EMPTY_RESULT_WARNING in result.warnings` |
| `tests/test_list_pipelines.py:2650–2653` | `TestParentAnchorPreservation::test_parent_anchor_outside_project_scope_not_preserved` | `"The combination of filters 'parent', 'project' resolved to zero tasks. No results." in result.warnings` | Replace with `assert EMPTY_RESULT_WARNING in result.warnings` |

**These are the four collateral updates the planner MUST pick up in addition to the 9→3 matrix collapse.** The todo file's "Blast radius" section only mentions the 9-case matrix — the four above fall *outside* `TestEmptyResultWarning` and are easy to miss.

### 7. Golden master snapshots

Searched `tests/golden_master/**/*.json` for `EMPTY_RESULT`, `"resolved to zero"`, `"didn't yield"`, `260424-j63`. **Zero hits.** Golden snapshots capture write-path operations (add_tasks / edit_tasks / repetition flow), not list_tasks warning envelopes. No snapshot refresh required.

Per CLAUDE.md (`feedback_golden-master-human-only`) this confirms no human-gated capture is needed — purely because no snapshot is affected, not because agents are skipping the step.

### 8. Docs directory references

Searched `docs/*.md` + `docs/index.html` for `EMPTY_RESULT`, `"resolved to zero"`, `"didn't yield"`. **Zero hits.** `docs/architecture.md`, `docs/configuration.md`, `docs/model-taxonomy.md`, `docs/omnifocus-concepts.md`, etc. don't reference the warning surface. `README.md` also zero hits. No docs update required.

### 9. Changelog

**`CHANGELOG.md`** — has an `[Unreleased]` section (lines 7–12). No existing entry about either j63 or kd0 warning work. Candidate for an agent-facing-messages entry, e.g.:

> ### Changed
> - Empty-result warning on `list_tasks` simplified to a static nudge — fires whenever the query returns zero items, regardless of which filters were set.

Flag only — actual wording is Flo's call; the planner shouldn't draft prose.

## Unflagged cleanup opportunities

- **`src/omnifocus_operator/agent_messages/warnings.py:7`** — module docstring line: *"Parameterized warnings use {placeholder} syntax -- call .format() at the usage site."* Still true of many other constants in the file (e.g. `EDIT_COMPLETED_TASK`, `TAG_ALREADY_ON_TASK`, `FILTER_MULTI_MATCH`). No change needed — this is a general note, not a reference to the retired constants.
- **`.planning/quick/260424-j63-.../260424-j63-SUMMARY.md:130–138` "Follow-ups"** — item 1 ("Extend unified warning to list_projects / list_folders / list_tags") is now architecturally obsolete. If/when Flo touches that SUMMARY for the supersession header, strike-through or delete follow-up #1. Items #2 (`_version.py` RUF022) and #3 (move todo to completed) are unrelated to warning design and remain valid.
- **Docstring trail at `src/omnifocus_operator/service/service.py:619–638`** (`_is_empty_scope_query`) — references "G2/G3" short-circuit. After kd0, the short-circuit itself still exists (nothing in the todo removes it — the `empty_result` path at line 432 stays; only the warning decoration logic changes). Flag: no edit needed, but planner should NOT conflate "short-circuit" deletion with the warning-surface simplification.

## What explicitly STAYS

- **`is_non_default` (entire function + export + test class).** Live in `service/domain.py::check_filtered_subtree` and the full `TestIsNonDefault` class in `test_service_domain.py:1357–1412`. DO NOT delete.
- **`UNSET` / `_Unset` / `is_set` / `unset_to_none`.** All four have callers across `service.py` unrelated to the warning surface. DO NOT remove from the `contracts.base` import on line 34.
- **`ListTasksQuery` import (service.py:57).** Used in the public method signature (`list_tasks`), the pipeline's `execute` signature, and elsewhere. DO NOT remove.
- **`_is_empty_scope_query` method (service.py:618–638)** and its call site at line 427. The short-circuit-to-empty path is a Phase 57-04 G2/G3 correctness fix — unrelated to the warning-decoration logic. The todo's `_emit_empty_result_warning` rewrite keeps calling it (`self._emit_empty_result_warning(empty_result)` at line 438 and `self._emit_empty_result_warning(await self._delegate())` at line 440). Both call sites stay; the inner helper is what simplifies.
- **`FILTER_DID_YOU_MEAN` constant + its DYM-standalone text in `warnings.py`.** kd0 does NOT revisit the DYM rewording; the DYM still composes with the new static warning (per todo §Consequences). DO NOT change.
- **`check_filter_resolution` in `service/domain.py` (lines 555–590).** Its `[]`-return branch for no-match-no-suggestion is what lets the unified warning cover the silent case. kd0 doesn't touch domain.py — the wiring from "resolver returns empty" → "_is_empty_scope_query returns True" → "_emit_empty_result_warning appends the static text" is unchanged. Only the LAST step's implementation collapses.
- **`PARENT_PROJECT_COMBINED_WARNING`, `FILTERED_SUBTREE_WARNING`, `LIST_TASKS_INBOX_PROJECT_WARNING`, `PARENT_RESOLVES_TO_PROJECT_WARNING`.** All live. Composition with the new static warning is verified by `test_intersection_empty_fires_two_filter_warning` (if kept).
- **Golden master tests infra.** Untouched (no snapshot captures the warning text).
- **`.planning/quick/260424-j63-.../CONTEXT.md` + `PLAN.md`.** Historical design record; supersession note goes on `SUMMARY.md` only.
