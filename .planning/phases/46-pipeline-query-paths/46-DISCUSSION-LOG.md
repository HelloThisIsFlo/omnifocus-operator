# Phase 46: Pipeline & Query Paths - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-04-08
**Phase:** 46-pipeline-query-paths
**Areas discussed:** Due-soon config retrieval, Lifecycle auto-include, Date field → column mapping, SQL composition, Inherited completion

---

## Due-soon Config Retrieval

| Option | Description | Selected |
|--------|-------------|----------|
| Repository protocol method | Add `get_due_soon_setting()` to Repository protocol. HybridRepo reads SQLite Settings table, BridgeOnlyRepo reads env var. Pipeline calls conditionally when `due: "soon"` present. | ✓ |
| Lifespan singleton | Read once at startup, cache on OperatorService. Stale if user changes OF preference. | |
| Always per-query | Read Settings table on every list_tasks call regardless of whether "soon" is used. | |

**User's choice:** Repository protocol method
**Notes:** Clean layering — each repo implementation handles its own config source. Conditional call avoids wasted I/O. Resolver stays pure.

---

## Lifecycle Auto-Include

| Option | Description | Selected |
|--------|-------------|----------|
| Dedicated `_resolve_date_filters()` | New method in pipeline. Takes now snapshot, resolves all 7 fields, accumulates lifecycle availability additions. Merged in `_build_repo_query`. Matches existing `_resolve_project`/`_resolve_tags` grain. | ✓ |
| Split across methods | Date resolution in new method, lifecycle availability folded into existing `_expand_availability` helper. | |
| All in `_build_repo_query` | Fold everything into existing method. Smallest diff but biggest method. | |

**User's choice:** Dedicated `_resolve_date_filters()`
**Notes:** Matches Method Object grain. `now` snapshot taken once at top. Lifecycle additions accumulated then merged in `_build_repo_query` via set-union.

---

## Date Field → Column Mapping

| Option | Description | Selected |
|--------|-------------|----------|
| Effective columns for all 7 dimensions | Confirmed by FINDINGS.md — always `effective*` columns for inherited fields, `dateAdded`/`dateModified` for non-inherited. | ✓ |

**User's choice:** Confirmed mapping
**Notes:** User emphasized: always filter on effective dates, never direct. "Show me completed tasks" means effectively completed, including project contents. This is opinionated but correct from real OmniFocus usage (8 years). Agent-facing API never mentions "effective."

---

## SQL Composition (Follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| AND composition | Date filters combine with AND at top level, consistent with all existing filters. Lifecycle date filters naturally exclude non-matching lifecycle states via NULL. | ✓ |
| OR composition (lifecycle in availability disjunction) | Lifecycle date filters join the availability OR clause. Would allow mixing available + completed-last-week in one query. | |

**User's choice:** AND composition
**Notes:** User pointed out all existing list_tasks filters are AND at top level. Tags use OR within the tag filter (any of these tags), but top-level is always AND. Adding OR for lifecycle would be inconsistent and add complexity. Agents wanting unions make separate calls.

---

## Inherited Completion (Follow-up)

| Option | Description | Selected |
|--------|-------------|----------|
| Document as implementation note | 174 tasks with inherited effectiveDateCompleted appearing in results is semantically correct. Pre-existing active-scope question, not v1.3.2. | ✓ |

**User's choice:** Document, don't block
**Notes:** User confirmed: effective dates everywhere. No IS NULL filtering (already scoped out in Phase 45 D-13). Intentional gap — clean scope, no real-life use case for filtering by absence of a date in 8 years of OmniFocus usage. Can be added later if requested.

---

## Claude's Discretion

- CF epoch conversion strategy
- `OPERATOR_DUE_SOON_THRESHOLD` env var format
- InMemoryBridge `get_due_soon_setting()` test implementation
- Internal method signatures and bridge filtering order

## Deferred Ideas

None — discussion stayed within phase scope.
