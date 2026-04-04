# Project Research Summary

**Project:** OmniFocus Operator — v1.3 Read Tools
**Domain:** SQL-filtered list/count tools for MCP server with dual read paths
**Researched:** 2026-03-29
**Confidence:** HIGH

## Executive Summary

v1.3 adds 5 new read tools (`list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`) to the existing three-layer architecture. No separate count tools — `ListResult` embeds `total_count` in every list response. The core challenge is not the feature set — it's maintaining identical semantics across two read paths: SQL (HybridRepository) and in-memory filtering (BridgeRepository fallback). Every filter must produce the same results regardless of which path executes it.

The recommended approach is clean layer separation: service layer handles all resolution and expansion (tag names to IDs, status shorthands, duration parsing, default exclusions), repositories receive only concrete unambiguous values. SQL generation is extracted to a pure-function `query_builder.py` module; in-memory filtering lives in a separate `filter.py` module. Both receive the same resolved query models (`ListTasksQuery`, `ListProjectsQuery`, `ListTagsQuery`, `ListFoldersQuery` — all inheriting `QueryModel`). Counting is embedded: `ListResult` always includes `total_count`, making separate count tools unnecessary.

The critical risk is filter semantic drift between SQL and in-memory paths — bugs are invisible until someone compares both paths side-by-side. Prevention requires: explicit NULL handling in both paths, LIKE escaping, deterministic ORDER BY for pagination, shared shorthand expansion at the service layer, and parametrized cross-path equivalence tests. No new dependencies are needed. Everything builds on the existing codebase.

## Key Findings

### Recommended Stack

No new dependencies. The existing stack (Python 3.12+, FastMCP, Pydantic v2, stdlib sqlite3) is sufficient. Two new internal modules are introduced: `repository/query_builder.py` (pure SQL generation) and `repository/filter.py` (in-memory predicates). New contract models: `ListTasksQuery`, `ListProjectsQuery`, `ListTagsQuery`, `ListFoldersQuery` (all inherit `QueryModel`), `ListResult[T]` (inherits `OmniFocusBaseModel`).

**Core technologies:**
- `sqlite3` (stdlib): filtered SQL via dynamic WHERE clause builder — parameterized `?` placeholders throughout, no injection risk
- Pydantic v2: `ListTasksQuery` / `ListProjectsQuery` with `extra="forbid"` — validates agent input at server entry
- Tag subquery (not JOIN): `IN (SELECT task FROM TaskToTag WHERE tag IN (?,...))` — avoids duplicate rows for multi-tag tasks
- LIKE with LOWER(): `LOWER(t.name) LIKE LOWER(?)` — consistent case-insensitive search between SQL and Python paths
- LIMIT/OFFSET + Python len() + slice: adequate for ~2,400 tasks; total_count without a second query

### Expected Features

**Must have (table stakes):**
- `list_tasks` with 10 filters: inbox, flagged, project, tags, has_children, estimated_minutes_max, availability, search, limit, offset
- `list_projects` with 6 filters: status, folder, review_due_within, flagged, limit, offset
- `list_tags`, `list_folders` with status list filter (OR logic, default: remaining); `list_perspectives` with no filters
- Bridge fallback parity — BridgeRepository produces identical results to SQL path
- Default exclusion of completed/dropped tasks
- Parameterized queries throughout

**Should have (differentiators):**
- `<6ms` filtered queries (vs 46ms full snapshot) — natural consequence of filtered SQL
- `ListResult` with `total_count` — agents get pagination info without a separate call
- `review_due_within` duration parsing ("now", "1w", "2m") — CF epoch float comparison
- Status shorthand expansion ("remaining", "available", "all") — resolved in service layer before either repository
- Educational error messages on validation failure — extend existing write-tool pattern

**Defer (v1.3.2+):**
- Date-based filtering (due, defer, planned, completed dates) — WHERE clause infrastructure is built in v1.3, filter logic deferred
- Fuzzy search — different algorithm from LIKE, deferred to v1.4.1
- Field selection / projection — deferred to v1.4
- ORDER BY configuration — hardcode `ORDER BY t.persistentIdentifier` for now

### Architecture Approach

Extend the existing three-layer architecture with no new layers. Service layer gains resolution pipelines (`_ListTasksPipeline`, `_ListProjectsPipeline`) following the established Method Object pattern. Repository layer gains two new modules for SQL generation and in-memory filtering. 7 new tools registered in `server.py`. Simple tools (list_tags, list_folders, list_perspectives) use direct pass-throughs, not pipelines.

**Major components:**
1. `contracts/use_cases/list_tasks.py`, `list_projects.py`, `list_common.py` — typed query contracts + `ListResult[T]` container
2. `repository/query_builder.py` — pure functions: query model in, `(sql_string, params_tuple)` out; independently testable without a database
3. `repository/filter.py` — in-memory predicate functions for BridgeRepository fallback; mirrors SQL semantics exactly
4. `_ListTasksPipeline` / `_ListProjectsPipeline` in `service/service.py` — tag resolution, shorthand expansion, default exclusions; Method Object pattern
5. 7 new tool registrations in `server.py` with LLM-oriented descriptions that enumerate all valid values

### Critical Pitfalls

1. **SQL/in-memory result divergence** — service layer resolves all shorthands and ambiguities before reaching either repository; parametrized cross-path equivalence tests are mandatory, not optional
2. **Pagination without deterministic ORDER BY** — every filtered query must include `ORDER BY t.persistentIdentifier`; in-memory path must `sorted(..., key=lambda t: t.id)` before slicing
3. **NULL handling asymmetry** — SQL silently excludes NULL via three-valued logic; Python must mirror with explicit `if field is not None` guards; test fixtures must include NULL values for every filterable optional field
4. **Count/list divergence** — `count_tasks()` must call the list pipeline and return `result.total_count`, never maintain a parallel WHERE clause
5. **LIKE escaping** — escape `%` and `_` in user search input with `ESCAPE '\'`; use `LOWER()` on both sides; in-memory path must use the same case semantics

## Implications for Roadmap

### Phase 1: Contracts and Query Foundation

**Rationale:** Everything else depends on typed query models and the query builder. Pure functions, no database needed — immediately testable.
**Delivers:** `ListTasksQuery`, `ListProjectsQuery`, `ListTagsQuery`, `ListFoldersQuery`, `ListResult[T]`, `query_builder.py`, protocol extensions on Repository and Service
**Addresses:** Typed filter contracts; ARCHITECTURE Patterns 1, 2, 3
**Avoids:** Pitfall 1 (divergence) — establishes the single source of truth for filter parameters before any repository code is written

### Phase 2: Repository Layer — SQL Path

**Rationale:** SQL path is the primary read path; build and test it first before the fallback.
**Delivers:** `HybridRepository.list_tasks`, `HybridRepository.list_projects`, list_tags/folders/perspectives
**Uses:** `query_builder.py` from Phase 1; reuses existing `_map_task_row`, `_map_project_row`
**Avoids:** Pitfall 2 (ORDER BY), Pitfall 3 (LIKE case), Pitfall 4 (NULL), Pitfall 9 (project JOIN through ProjectInfo), Pitfall 13 (LIKE wildcard escaping)

### Phase 3: Repository Layer — In-Memory Fallback

**Rationale:** Build after SQL path so cross-path tests can immediately verify equivalence.
**Delivers:** `filter.py`, `BridgeRepository.list_tasks/projects/tags/folders/perspectives`
**Uses:** Same `ListTasksQuery` models; each predicate mirrors its SQL counterpart
**Avoids:** Pitfall 1 (divergence) — cross-path equivalence tests run immediately after this phase; Pitfall 8 (tag OR vs AND algebra)

### Phase 4: Service Layer — Orchestration

**Rationale:** Service depends on both repository paths being complete.
**Delivers:** `_ListTasksPipeline`, `_ListProjectsPipeline`, simple list pass-throughs (tags, folders, perspectives via query models)
**Uses:** `Resolver.resolve_tags()` (existing); Method Object pattern (established)
**Avoids:** Pitfall 5 (count/list divergence via shared code path), Pitfall 6 (shorthand expansion in one place), Pitfall 7 (CF epoch resolution for review_due_within), Pitfall 10 (default exclusion as removable clause), Pitfall 11 (offset without limit validation)

### Phase 5: Server Registration and Integration Testing

**Rationale:** Outermost layer wires everything together; integration and cross-path equivalence tests run here.
**Delivers:** 5 new tool registrations, LLM-oriented descriptions with enumerated values and examples, full equivalence test suite
**Avoids:** Pitfall 12 (tool description quality and LLM calling errors)

### Phase Ordering Rationale

- Bottom-up dependency order: contracts -> SQL repository -> in-memory repository -> service -> server
- Cross-path equivalence tests are only meaningful once both repository paths exist — Phase 3 must complete before Phase 5 validation
- No separate count tools — `total_count` embedded in `ListResult` eliminates divergence risk by construction
- Simple tools (list_tags, list_folders, list_perspectives) slot into Phase 2 as low-complexity deliverables alongside the SQL path

### Research Flags

Phases with standard patterns (skip deeper research):
- **Phase 1 (Contracts):** Pydantic model patterns well-established in this codebase; `ListResult[T]` is straightforward
- **Phase 4 (Service):** Method Object pattern is established; `Resolver.resolve_tags()` already exists and can be reused
- **Phase 5 (Server):** FastMCP tool registration is well-understood from v1.2

Phases that benefit from careful implementation review (not research, but verification):
- **Phase 2 (SQL Path):** Project name filter requires a non-trivial JOIN through `containingProjectInfo -> ProjectInfo -> Task.name` (Pitfall 9). Run `EXPLAIN QUERY PLAN` on generated queries during development to verify index usage. Verify exact column names for `nextReviewDate` and `effectiveStatus` in the live schema.
- **Phase 3 (In-Memory):** Each predicate must mirror its SQL counterpart exactly — write the equivalence test fixture before the predicate code to drive correctness.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | No new deps; all patterns established in v1.1/v1.2; direct extension of existing code |
| Features | HIGH | Spec is detailed with explicit acceptance criteria; deferral decisions are explicit (v1.3.2) |
| Architecture | HIGH | Existing codebase thoroughly analyzed; new components are direct extensions of established conventions |
| Pitfalls | HIGH | SQL/NULL/LIKE semantics well-documented; cross-path drift is clearly identified with concrete prevention strategies |

**Overall confidence:** HIGH

### Gaps to Address

- **Project name JOIN structure:** The SQL to traverse `containingProjectInfo -> ProjectInfo -> Task.name` needs verification against the actual SQLite schema during Phase 2 (column name and join path).
- **`review_due_within` CF epoch:** Verify `nextReviewDate` is the correct column name in `ProjectInfo` and confirm it stores a CF epoch float before building the date comparison.
- **Tag case sensitivity contract:** The spec doesn't explicitly define whether tag name matching in the `tags` filter is case-sensitive. Decide before Phase 2: exact match (case-sensitive) is the safer default; document it in the tool description.
- **`ListResult[T]` FastMCP serialization:** Verify FastMCP correctly serializes a Pydantic generic model to JSON Schema in the outputSchema. Run `test_output_schema.py` after introducing `ListResult` — per project conventions, this test catches serializer issues.
- **Date filter model design:** `ListTasksQuery` should include nullable date filter fields from the start (per the v1.3.2 spec) even if v1.3 doesn't implement them — avoids a breaking contract change in the next milestone.

## Sources

### Primary (HIGH confidence)
- `.research/updated-spec/MILESTONE-v1.3.md` — feature requirements, acceptance criteria, filter definitions
- `.research/updated-spec/MILESTONE-v1.3.2.md` — date filter deferral decisions
- `docs/architecture.md` — three-layer architecture, Method Object pattern, model taxonomy
- `.research/deep-dives/direct-database-access/RESULTS.md` — SQLite schema, CF epoch constants, existing query patterns
- `repository/hybrid.py`, `repository/bridge.py`, `service/service.py` — established patterns to extend

### Secondary (MEDIUM confidence)
- [SQLite NULL handling](https://sqlite.org/nulls.html) — three-valued logic, NULL in comparisons
- [SQLite LIKE expression docs](https://www.sqlite.org/lang_expr.html) — ASCII-only case folding, ESCAPE clause
- [Non-deterministic pagination](https://use-the-index-luke.com/sql/partial-results/fetch-next-page) — ORDER BY requirement for LIMIT/OFFSET

### Tertiary (LOW confidence)
- LLM tool calling behavior — tool description quality recommendations based on community patterns; validate with UAT against actual models

---
*Research completed: 2026-03-29*
*Ready for roadmap: yes*
