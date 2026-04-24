---
created: 2026-04-24T13:26:54.704Z
title: Simplify empty-result warning to single static message
area: service
files:
  - src/omnifocus_operator/agent_messages/warnings.py:198-208,222
  - src/omnifocus_operator/service/service.py:438-440,640-678
  - tests/test_list_pipelines.py (TestEmptyResultWarning class, ~9 cases)
  - .planning/quick/260424-j63-unify-empty-result-warning-surface/260424-j63-SUMMARY.md (supersession note)
  - .planning/phases/57-parent-filter-filter-unification/57-UAT.md (Post-Resolution Gap Audit)
---

## Problem

Live-probe verification of the newly-shipped unified empty-result warning (quick task 260424-j63, commits `59cc62ec` + `a7aded6a` + `d44e4742`) surfaced that `_active_filter_names` incorrectly treats `limit`, `offset`, `include`, `only` as filters. These are pagination / response-shaping controls, not filters.

Concrete live repro against real OmniFocus:

```
list_tasks(project="Migrate to Omnifocus", parent="Build and Ship OmniFocus", limit=5)
→ warnings: [
    "Both 'project' and 'parent' filters are set. ...",
    "The combination of filters 'limit', 'parent', 'project' resolved to zero tasks. No results."
  ]
```

`limit` is listed as a filter. Same category risk for `offset`, `include`, `only`.

The 9-case test matrix missed this because every case constructs `ListTasksQuery(...)` directly with `limit` at its default (50). Live callers passing non-default `limit` / `offset` hit the bug.

While discussing the fix, Flo recognized the parameterization itself is low-value complexity. The agent already sees `items: []` in the response — re-enumerating the filters they just sent is redundant noise. A static nudge is enough.

## Solution

Collapse to a single static warning. No filter-enumeration, no `is_non_default` iteration, no alias lookups, no alphabetical sort, no exclusion-set maintenance.

### One constant (warnings.py)

```python
EMPTY_RESULT_WARNING = "The filters you selected didn't yield any results. Try widening the search."
```

Final wording is Flo's call — his exact draft above, or a minor tweak like "Try widening or removing filters".

### Collapsed helper (service.py)

```python
def _emit_empty_result_warning(self, result: ListResult[Task]) -> ListResult[Task]:
    if result.items:
        return result
    warnings = [*(result.warnings or []), EMPTY_RESULT_WARNING]
    return result.model_copy(update={"warnings": warnings})
```

### Deletes

- `EMPTY_RESULT_WARNING_SINGLE` constant
- `EMPTY_RESULT_WARNING_MULTI` constant
- `_active_filter_names` helper (entire function, ~20 LOC)
- All `is_non_default` iteration / `model_fields` alias lookup / alphabetical sort / exclusion-set thinking

### Consequences

- `limit`/`offset`/`include`/`only` bug disappears by construction — nothing enumerates fields anymore.
- "Zero filters + empty DB" edge case — warning fires anyway. Acceptable per Flo's earlier stance ("almost impossible to get zero results without any filter, not worried about the edge case").
- `FILTER_DID_YOU_MEAN` composition unchanged — DYM fires independently on fuzzy candidates; composes fine with the new simpler warning.

## Blast radius (measured)

- `src/omnifocus_operator/agent_messages/warnings.py` — -2 constants, +1 (+ update header comment)
- `src/omnifocus_operator/service/service.py` — delete `_active_filter_names` (~20 LOC), simplify `_emit_empty_result_warning` (~6 LOC)
- `tests/test_list_pipelines.py` — delete ~5 of the 9 `TestEmptyResultWarning` matrix cases (ordering lock, camelCase alias, default-availability, zero-filters-skip, single-vs-multi format). Keep: empty → warning verbatim, non-empty → no warning, empty + DYM → both warnings compose.
- `tests/test_service_domain.py` — no changes expected (DYM path unchanged)

Net: roughly **~70 LOC smaller** than the shipped 260424-j63 version.

No contract changes, no repo changes — service layer only.

## Time estimate

~15 min.

## Supersession note

Quick task 260424-j63's `SUMMARY.md` should be annotated with a "SUPERSEDED by quick task <this-one>" header once this lands, so the evolution trail shows:

1. 57-04 shipped narrow `EMPTY_SCOPE_INTERSECTION_WARNING` (project ∩ parent disjoint only)
2. 260424-j63 generalized to parameterized `EMPTY_RESULT_WARNING_{SINGLE,MULTI}` (any filter combination)
3. This todo simplifies to static `EMPTY_RESULT_WARNING` (live-probe surfaced `limit` bug; parameterization judged low-value)

## UAT trail

When this lands, append a note to `.planning/phases/57-parent-filter-filter-unification/57-UAT.md`'s "Post-Resolution Gap Audit" section recording this second iteration. The live probe that surfaced the `limit` bug is the trigger.

## Session-local probe evidence

Live probes run against real OmniFocus on 2026-04-24 during the post-resolution gap audit:

```
Probe A: list_tasks(project="Migrate to Omnifocus", parent="Build and Ship OmniFocus", limit=5)
  → items: []
  → warnings: [
      "Both 'project' and 'parent' filters are set. ...",  (WARN-03, correct)
      "The combination of filters 'limit', 'parent', 'project' resolved to zero tasks. No results."  (BUG: limit listed)
    ]

Probe B: list_tasks(parent="NonexistentTaskNameThatShouldNotResolveXYZ", limit=5)
  → items: []
  → warnings: [
      "The combination of filters 'limit', 'parent' resolved to zero tasks. No results."  (BUG: limit listed, nothing else even set)
    ]
```
