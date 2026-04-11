# Phase 48: Refactor DateFilter into discriminated union with typed date bounds - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-10
**Phase:** 48-refactor-datefilter-into-discriminated-union-with-typed-date
**Areas discussed:** Timezone todo scope, Typed bound ordering, Error message wording, Discriminator pattern, Todo review

---

## Timezone Todo Scope

| Option | Description | Selected |
|--------|-------------|----------|
| Proceed with AwareDatetime as designed | Phase 48 fixes contract shape. Timezone interpretation stays in resolver. Timezone todo stays separate. | ✓ |
| Fold timezone decision into Phase 48 | Decide timezone strategy now, implement together. Expands scope but avoids locking in wrong semantics. | |

**User's choice:** Proceed as designed
**Notes:** User emphasized wanting Phase 48 to be purely about structural consistency — making everything AwareDatetime. The timezone interpretation question is easier to tackle as a single coherent change in a separate phase, rather than half-migrating here and potentially needing to undo. "It's going to be easier if I change my mind about the timezone thing."

---

## Typed Bound Ordering

| Option | Description | Selected |
|--------|-------------|----------|
| Normalize to naive datetime | date → datetime(midnight), AwareDatetime → strip tzinfo. Same guarantee as current _parse_to_comparable. | ✓ |
| Skip mixed-type pairs | Only compare same types. Reversed mixed-type bounds pass silently, caught at resolve-time. | |

**User's choice:** Normalize to naive (with caveat)
**Notes:** User agreed with normalization approach. Key requirement: must not produce false rejections for valid queries. The reverse (missing a truly reversed pair) is acceptable since the resolver catches it later. User also asked about using `mode="after"` validator — confirmed it won't work because the value fails all union branches before an after-validator runs.

---

## Error Message Wording

| Option | Description | Selected |
|--------|-------------|----------|
| Educative with accepted formats | Names fields, lists accepted types with examples. Self-contained for agent self-correction. | ✓ |
| Minimal | "Requires at least one of: before or after." No format guidance. | |

**User's choice:** Educative wording looks good
**Notes:** Draft text accepted as-is. Delete 4 dead constants (DATE_FILTER_MIXED_GROUPS, DATE_FILTER_MULTIPLE_SHORTHAND, DATE_FILTER_INVALID_THIS_UNIT, DATE_FILTER_INVALID_ABSOLUTE).

---

## Naive Datetime BeforeValidator

Emerged during error message discussion. User initially concerned about "re-implementing Pydantic" but agreed when framed as pattern detection (not parsing).

**Decision:** Add `mode="before"` field_validator on `before`/`after` fields. String shape check for naive datetimes. Clean educational error.

---

## Callable Discriminator Pattern

Emerged during todo review when `{}` empty input error regression was identified.

| Option | Description | Selected |
|--------|-------------|----------|
| Simple union (X \| Y \| Z) | Like EndConditionSpec. Accept rare noisy errors. | |
| Callable Discriminator | Route to one branch based on key presence. Clean single-branch errors. | ✓ |

**User's choice:** Add Discriminator
**Notes:** User was genuinely interested in the pattern for learning purposes. Decision motivated both by error UX preservation and by the pattern being "a nice pattern for the future." Acknowledged it's a new pattern alongside EndConditionSpec's simple union — justified by different union shapes.

---

## Todo Review Findings

User asked for critical review of the todo document (designed with another agent). Findings:

1. **`isinstance(value, DateFilter)` reasoning** — Todo says TypeError; real issue is AttributeError. Fix is correct, reasoning updated.
2. **`{}` error regression** — Led to Discriminator discussion (resolved above).
3. **Typo line 140** — `ThispPeriodFilter` (extra 'p'). Minor.
4. **Everything else checked out** — Model structure, spike results, validator migration, dead code removal all confirmed correct.

---

## Claude's Discretion

- Internal naming of discriminator routing function
- Whether `_validate_duration` is duplicated or shared as private helper
- Test migration approach and ordering
- BeforeValidator placement details

## Deferred Ideas

- Timezone handling strategy — separate future phase
- Date filters on list_projects — separate capability
