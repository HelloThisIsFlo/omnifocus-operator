# Phase 35: SQL Repository - Discussion Log

> **Audit trail only.** Do not use as input to planning, research, or execution agents.
> Decisions are captured in CONTEXT.md — this log preserves the alternatives considered.

**Date:** 2026-03-30
**Phase:** 35-sql-repository
**Areas discussed:** Tags/Folders query approach, Lookup tables for list queries, Performance validation (INFRA-02), Plan structure

---

## Tags/Folders Query Approach

| Option | Description | Selected |
|--------|-------------|----------|
| Fetch-all + Python filter | Reuse existing _TAGS_SQL/_FOLDERS_SQL, filter availability in Python. Zero query_builder growth. ~64/~79 rows trivially fast. | ✓ |
| Extend query_builder | Add build_list_tags_sql/build_list_folders_sql for uniform pattern across all 5 entity types. |  |

**User's choice:** Fetch-all + Python filter (Recommended)
**Notes:** Query builder's value is parameterized multi-condition SQL — tags/folders have one filter (availability) with zero user-supplied params. Fetch-all is simpler with the door open to migrate if filters grow.

---

## Lookup Tables for List Queries

| Option | Description | Selected |
|--------|-------------|----------|
| Full lookup tables, same as get_all | Load ALL tag names and ALL project info into memory first, then map only filtered rows. Reuses existing code exactly. Sub-millisecond at current scale. | ✓ |
| Targeted lookups for returned rows only | Fetch filtered tasks first, collect IDs, then query ONLY tags/parents for those IDs. More surgical, two-phase pattern. |  |
| SQL JOINs + GROUP_CONCAT | Single round-trip with JOINs. Breaks mapper contract, non-deterministic ordering. |  |

**User's choice:** Full lookup tables, same as get_all (Recommended)
**Notes:** At ~64 tags, ~363 projects, ~2,400 tasks — full table scans are sub-millisecond. Reusing the existing _read_all() pattern means zero new logic and unchanged row mapper signatures.

---

## Performance Validation (INFRA-02)

| Option | Description | Selected |
|--------|-------------|----------|
| Comparative test + UAT note | In pytest: seed ~200 rows, run filtered query AND full get_all, assert filtered is faster. UAT confirms real gap. | ✓ |
| Defer entirely to UAT | Validate manually against real OmniFocus database. No automated regression detection. |  |
| Hard timing threshold in pytest | assert elapsed < 6ms. Clear pass/fail but machine-dependent and CI-flaky. |  |

**User's choice:** Comparative test + UAT note (Recommended)
**Notes:** Core tension: tests use in-memory SQLite where both paths are sub-millisecond. Comparative test eliminates machine variance by testing relative ordering. Seeding ~200 rows makes the gap meaningful. UAT covers real-database validation.

---

## Plan Structure

| Option | Description | Selected |
|--------|-------------|----------|
| Two plans | Plan 1: tasks + projects (query builder, lookups, pagination). Plan 2: tags + folders + perspectives (simple filters, no lookups). | ✓ |
| Single plan (all 5) | One commit boundary. Simpler tracking but larger diff. |  |
| Three plans | tasks / projects / simpler entities. Maximum granularity but artificial split. |  |

**User's choice:** Two plans (Recommended)
**Notes:** Complexity split maps to what exists in hybrid.py — tasks/projects share lookup table setup and query builder integration; tags/folders/perspectives have zero lookup dependencies. Natural boundary, not administrative.

---

## Claude's Discretion

- Internal organization of sync helpers
- hasMore computation formula
- Lookup-building code sharing strategy
- Test fixture design for performance seed
- Perspectives plist flow

## Deferred Ideas

None — discussion stayed within phase scope.
