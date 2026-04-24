---
created: 2026-04-24T11:47:21.888Z
title: Unify empty-result warning surface
area: service
files:
  - src/omnifocus_operator/service/service.py:425-442,620-660
  - src/omnifocus_operator/service/domain.py:565-595
  - src/omnifocus_operator/agent_messages/warnings.py:160,204,222
  - tests/test_list_pipelines.py:2230,2282,2297,2522
  - tests/test_service_domain.py:1118-1131
  - .planning/phases/57-parent-filter-filter-unification/57-UAT.md (Post-Resolution Gap Audit section)
---

## Problem

Surfaced during the Phase 57 post-resolution gap audit on 2026-04-24.

G2 (from UAT-57) shipped `EMPTY_SCOPE_INTERSECTION_WARNING` only for the `project + parent` disjoint case. Single-scope-resolves-to-empty stays silent — e.g., `list_tasks(parent="EmptyProject")` returns `items=[], warnings=None`. The agent can't tell whether the result is empty because the filter matched nothing or because it matched an empty entity.

Flo's decision: the silence is weird. Instead of adding another narrow sibling warning, unify the whole empty-result warning surface into one parameterized warning. Retire the two current narrow warnings.

## Solution

Two-layer model:

**Layer 1 — unified empty-result warning.** Fires when `items == []` AND at least one filter is non-default. Text parameterized by active-filter count:
- 1 filter:  `"The 'X' filter resolved to zero tasks. No results."`
- 2+ filters: `"The combination of filters 'X', 'Y', 'Z' resolved to zero tasks. No results."`

Zero-filter case (no filters set AND empty result): skip the warning. Per Flo: "almost impossible to get zero results without any filter — not worried about the edge case."

**Layer 2 — did-you-mean.** Unchanged in role; fires on top when an unresolved name has fuzzy candidates. Needs small standalone reword (currently designed to be appended to `FILTER_NO_MATCH`).

### Retired
- `EMPTY_SCOPE_INTERSECTION_WARNING` (subsumed by Layer 1)
- `FILTER_NO_MATCH` (subsumed — the "no name matched" case now just looks like "zero result" with DYM suggestions layered on)

### Active-filter detection
Reuse `is_non_default` from G4 (see Phase 57-05 SUMMARY). Already handles Patch vs regular-default fields uniformly. Good dogfood of the new helper.

### Implementation sketch
- Add `EMPTY_RESULT_WARNING` constant in `agent_messages/warnings.py` with `{filters}` placeholder
- Add `_active_filter_names(query) -> list[str]` helper in service layer, using `is_non_default` on every filter field of `ListTasksQuery`
- Single emit point in `execute()` post-short-circuit / post-delegate: `if not result.items and active_filters: append EMPTY_RESULT_WARNING.format(filters=...)`
- Remove `_emit_empty_intersection_warning_if_applicable` helper (service.py:642-660)
- Reword `FILTER_DID_YOU_MEAN` to stand alone without `FILTER_NO_MATCH` preceding it
- Drop `FILTER_NO_MATCH` path from `check_filter_resolution` in `service/domain.py`

### Blast radius (measured)
- Src: 3 files (service.py, domain.py, warnings.py)
- Tests: 2 files (test_list_pipelines.py, test_service_domain.py)
- Existing tests to flip: ~5 (`TestEmptyScopeShortCircuit`, `TestFilterNoMatchWarningText`, the domain test_no_match_* cluster)
- New tests to add: ~8 (matrix: scope-empty / intersection-empty / pruning-empty / no-match / combos / default-vs-non-default / zero-filters-skip / DYM standalone)
- Total diff estimate: ~200 LOC
- No contract changes, no repo changes — service layer only

### Time estimate
~30–45 min including tests.

### UAT audit trail
When picked up: record the decision + link back to this todo in the UAT's "Post-Resolution Gap Audit (2026-04-24)" section so the supersession of G2's partial fix is preserved.

### Open questions for implementer
- Pedagogical ordering of filter names in the text (e.g. scope first, then pruning, then modifier)? Pick one deterministic order and lock it in a test.
- Should `project="$inbox"` resolving to zero tasks fire the warning? (Current short-circuit catches this; likely yes for consistency.)
