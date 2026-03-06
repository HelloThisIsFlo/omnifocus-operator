# TODO #3 Findings: SQLite Read Performance

**Date:** 2026-03-06
**Status:** Complete

---

## Abstract

SQLite reads are fast enough that we don't need any caching layer. A full snapshot of all 5 tables (2829 tasks, 368 projects, 65 tags, 79 folders, 4581 tag links) completes in ~46ms. Filtered queries run under 6ms. This eliminates the need for cache invalidation logic entirely — just read fresh from SQLite on every MCP tool call.

For comparison, the JS bridge takes 1-3 seconds for the same data. SQLite is 30-60x faster.

---

## Results

Database: 2829 tasks, 368 projects, 65 tags, 79 folders, 4581 tag links. 10 iterations each.


| Query                      | Min    | Avg    | Max    |
| -------------------------- | ------ | ------ | ------ |
| Full task read             | 38.1ms | 38.8ms | 40.0ms |
| Full snapshot (all tables) | 44.7ms | 45.9ms | 48.6ms |
| Task count only            | 0.0ms  | 0.0ms  | 0.0ms  |
| Actionable overdue filter  | 5.8ms  | 5.9ms  | 6.0ms  |
| Task+tag join              | 5.1ms  | 5.4ms  | 6.0ms  |


Connection overhead: ~1.8ms per open/close (negligible).

---

## Script

- `test_sqlite_benchmark.py` — Benchmarks 5 query types with warmup, plus connection overhead measurement

