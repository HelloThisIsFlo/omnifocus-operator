---
status: clean
phase: 57
phase_name: parent-filter-filter-unification
reviewed: 2026-04-24
depth: standard
files_reviewed: 22
findings:
  critical: 0
  warning: 0
  info: 5
  total: 5
---

# Phase 57: Code Review Report

**Reviewed:** 2026-04-24
**Depth:** standard
**Files Reviewed:** 22
**Status:** clean (5 informational observations)

## Summary

Reviewed the full Phase 57 surface — `parent` filter + filter unification, executed across 4 waves (Plans 01–03 + gap-closure 04–05). All 10 production files and 12 test files scanned for bugs, security, and quality issues.

**Verdict:** No critical bugs or security vulnerabilities. No warnings. 5 informational observations, all minor design nits rather than defects. The phase is ready to ship as-is.

**Focus-area verdicts:**

- **OR-with-pinned WHERE clause correctness** — hybrid SQL and bridge_only Python agree by construction. Locked by `test_pinned_cross_path_equivalence` and `test_pinned_bypasses_pruning_cross_path` in `tests/test_cross_path_equivalence.py`. No SQL injection risk: all pinned IDs go through `?` placeholders (line 303 in `query_builder.py`), never string interpolation.
- **Anchor filtering through project scope** — correctly enforced at `service/service.py:601-604`. When `project_scope` is set, `anchors = anchors & self._project_scope` intersects anchors against project scope before assignment. `test_parent_anchor_outside_project_scope_not_preserved` locks this.
- **`is_non_default` helper** — correctly handles all four field-type cases (Patch sentinel, literal default, `default_factory`, required field). Pydantic v2 stores the literal `[AvailabilityFilter.REMAINING]` on `FieldInfo.default` per-class (not per-instance), so no shared-mutable-default bug.
- **Empty-scope short-circuit** — correctly distinguishes `None` ("filter not set") from `[]` ("filter set, resolved to zero") at both `candidate_task_ids` and `tag_ids` layers.
- **Warning wording** — `grep -rn "skipped" src/` returns zero matches in the touched files. Rewording is clean.
- **SAFE-01/02 compliance** — all `RealBridge` references are in the class definition, the factory, and the dedicated safety tests. No phase-57 code path touches it.

---

## Info

### IN-01: `_is_empty_scope_query` conflates two short-circuit triggers under one predicate

**File:** `src/omnifocus_operator/service/service.py:620-642`

**Issue:** The method fuses two logically independent short-circuit conditions — "scope collapsed" and "tags no-match" — behind a single `True` return. When it fires, the caller has no way to know *which* condition tripped, which matters because `_emit_empty_intersection_warning_if_applicable` is a separate method that runs *before* the short-circuit and only fires for one of the two triggers.

Today this works because `_emit_empty_intersection_warning_if_applicable` also inspects `candidate_task_ids == []` itself (duplicate check at lines 654-658), so the warning-vs-short-circuit semantics stay aligned. But the duplicated predicate is a coupling smell: if someone changes one without the other, the warning surface diverges from the short-circuit surface silently.

**Fix (optional, for maintainability):** Split the two triggers into named helpers (e.g. `_scope_collapsed_to_empty()` + `_tags_resolved_to_empty()`) and have both `_is_empty_scope_query` and `_emit_empty_intersection_warning_if_applicable` call the scope-collapsed helper.

### IN-02: `is_non_default` docstring is slightly stronger than reality

**File:** `src/omnifocus_operator/contracts/base.py:73-117`

**Issue:** The docstring says the predicate reads the default from Pydantic's `model_fields` to provide a "single source of truth for defaults." True for direct field access, but Pydantic v2 can apply `@field_validator(..., mode="before"|"after")` transformations to the default on instance construction. For `ListTasksQuery`, no validator mutates `availability` today, so `getattr(instance, "availability") == type(instance).model_fields["availability"].default` holds. But a future validator that normalizes `availability` (e.g. dedup, sort) could make the comparison misclassify.

Not a bug today — just an implicit assumption worth flagging in the docstring.

**Fix (documentation only):** Add a caveat noting that a `@field_validator` that transforms the value on construction can make the stored value differ from the declared default even when the caller passed the default literal. The drift test at CI catches classification mismatches; it does NOT catch validator-vs-default divergence.

### IN-03: `_resolve_parent` duplicates the project-id membership check from `check_filter_resolution`

**File:** `src/omnifocus_operator/service/service.py:536-544`

**Issue:** The method rebuilds `task_ids = {t.id for t in self._tasks}` and `project_ids = {p.id for p in self._projects}` inline every time. `_resolve_scope_filter` already has access to `self._tasks`/`self._projects` via `self`, so the sets could be computed once per pipeline. Not measurable at this scale (few hundred tasks), but marginally redundant.

**Fix (optional):** Hoist into `_ListTasksPipeline` setup in `execute()`:
```python
self._task_id_set = {t.id for t in self._tasks}
self._project_id_set = {p.id for p in self._projects}
```
Then `_resolve_parent` uses `self._task_id_set` and `self._project_id_set`.

### IN-04: Degenerate pinned-only branch loses the safety of the availability AND-chain

**File:** `src/omnifocus_operator/repository/hybrid/query_builder.py:302-312`

**Issue:** When `pinned` is set and `conditions` is empty (degenerate case), the SQL degenerates to:
```
WHERE pi.task IS NULL AND t.persistentIdentifier IN (<pinned>)
```
This means pinned tasks bypass the default availability filter (`[AVAILABLE, BLOCKED]`) — a completed/dropped pinned task would be returned. The docstring at line 297 explicitly says "The pinned branch bypasses all other predicates, honoring FILTERED_SUBTREE_WARNING's 'always included' promise" — so this is intentional.

However, `ListTasksRepoQuery` always has a non-empty `availability` default `[AVAILABLE, BLOCKED]`, which always contributes an availability clause to `conditions`. The "no other filters" branch at line 310-312 is thus unreachable under normal flow — `test_pinned_task_ids_direct_or_shape` explicitly notes "the OR wrapper [is] present because default availability fills the candidate branch."

Two subtle points:
1. If a direct caller somehow constructed a `ListTasksRepoQuery` with `availability=[]`, the dead branch would fire and pinned tasks would be returned unconditionally. Today this is prevented only by the service layer's `expand_availability` never producing `[]` — but there's no assertion at the repo boundary.
2. The "pinned bypasses availability" semantic is correct by design, but test coverage for it is indirect. A dedicated test for "pinned completed task is returned when `pinned_task_ids` set" would lock the invariant.

**Fix (optional, defense-in-depth):** Add a regression test locking the degenerate-branch semantics.

### IN-05: `_emit_empty_intersection_warning_if_applicable` uses `== []` for empty-list check

**File:** `src/omnifocus_operator/service/service.py:654`

**Issue:** `self._repo_query.candidate_task_ids == []` works correctly, but is slightly idiosyncratic — the more idiomatic form is the length-and-not-None check used in `_is_empty_scope_query` (line 636: `q.candidate_task_ids is not None and len(q.candidate_task_ids) == 0`). If `candidate_task_ids` ever became `frozenset[str] | None`, `== []` would return `False` even for empty inputs.

**Fix (optional):** Align the two checks for consistency.

---

## Cross-Cutting Observations (not findings — just context)

- **Coverage is thorough.** The G1/G2/G3/G4 gap-closure tests are load-bearing regression guards. `TestParentAnchorPreservation` (8 cases), `TestEmptyScopeShortCircuit` (3 cases), `TestFilterNoMatchWarningText` (2 cases), and `TestIsNonDefault` (8 cases) together lock every edge case UAT-57 surfaced.
- **Cross-path equivalence is enforced by construction.** The service layer short-circuits before either repo sees `candidate_task_ids=[]`, eliminating the hybrid-vs-bridge divergence that caused G2. `test_pinned_cross_path_equivalence` and `test_pinned_bypasses_pruning_cross_path` cover the OR-with-pinned semantic end-to-end.
- **No SQL injection surface.** `pinned_task_ids` uses `?` placeholders at line 303 of `query_builder.py`. The `sorted()` at line 588 of `service.py` is deterministic-ordering, not a sanitizer, but sanitization isn't needed — values never touch the SQL string.
- **Em-dash U+2014 fidelity preserved.** `FILTERED_SUBTREE_WARNING` at `warnings.py:187-192` has the verbatim em-dash from the spec. `test_verbatim_text` + the grep gate in 57-03 lock this byte-for-byte.

---

## Files Reviewed

- `src/omnifocus_operator/agent_messages/descriptions.py`
- `src/omnifocus_operator/agent_messages/warnings.py`
- `src/omnifocus_operator/contracts/base.py`
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py`
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py`
- `src/omnifocus_operator/repository/hybrid/query_builder.py`
- `src/omnifocus_operator/service/domain.py`
- `src/omnifocus_operator/service/resolve.py`
- `src/omnifocus_operator/service/service.py`
- `src/omnifocus_operator/service/subtree.py`
- `tests/doubles/bridge.py`
- `tests/golden_master/normalize.py`
- `tests/test_bridge_contract.py`
- `tests/test_bridge_only_repository.py`
- `tests/test_cross_path_equivalence.py`
- `tests/test_hybrid_repository.py`
- `tests/test_list_contracts.py`
- `tests/test_list_pipelines.py`
- `tests/test_query_builder.py`
- `tests/test_service_domain.py`
- `tests/test_service_resolve.py`
- `tests/test_service_subtree.py`

---

*Reviewer: gsd-code-reviewer (standard depth)*
*Findings: 0 critical, 0 warnings, 5 info*
