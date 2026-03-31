---
title: Add deterministic ordering for list pagination
area: repository
priority: bug
discovered: 2026-03-31
context: Phase 36 discuss-phase — cross-path equivalence discussion
---

# Add deterministic ordering for list pagination

## Problem

`LIMIT`/`OFFSET` pagination in `query_builder.py` has no `ORDER BY` clause. Without deterministic ordering, the same query with the same offset can return different results — pages may overlap or skip items.

Both repository paths (SQL and bridge/in-memory) have this issue:
- SQL path: `LIMIT ? OFFSET ?` without `ORDER BY` — SQLite returns rows in arbitrary order
- Bridge path: fetch-all + Python filter — iteration order depends on insertion order

## Ideal solution

Order by OmniFocus display order (matching the UI arrangement). This likely involves `rank` columns in the OmniFocus SQLite schema and/or the bridge returning items in their natural perspective order. Needs investigation.

## Interim option

`ORDER BY persistentIdentifier` (or equivalent) as a stable fallback. Not user-meaningful but makes pagination deterministic.

## Affected files

- `src/omnifocus_operator/repository/query_builder.py` — task and project queries need `ORDER BY`
- `src/omnifocus_operator/repository/bridge.py` — BridgeRepository list methods need consistent sort
- `src/omnifocus_operator/repository/hybrid.py` — if ordering is applied after fetch

## Notes

- Cross-path equivalence tests (Phase 36) work around this by sorting results by ID before comparison
- Display order investigation may belong in v1.5 (UI & Perspectives)
