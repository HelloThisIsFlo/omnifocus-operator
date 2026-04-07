# Phase 45: Date Models & Resolution - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-07
**Phase:** 45-date-models-resolution
**Areas discussed:** "soon"/"overdue" spec tension, Resolved output boundary, DateFilter contract shape, Week start config, Due-soon threshold

---

## "soon"/"overdue" Spec Tension

| Option | Description | Selected |
|--------|-------------|----------|
| Timestamp-resolved DateRange | Resolver computes timestamps directly. "overdue" → {before: now}, "soon" → {before: threshold}. Both SQL and bridge use same comparisons. | ✓ |
| Column-marker pass-through | Resolver emits tagged markers, Phase 46 maps to SQL columns. Blocked by findings. | |

**User's choice:** Timestamp-resolved DateRange
**Notes:** Column approach blocked by findings: dueSoon column excludes overdue (zero overlap), overdue column stale on completed tasks (339), bridge has no column equivalent. RESOLVE-11/12 in REQUIREMENTS need updating.

---

## Resolved Output Boundary

| Option | Description | Selected |
|--------|-------------|----------|
| Simple _after/_before fields on RepoQuery | 7 × 2 = 14 datetime fields. "any" = availability expansion. | ✓ |
| Tagged union (DateRange \| IsNull \| IncludeAll) | 3-variant union type per date dimension. | |
| Single flat type with optional fields | One class with start/end/is_null/include_all. Ambiguous. | |
| Pipeline-internal only | Don't put on RepoQuery, pass directly to query builder. | |

**User's choice:** Simple _after/_before fields on RepoQuery
**Notes:** User pointed out the Frequency model precedent — flat models preferred over tagged unions in this codebase. Patch semantics handle UNSET vs set distinction. "any" is just availability expansion (same as current `availability: ["completed"]`). "none" (IS NULL) scoped out entirely — no _is_null fields needed.

---

## DateFilter Contract Shape

| Option | Description | Selected |
|--------|-------------|----------|
| Flat model with validators (MoveAction pattern) | Single model, 5 optional keys, model_validator for mutual exclusion. Field-specific StrEnum/Literal for shortcuts. | ✓ |
| Two models with Union (DateShorthand \| DateAbsolute) | Pydantic v2 left-to-right union evaluation produces confusing errors. | |
| Discriminated union with literal type field | Forces agents to supply a discriminator field — breaks spec's clean syntax. | |

**User's choice:** Flat model with validators + field-specific StrEnum/Literal shortcuts
**Notes:** User confirmed StrEnum approach after realizing shortcuts include overdue/soon (not just "any"). Each field gets its own enum type so JSON Schema shows valid shortcuts per field. User referenced Frequency model evolution (flat over tagged union) as validation.

---

## Week Start Config

| Option | Description | Selected |
|--------|-------------|----------|
| os.environ.get() — same as existing OPERATOR_* vars | OPERATOR_WEEK_START env var, default Monday. Follows existing pattern. | ✓ |
| Hardcoded Monday | No config. Sunday users out of luck. | |
| pydantic-settings | Over-engineered for one value. Noted as future consolidation. | |

**User's choice:** Env var, same pattern as existing
**Notes:** User corrected that the codebase already has OPERATOR_* env vars (I incorrectly stated there were none). Pydantic-settings noted as future improvement for consolidating 3-6 env vars.

---

## Due-Soon Threshold

| Option | Description | Selected |
|--------|-------------|----------|
| Read from OmniFocus Settings table + env var fallback | DueSoonInterval + DueSoonGranularity from SQLite. OPERATOR_DUE_SOON_THRESHOLD env var for bridge-only mode. Fail fast if neither. | ✓ |
| Hardcode 24h | Simple but mismatches user's OmniFocus config. | |

**User's choice:** Settings table primary, env var fallback, fail fast
**Notes:** User ran a spike experiment that discovered DueSoonGranularity flag — two distinct modes (rolling vs calendar-aligned). "Today" and "24 hours" share interval=86400 but differ in granularity. Critical for correct behavior at midnight boundary.

---

## "none" Shortcut

| Option | Description | Selected |
|--------|-------------|----------|
| Include in v1.3.2 | IS NULL filtering for tasks without dates. | |
| Scope out | Defer to future milestone. UNSET handles "no filter" case. | ✓ |

**User's choice:** Scope out
**Notes:** User: "I personally don't have the use case. In six years of heavy OmniFocus I've never asked this question." Valid use case (find tasks missing due dates) but niche enough to defer.

---

## Claude's Discretion

- Exact StrEnum class names and grouping
- DurationUnit reuse vs new type
- Resolver module structure
- Error message wording

## Deferred Ideas

- "none" shortcut (IS NULL filtering) — future milestone
- pydantic-settings consolidation of env vars — future improvement

## Requirements Updates Applied

The following changes were applied to `.planning/REQUIREMENTS.md` based on decisions above:

- **DATE-06**: Revised — removed `"none"` reference (D-13)
- **DATE-07**: ~~Struck through~~ — scoped out (D-13)
- **DATE-08**: ~~Struck through~~ — scoped out (D-13)
- **RESOLVE-11**: ~~Struck through~~ → revised to timestamp comparison (D-04)
- **RESOLVE-12**: ~~Struck through~~ → revised with two-mode threshold + Settings table (D-04/D-06)
- **EXEC-08**: ~~Struck through~~ — scoped out (D-13)
- **Out of Scope** table: added `"none"` IS NULL filtering, updated due-soon threshold entry
- **Coverage**: 40 total → 37 active (3 scoped out), 3 revised
