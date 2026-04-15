# OmniFocus Inheritance Semantics

Empirical study of how OmniFocus computes `effective*` values from task hierarchy.
Determines the correct aggregation strategy for each inherited field.

## Why This Exists

Phase 53.1 (True Inherited Fields) introduced `_walk_one` in `service/domain.py` to
compute truly inherited values. The initial implementation used `min` for all date fields.
During UAT, we discovered this is wrong for defer (should be max), planned (should be
first-found/override), and likely drop/completion (should be first-found/override).

This deep-dive documents the empirical tests that determined the correct semantics.

## Key Finding: Three Semantic Families

| Family | Fields | Rule |
|--------|--------|------|
| Constraint (min) | `dueDate` | Tightest deadline wins |
| Constraint (max) | `deferDate` | Latest block wins |
| Override | `plannedDate`, `dropDate`, `completionDate` | Nearest ancestor wins |
| Boolean OR | `flagged` | Any-True propagates down |

## Files

- `FINDINGS.md` — Complete test data, raw outputs, verification tables, confidence levels
- `README.md` — This file

## Confidence Levels

- **High:** due, defer, planned, flagged — verified with 5-level hierarchy, multiple data points
- **Medium:** drop — verified with 4 tests including decisive blocker-sibling test
- **Low:** completion — only one test, all timestamps identical, needs follow-up

## Related

- `service/domain.py` — `_walk_one` function that implements inheritance
- Phase 53.1 plans in `.planning/phases/53.1-true-inherited-fields/`
- `docs/architecture.md` — may need updating with inheritance semantics
