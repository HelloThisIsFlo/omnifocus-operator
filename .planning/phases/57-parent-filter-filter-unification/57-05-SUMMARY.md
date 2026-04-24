---
phase: 57-parent-filter-filter-unification
plan: 05
subsystem: api
tags: [list-tasks, filtered-subtree-warning, availability, agent-warnings, value-aware-predicate]

# Dependency graph
requires:
  - phase: 57-parent-filter-filter-unification
    provides: "Plan 57-04 foundation (candidate_task_ids + pinned_task_ids contract, reworded warnings, TestSubtreePruningFieldsDrift ready to broaden)"
provides:
  - "New public helper: `is_non_default(model, field_name)` on contracts/base.py — value-aware predicate handling Patch (UNSET sentinel) and regular fields (Pydantic model_fields default / default_factory)"
  - "`availability` added to `_SUBTREE_PRUNING_FIELDS`: first non-Patch pruning field"
  - "`check_filtered_subtree` uses `is_non_default` for the pruning iteration (scope predicate still uses `is_set`)"
  - "Broadened `TestSubtreePruningFieldsDrift`: reference set flips from `_PATCH_FIELDS` to `ListTasksQuery.model_fields`; new drift test catches typos on both Patch and regular classified fields"
  - "G4 closure: non-default `availability` (e.g. `['available']`, `['blocked']`, `[]`) with scope filter fires FILTERED_SUBTREE_WARNING; default `['remaining']` still does not (D-13 preserved)"
affects: ["v1.4.1 gap closure (Phase 57 wave 4 complete: G1/G2/G3 via 57-04, G4 via 57-05)", "Future non-Patch filter-semantic fields can reuse `is_non_default`"]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Value-aware contract predicate: dispatch on field type (Patch sentinel vs. regular-with-default vs. default_factory) using Pydantic `model_fields[name].default` + `PydanticUndefined` sentinel"
    - "Stdlib list equality (`==`) as the default-comparison contract for mutable-default fields; order-sensitivity documented as intentional"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/contracts/base.py — imports BaseModel + PydanticUndefined; adds `is_non_default` helper after `is_set`; extends `__all__`"
    - "src/omnifocus_operator/service/domain.py — imports `is_non_default`; comment-block rework for `_SUBTREE_PRUNING_FIELDS`; `availability` added to tuple; `check_filtered_subtree` switches pruning predicate to `is_non_default`"
    - "tests/test_service_domain.py — imports `is_non_default`; new `TestIsNonDefault` class (8 cases); `TestCheckFilteredSubtree` extended with 9 G4 matrix cases (old availability tests removed/replaced); `TestSubtreePruningFieldsDrift` broadened to `model_fields` reference + new `test_every_classified_field_exists_on_query`"
    - "tests/test_list_pipelines.py — old `test_filtered_subtree_warning_availability_only_does_not_fire` flipped to `test_filtered_subtree_warning_project_and_narrower_availability_fires` (G4 lock, replays UAT-57 Test 9 probe (c)); new negative tests `test_filtered_subtree_warning_project_and_default_availability_does_not_fire` and `test_filtered_subtree_warning_availability_only_no_scope_does_not_fire`"

key-decisions:
  - "Introduce `is_non_default` at the contract layer (contracts/base.py). Alternatives rejected: ad-hoc per-field if-else in domain (doesn't scale); hardcoded 'availability' special case (invites drift as more non-Patch filter fields are added). Value-aware predicate generalizes cleanly."
  - "Read default via Pydantic `model_fields[name].default` (Pydantic stores the literal list for `Field(default=[...])`). Handle `default_factory` path by calling the factory once; handle truly-required fields by returning True (unset would fail validation). Single source of truth for defaults."
  - "List equality is order-sensitive (stdlib `==`) -- intentional contract. For the current single-element default `[REMAINING]`, ordering is moot. A future multi-element default reorder at the contract level would be API-breaking (schema version bump), not a runtime concern. CI drift test gates any classification/default mismatch."
  - "Scope predicate (`is_set` on `project`/`parent`) unchanged. Both are Patch fields where `is_set` is the correct and more specific test; switching them to `is_non_default` would be functionally equivalent but muddies intent."
  - "Drop the no-op `test_is_non_default_regular_field_reordered_default` test (A4 fix from planning review) -- reordering a single-element default `[REMAINING]` is a no-op. Document order-sensitivity in the helper docstring instead."
  - "Replace invalid plan-matrix value `AvailabilityFilter.COMPLETED` (which doesn't exist -- the filter enum has only AVAILABLE/BLOCKED/REMAINING) with a valid multi-element combination `[REMAINING, AVAILABLE]`. Test semantics preserved (multi-value != default)."

patterns-established:
  - "Value-aware predicates at the contract layer: when a classification spans Patch and non-Patch fields, the predicate must dispatch on field type. `is_non_default` is the template for future additions (e.g. if `include` or `limit` classifications grow)."
  - "`ListTasksQuery.model_fields.keys()` as the drift-test reference set for classifications that touch both Patch and non-Patch fields. Replaces `_PATCH_FIELDS` as the authoritative field-membership source."

requirements-completed: [WARN-01]

# Metrics
duration: 6min
completed: 2026-04-24
---

# Phase 57-05: G4 Gap Closure — Value-Aware FILTERED_SUBTREE_WARNING for `availability`

**Non-default `availability` (`['available']`, `['blocked']`, `[]`, multi-value) combined with a scope filter now fires FILTERED_SUBTREE_WARNING via a new value-aware predicate `is_non_default`. Default `['remaining']` (implicit or explicit) still does not fire — D-13's "don't spam on the default" intent preserved.**

## Performance

- **Duration:** ~6 min
- **Started:** 2026-04-24T00:41:09Z
- **Completed:** 2026-04-24T00:47:20Z
- **Tasks:** 1 (TDD: RED → GREEN)
- **Files modified:** 4

## Accomplishments

- **G4 closed** (UAT-57): agents combining `project` or `parent` with non-default `availability` now receive FILTERED_SUBTREE_WARNING — the same pedagogical hint they get for other pruning filters (`flagged`, `tags`, date filters, etc.). Agents using only the default `availability=['remaining']` (explicitly or implicitly) still do not see the warning, preserving D-13's original intent.
- **`is_non_default` helper landed** on `contracts/base.py`. Value-aware predicate: dispatches on field type (Patch → is_set equivalence; regular-with-default → stdlib `!=`; default_factory → factory call baseline; required → always True). Documented in docstring including order-sensitivity note.
- **`_SUBTREE_PRUNING_FIELDS` classification extended** to include `availability`. The "Explicitly NOT listed" comment block updated to drop the `availability` item and explain the value-aware predicate that now handles the default-vs-non-default distinction.
- **Drift test broadened**: reference set flips from `_PATCH_FIELDS` to `ListTasksQuery.model_fields`. New `test_every_classified_field_exists_on_query` explicitly catches typos (e.g. `"avilability"`) for both Patch and non-Patch classified fields.
- **Pipeline-level lock test** replays the exact UAT-57 Test 9 probe (c) scenario: `ListTasksQuery(project="Work", availability=[AVAILABLE])` → FILTERED_SUBTREE_WARNING fires. Plus negative tests for default-availability + no-scope cases.

## Task Commits

1. **Task 1: Add `is_non_default` helper + update `check_filtered_subtree` (TDD RED → GREEN)** — `8bca6e0e` (fix)

TDD flow:
- RED: added `TestIsNonDefault` (8 cases), `TestCheckFilteredSubtree` G4 matrix (9 new cases), broadened drift tests, pipeline G4 lock test. Initial run failed at import (`is_non_default` not defined) and on pruning assertions.
- GREEN: added `is_non_default` to contracts/base.py, extended `__all__`, imported into service/domain.py, added `availability` to `_SUBTREE_PRUNING_FIELDS`, switched predicate to `is_non_default`. Full suite green.

Committed as a single TDD round (RED/GREEN in one atomic commit) because the tests and implementation are tightly coupled and the suite needs to remain atomic on main.

## Files Modified

- `src/omnifocus_operator/contracts/base.py` — imports `BaseModel` from `pydantic` and `PydanticUndefined` from `pydantic_core`; adds `is_non_default` helper immediately after `is_set`; extends `__all__`.
- `src/omnifocus_operator/service/domain.py` — imports `is_non_default`; rewrites the `_SUBTREE_PRUNING_FIELDS` comment block (explains value-aware predicate + removes the deferred-availability note); adds `"availability"` to the tuple; `check_filtered_subtree` uses `is_non_default(query, f)` for pruning iteration (scope `is_set` check unchanged).
- `tests/test_service_domain.py` — imports `is_non_default`; new `TestIsNonDefault` class with 8 cases (Patch UNSET/True/False + regular-field default implicit/explicit, different, empty, multi-value); `TestCheckFilteredSubtree` loses two old tests (`test_project_with_availability_does_not_fire`, `test_availability_only_does_not_fire`) and gains 9 G4 matrix cases (implicit default no-fire, explicit default no-fire, narrower fires, BLOCKED fires, empty fires, multi-value fires, narrower+flagged fires once, availability alone no-fire, parent+narrower fires); `TestSubtreePruningFieldsDrift` broadened (new drift test + old drift test now references `ListTasksQuery.model_fields`).
- `tests/test_list_pipelines.py` — old `test_filtered_subtree_warning_availability_only_does_not_fire` (which asserted the old behavior) replaced with:
  - `test_filtered_subtree_warning_project_and_narrower_availability_fires` (G4 lock, replays UAT-57 Test 9 probe (c))
  - `test_filtered_subtree_warning_project_and_default_availability_does_not_fire` (D-13 regression guard at pipeline layer)
  - `test_filtered_subtree_warning_availability_only_no_scope_does_not_fire` (scope predicate still gates)

## Decisions Made

See `key-decisions` in frontmatter. Highlights:

- **Value-aware predicate at the contract layer.** `is_non_default` generalizes cleanly across Patch and non-Patch fields. Reads the default from Pydantic's `model_fields` — no hardcoding of defaults, single source of truth.
- **List equality is order-sensitive by stdlib contract.** Documented in the helper's docstring as intentional. For the current single-element `[REMAINING]` default, ordering is moot. Future multi-element defaults are an API-breaking change territory (schema version bump).
- **Scope predicate unchanged.** `is_set(query.project) or is_set(query.parent)` stays: both are Patch fields, `is_set` is the correct and more specific test.
- **`default_factory` handled defensively** even though the current non-Patch pruning field (`availability`) uses literal `default`. Future additions may use `default_factory` (e.g. `list[X] = Field(default_factory=list)`); helper handles the path correctly by calling the factory once to produce a fresh baseline.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Plan matrix referenced non-existent `AvailabilityFilter.COMPLETED`**
- **Found during:** Step 1 (RED, running `TestIsNonDefault.test_is_non_default_regular_field_superset`).
- **Issue:** Plan's coverage matrix and the corresponding test used `AvailabilityFilter.REMAINING, AvailabilityFilter.COMPLETED` as a "superset" example, but `AvailabilityFilter` has only `AVAILABLE`, `BLOCKED`, `REMAINING` (the lifecycle `COMPLETED` lives on the separate `LifecycleDateFilter` / core `Availability` enum). Test raised `AttributeError` at collection.
- **Fix:** Replaced both occurrences (`TestCheckFilteredSubtree.test_project_with_superset_availability_fires` renamed to `test_project_with_multi_value_availability_fires`; `TestIsNonDefault.test_is_non_default_regular_field_superset` renamed to `test_is_non_default_regular_field_multi_value`) with the valid multi-value list `[REMAINING, AVAILABLE]`. Semantic preserved: multi-element list != single-element default list, so `is_non_default` returns True and the warning fires.
- **Files modified:** `tests/test_service_domain.py`
- **Verification:** `uv run pytest tests/test_service_domain.py::TestIsNonDefault -q` → 8 passed.
- **Committed in:** `8bca6e0e` (Task 1 commit, alongside the rest of the GREEN changes).

### Flagged-to-Orchestrator

None.

---

**Total deviations:** 1 auto-fixed (Rule 1: invalid enum member in the plan's matrix). No scope creep. The rename (superset → multi_value) is semantically equivalent and preserves the test's intent.

## Issues Encountered

- `AvailabilityFilter.COMPLETED` does not exist (see Deviation 1). Caught at the first RED run — exactly the kind of issue TDD is designed to surface immediately.

## Threat Flags

None — this plan extends an existing warning's coverage predicate. No new network endpoints, auth paths, file access patterns, or schema changes introduced.

## Known Stubs

None. All data paths are wired end-to-end — the G4 fix takes immediate effect for every pipeline call through `check_filtered_subtree`.

## TDD Gate Compliance

Single-task TDD plan. RED → GREEN executed atomically within one commit (`8bca6e0e`) because tests and implementation are tightly coupled (import-level RED + runtime-level RED both needed the GREEN landing to turn green). Prior drift tests ensured existing classifications stayed honest throughout.

Gate sequence verified in git log:
1. Plan 57-05 commit is a `fix(57-05): ...` (GREEN); RED state was verified interactively before landing (see Issues Encountered / Deviation 1 for evidence that tests started red).
2. No subsequent REFACTOR commit needed — the implementation is minimal and the docstring captures the contract.

**Note on TDD commit granularity:** Because this is a small atomic change (1 helper + 1 predicate switch + its tests), splitting into RED/GREEN commits would produce an empty-state commit that breaks `main` between them. Project convention per feedback log allows merging TDD phases when splitting adds no value — applied here.

## Grep Invariants (Before/After)

| Invariant | Before | After | Target |
|-----------|--------|-------|--------|
| `def is_non_default` in `src/omnifocus_operator/contracts/base.py` | 0 | **1** | 1 |
| `"is_non_default"` in `__all__` | 0 | **1** | 1 |
| `"availability",` inside `_SUBTREE_PRUNING_FIELDS` | 0 | **1** | 1 |
| `is_set(getattr(query` in `service/domain.py` (old predicate) | 1 | **0** | 0 |
| `is_non_default` occurrences in `service/domain.py` | 0 | **4** (import + 3 call sites in code/docstring) | ≥ 2 |
| `class TestIsNonDefault` in `tests/test_service_domain.py` | 0 | **1** | 1 |
| `test_every_classified_field_exists_on_query` in `tests/test_service_domain.py` | 0 | **1** | 1 |
| `test_filtered_subtree_warning_project_and_narrower_availability_fires` | 0 | **1** | 1 |
| `test_is_non_default_regular_field_reordered_default` (A4 drop) | 0 | **0** | 0 |

## Self-Check

Verified via `ls` / `git log` / `grep`:

- `src/omnifocus_operator/contracts/base.py` present, contains `def is_non_default`, imports `BaseModel` and `PydanticUndefined`, extends `__all__`.
- `src/omnifocus_operator/service/domain.py` present, imports `is_non_default`, `"availability"` is inside `_SUBTREE_PRUNING_FIELDS`, `check_filtered_subtree` uses `is_non_default(query, f)` and no longer calls `is_set(getattr(query, f))`.
- `tests/test_service_domain.py` present, contains `class TestIsNonDefault` (8 tests), G4 matrix cases in `TestCheckFilteredSubtree`, broadened `TestSubtreePruningFieldsDrift` with `test_every_classified_field_exists_on_query`.
- `tests/test_list_pipelines.py` present, contains `test_filtered_subtree_warning_project_and_narrower_availability_fires`.
- Commit `8bca6e0e` present in `git log`.
- Full suite: `uv run pytest --no-cov -q` → **2555 passed**.
- `uv run pytest tests/test_output_schema.py --no-cov -q` → **35 passed** (MANDATORY per CLAUDE.md).

## Self-Check: PASSED

## Next Phase Readiness

Phase 57 (parent-filter-filter-unification) is now fully closed:
- **G1 (anchor preservation)** — 57-04
- **G2 (empty-scope cross-path divergence)** — 57-04
- **G3 (no-match resolver fallback)** — 57-04
- **G4 (availability under-alerting)** — 57-05 (this plan)

`is_non_default` is a reusable contract-layer helper. Future non-Patch filter-semantic fields (e.g. if `completed`/`dropped` are ever reclassified, or if new regular-default filter fields are added) can drop straight into `_SUBTREE_PRUNING_FIELDS` without needing a new predicate.

Downstream plans that may want to consume `is_non_default`:
- Future agent-warning logic that needs to distinguish "user passed the default" from "user left the field unset" for other classifications.
- Any new regular-default filter-semantic field on `ListProjectsQuery`, `ListTagsQuery`, etc. — the same pattern applies at those boundaries.

---
*Phase: 57-parent-filter-filter-unification*
*Plan: 05*
*Completed: 2026-04-24*
