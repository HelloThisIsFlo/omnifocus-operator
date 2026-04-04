---
created: 2026-03-08T11:51:37.290Z
title: Add position field to expose child task ordering
area: models
priority: high
files:
  - src/omnifocus_operator/models/
  - src/omnifocus_operator/service/
---

## Problem

The agent has no way to see child ordering — `get_task` shows the parent but not siblings or their position. During UAT, verifying task order after moves was impossible without manual OmniFocus inspection. Workaround: set `estimatedMinutes` to 1, 2, 3... as position markers, then asked user to visually confirm sequential numbers.

## Solution — FULLY RESEARCHED

Deep dive completed: `.research/deep-dives/direct-database-access-ordering/RESULTS.md`

**No remaining unknowns.** The research answered all ordering questions.

- Add an `order` integer field to task responses so agents can see sibling ordering
- `parent` stays as-is (object with id and name) — this is purely read-only, informational
- When listing children of a parent, return them in display order with `order`
- Example: `[{"id": "abc", "name": "Design", "order": 0, "parent": {"id": "xyz", "name": "..."}}, ...]`
- Independent of the `actions.move` restructuring (see "Introduce actions grouping" todo). Can be implemented at any time.

### How to compute `order`

Two options (implementation decision, not a research question):
- **SQL-side**: `ROW_NUMBER() OVER (PARTITION BY parent ORDER BY rank) - 1` — cheap window function, 0-based
- **Python-side**: sort siblings by `rank`, assign index

Raw `rank` values (e.g. -1,069,498,304) are not human-friendly. The 0-based ordinal is what agents need.

### Key findings from research

- `rank` INTEGER column is unique within each parent, determines UI order
- Signed 32-bit range, midpoint-insertion scheme (65536 gaps)
- Negative ranks are normal (from drag-and-drop reordering) — verified with real reorganized data
- `rank` works identically for tasks, projects, folders, and tags

## Extra Context

- TaskPaper output (v1.4.2) naturally shows hierarchy and order via indentation — complementary to `order` field
- `order` is for programmatic use, TaskPaper for full-hierarchy comprehension

## Sequencing

- Target: v1.3.3 (ordering milestone). The query infrastructure built for filtering naturally supports exposing child ordering.
- Implementing this before or alongside the same-container move fix is ideal — both need the ability to query children in order.

## Related

- **[Fix same-container move by translating to moveBefore/moveAfter](2026-03-12-fix-same-container-move-by-translating-to-movebefore-moveafter.md)** — the write-side counterpart. This todo exposes ordering to agents (read); that fix uses ordering to make moves work (write). They share infrastructure and should land in the same milestone.
