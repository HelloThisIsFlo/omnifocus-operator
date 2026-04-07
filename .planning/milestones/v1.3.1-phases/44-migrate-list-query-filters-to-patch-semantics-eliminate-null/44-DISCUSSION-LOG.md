# Phase 44: Migrate list query filters to Patch semantics -- Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md -- this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 44-migrate-list-query-filters-to-patch-semantics-eliminate-null
**Areas discussed:** Empty-list error wording, Service layer translation, review_due_within validator, Null guards, AvailabilityFilter mechanics

---

## Empty-list Error Wording

| Option | Description | Selected |
|--------|-------------|----------|
| Two templates | One for tags (provide values or omit), one for availability (provide statuses or omit for default). Different recovery actions = different messages. | |
| Generic template with {field} | Single template: '{field} cannot be empty. Provide at least one value or omit the field.' | |
| Per-field templates | 5 distinct messages, each tailored to the specific field. | |

**User's choice:** Generic template, but refined: `"'{field}' cannot be empty. To ignore this filter, simply omit the field."` No "provide at least one value" -- that's redundant.

**Follow-up decision:** User proposed adding `ALL` shorthand to availability enums, which creates a second template for availability fields: `"'{field}' cannot be empty. Use 'all' to include every status, or omit for the default filter."`

**Notes:** User noted the field name should be in single quotes inside the message. The guidance genuinely differs between filter-like fields (just omit) and availability fields (use ALL or omit for defaults), justifying two templates.

---

## AvailabilityFilter ALL Shorthand (emerged from error wording discussion)

| Option | Description | Selected |
|--------|-------------|----------|
| Add ALL to new filter enums | AvailabilityFilter, TagAvailabilityFilter, FolderAvailabilityFilter in contracts/ with ALL value | :heavy_check_mark: |
| Keep current enums, no ALL | Agents must list all individual values to get everything | |

**User's choice:** Add ALL shorthand, folded into Phase 44 scope.

**Follow-up decisions:**
- ALL value is lowercase `"all"` (consistent with existing enum values)
- Mixed usage (`["all", "available"]`): accept, treat ALL as dominant, add warning. User explicitly chose warning over error -- consistent with project's educational warning pattern.
- Filter enums live in new `contracts/use_cases/list/_enums.py`
- ALL expansion + warning logic lives in service pipeline (not field_validator)

---

## Service Layer Translation (UNSET -> None)

| Option | Description | Selected |
|--------|-------------|----------|
| unset_to_none() helper | New utility in contracts/base.py alongside is_set(). Clean call sites, reusable. | :heavy_check_mark: |
| Inline is_set() ternaries | No new function: `field if is_set(field) else None` at each usage. | |
| Early normalization in execute() | Translate all fields upfront into self._field vars. Downstream unchanged. | |

**User's choice:** unset_to_none() helper after clarifying the difference between it and early normalization.

**Notes:** User asked for clarification on the difference between option 1 and option 3. Key distinction: unset_to_none() translates lazily at each usage site (one source of truth: self._query), while early normalization translates eagerly creating parallel state (self._query.field vs self._field). User chose the single-source-of-truth approach.

---

## review_due_within Validator

| Option | Description | Selected |
|--------|-------------|----------|
| Minimal (string-only) | Just `if isinstance(v, str): parse`. Everything else falls through to Pydantic. | |
| Tightened catch-all | String parsing + reject anything not str/dict/ReviewDueFilter with educational error. | :heavy_check_mark: |
| Keep ReviewDueFilter guard | Keep isinstance check for explicitness, drop None check. | |

**User's choice:** Simplified, but with catch-all to prevent Pydantic leaks. User asked about what happens with invalid types (numbers, etc.) which led to the broader null guard discussion.

**Notes:** User asked "when would it already be an instance of ReviewDueFilter?" -- answered: programmatic construction in tests/internal code. The isinstance check is redundant since fall-through to Pydantic handles it.

---

## Null Guards (Pydantic Leak Prevention)

| Option | Description | Selected |
|--------|-------------|----------|
| Shared helper + model_validator | Helper `reject_null_filters(data, fields)` in _validators.py. Each model calls from model_validator(mode='before'). | :heavy_check_mark: |
| Auto-detect on QueryModel base | Base class introspects Patch fields automatically. Zero maintenance. | |
| Rely on middleware only | ValidationReformatterMiddleware already filters _Unset. | |
| Per-field validators | 13 individual @field_validator decorators. | |

**User's choice:** Shared helper after codebase exploration confirmed the established pattern.

**Notes:** User asked to explore existing patterns in the codebase. Agent found: (1) write-side uses per-field validators with field-specific messages, (2) middleware already filters _Unset as defense-in-depth, (3) no base-class auto-detection (intentional, to preserve PatchOrClear distinction). Since read-side messages are all identical (unlike write-side), shared helper is more pragmatic than 13 identical validators.

---

## Claude's Discretion

- Internal naming of availability expansion helper methods in service pipelines
- Whether the three AvailabilityFilter enums share a base or are standalone
- Test organization for new validators and ALL expansion logic
- Exact wording of the mixed-ALL warning message

## Deferred Ideas

- Null-stripping for read tool responses (v1.4 scope, not this phase)
