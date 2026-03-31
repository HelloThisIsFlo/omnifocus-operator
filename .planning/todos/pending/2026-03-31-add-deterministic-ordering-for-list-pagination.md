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

## Solution — FULLY RESEARCHED

Deep dive completed: `.research/deep-dives/direct-database-access-ordering/RESULTS.md`

**No remaining unknowns.** The research reverse-engineered OmniFocus's UI ordering from SQLite and validated it against real reorganized data.

### Tasks (the main one)

Prepend a recursive CTE to every task query. The CTE builds a `sort_path` from rank values at each depth level, producing exact OmniFocus outline order:

```sql
WITH RECURSIVE task_order(id, sort_path) AS (
    SELECT t.persistentIdentifier, printf('%010d', t.rank + 2147483648)
    FROM Task t JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
    UNION ALL
    SELECT t.persistentIdentifier, o.sort_path || '/' || printf('%010d', t.rank + 2147483648)
    FROM Task t JOIN task_order o ON t.parent = o.id
)
-- Then JOIN task_order and ORDER BY sort_path
```

- Performance: ~5ms for 3062 tasks (well under 100ms target)
- Handles negative ranks, drag-and-drop reordering, action groups, multi-project queries
- Inbox: extend CTE with second anchor + `ZZZZZZZZZZ/` prefix (Strategy B, validated)

### Projects / Folders / Tags

No CTE needed — simple `ORDER BY parent, rank ASC, persistentIdentifier ASC`

### Bridge path

Sort by rank in Python after fetch. Same semantics, different implementation.

## Affected files

- `src/omnifocus_operator/repository/query_builder.py` — task and project queries need `ORDER BY` (CTE for tasks, simple rank for others)
- `src/omnifocus_operator/repository/bridge.py` — BridgeRepository list methods need consistent sort by rank
- `src/omnifocus_operator/repository/hybrid.py` — if ordering is applied after fetch

## Notes

- Cross-path equivalence tests (Phase 36) work around this by sorting results by ID before comparison
- Simple `ORDER BY rank` does NOT work for flat task queries — rank is only unique within a parent, interleaves depths nonsensically. The CTE is required.
