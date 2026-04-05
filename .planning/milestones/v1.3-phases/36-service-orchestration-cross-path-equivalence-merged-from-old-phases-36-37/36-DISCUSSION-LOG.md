# Phase 36: Service Orchestration + Cross-Path Equivalence - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-03-31
**Phase:** 36-service-orchestration-cross-path-equivalence
**Areas discussed:** Validation strategy, Educational errors, Shorthand expansion, Cross-path equivalence

---

## Validation Strategy

| Option | Description | Selected |
|--------|-------------|----------|
| Pipeline `_validate()` step | Add validation in pipeline, extend `service/validate.py` | |
| Pydantic model validators | `@model_validator` / `@field_validator` on query models, calling `validate.py` helpers | |
| Three-layer (architecture doc) | Pydantic structural on model, type-specific on model, service semantic in pipeline | ✓ |

**User's choice:** Follow existing architecture doc (lines 631-635) and structure-over-discipline doc (lines 39-42). Offset-requires-limit is structural (like `_check_cross_type_fields`), so `@model_validator` on the query model. User identified this was already decided by pointing to the frequency model precedent.

**Notes:** Research agent initially suggested pipeline `_validate()` based on PITFALLS.md (not written by user). User corrected by pointing to architecture doc and frequency model validators as the authoritative pattern. The three-layer split was already documented.

---

## Educational Errors

| Option | Description | Selected |
|--------|-------------|----------|
| ToolError with valid-values list | Raise ValueError with educational message listing valid values | ✓ |
| Warning in ListResult, filter skipped | Return partial results with warning | |

**User's choice:** ToolError with valid-values list. Follow existing pattern (`LIFECYCLE_INVALID_VALUE`, `REPETITION_INVALID_FREQUENCY_TYPE`).

**Notes:** Error/warning boundary already established: ToolError for schema violations (can't proceed), warnings for runtime ambiguity (results still meaningful). Server's `_format_validation_errors()` already handles the Pydantic → agent-friendly message pipeline. User confirmed: "follow the pattern."

---

## Shorthand Expansion

### Status Shorthands (remaining, available, all)

| Option | Description | Selected |
|--------|-------------|----------|
| Implement shorthands | Expand remaining/available/all in pipeline | |
| Shorthands killed | Phase 34 D-03b already decided: no shorthands | ✓ |

**User's choice:** Confirmed shorthands were killed in Phase 34. Roadmap SC#3 was outdated and was updated during the discussion to remove shorthand references.

### review_due_within Parsing

| Option | Description | Selected |
|--------|-------------|----------|
| All on model (ReviewDueFilter) | `@field_validator` parses string into ReviewDueFilter value object. "Parse, don't validate." Service expands to datetime. | ✓ |
| All in pipeline | Model takes `str | None`, pipeline validates and expands | |
| Split (validate on model, expand in pipeline) | Parses twice or validates with regex then re-parses | |

**User's choice:** ReviewDueFilter as a `<noun>Filter` value object (taxonomy Scenario F pattern). User proposed the design: store amount + unit on the filter, validate on model construction, expand to datetime in the domain. DurationUnit as StrEnum.

**Notes:** User identified the taxonomy document as the key reference before the question was asked. User proposed the structured fields (amount, unit) and the domain expansion. Option 3 (split) was dismissed as "total madness" by user. Roadmap updated during discussion.

### ReviewDueFilter Unit Type

| Option | Description | Selected |
|--------|-------------|----------|
| DurationUnit StrEnum | Small enum: d, w, m, y | ✓ |
| Plain str, validated | Field validator checks against valid set | |

**User's choice:** DurationUnit StrEnum. Consistent with Availability enum pattern.

---

## Cross-Path Equivalence

### Test Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Parametrized repo fixture | Single test body, fixture with params=[sqlite, bridge]. Seed adapters translate neutral data. | ✓ |
| Explicit paired assertions | Each test calls both repos and asserts equality inline | |

**User's choice:** Parametrized fixture + seed adapters. Validated after investigation confirmed seeding is feasible (different formats but bounded translation).

### Entity Scope

| Option | Description | Selected |
|--------|-------------|----------|
| All 5 entities | Tasks, projects, tags, folders, perspectives | ✓ |
| Tasks and projects only | Focus on complex query paths | |

**User's choice:** All 5 entities.

### Ordering

| Option | Description | Selected |
|--------|-------------|----------|
| Sort by ID for comparison | No ordering added yet, sort by ID in tests only | ✓ |
| Assert identical order | Both paths must return same order | |
| Add ORDER BY in Phase 36 | Add deterministic ordering now | |

**User's choice:** Sort by ID in tests. No ordering added to repos. Ordering bug (pagination without deterministic order) captured as todo.

---

## Default Completed/Dropped Exclusion (SC#2)

| Option | Description | Selected |
|--------|-------------|----------|
| Model default is sufficient | ListTasksQuery.availability already defaults to [available, blocked] | ✓ |
| Pipeline needs extra logic | Pipeline should enforce/override beyond model default | |

**User's choice:** Model default is sufficient. No pipeline logic needed.

---

## Claude's Discretion

- Seed adapter implementation details (helper functions, fixtures, conftest organization)
- Internal pipeline step organization for ReviewDueFilter expansion
- Test case selection for cross-path equivalence (which filter combinations)
- Whether ReviewDueFilter expansion helper lives in `validate.py` or `domain.py`

## Deferred Ideas

- Deterministic ordering for pagination (TODO — ordering bug)
