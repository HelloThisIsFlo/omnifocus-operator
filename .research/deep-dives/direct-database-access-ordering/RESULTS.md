# OmniFocus UI Ordering from SQLite — Investigation Results

> **Status**: Complete
> **Date**: 2026-03-31
> **Purpose**: Reverse-engineer OmniFocus's manual arrangement order from SQLite so query results match project UI order

## TL;DR

**A recursive CTE building a `sort_path` from rank values at each depth level reproduces exact OmniFocus UI outline order.** Verified against two test projects (17 tasks across 4 nesting levels). Performance: ~5ms for the full 3062-task database — well under the 100ms target. The CTE should be prepended to every paginated query in `query_builder.py`.

Simple `ORDER BY rank` does NOT work for flat queries — rank is only unique within a parent, so it interleaves tasks from different depths nonsensically.

## The Solution: Recursive CTE with sort_path

```sql
WITH RECURSIVE task_order(id, sort_path) AS (
    -- Anchor: project-root tasks (the task row that IS the project)
    SELECT t.persistentIdentifier,
           printf('%010d', t.rank + 2147483648)
    FROM Task t
    JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task

    UNION ALL

    -- Recursive: children, appending their shifted rank to the path
    SELECT t.persistentIdentifier,
           o.sort_path || '/' || printf('%010d', t.rank + 2147483648)
    FROM Task t
    JOIN task_order o ON t.parent = o.id
)
SELECT t.*
FROM Task t
JOIN task_order o ON t.persistentIdentifier = o.id
LEFT JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task
WHERE pi.task IS NULL
  -- ... additional WHERE conditions ...
ORDER BY o.sort_path
LIMIT ? OFFSET ?
```

### How it works
- **Anchor**: Every project-root task (has a ProjectInfo row) gets a sort_path of its own shifted rank
- **Recursive step**: Each child appends `/<shifted_rank>` to its parent's path
- **sort_path format**: `"2155970688/2155970688/2156036224"` — slash-separated, zero-padded to 10 digits
- **Rank shift**: `rank + 2147483648` converts signed 32-bit → unsigned so lexicographic sort is correct for negatives
- **Result**: `ORDER BY sort_path` produces depth-first traversal matching the OmniFocus outline view
- **Multi-project**: Tasks naturally group by project (each project's subtree shares a sort_path prefix)

## Findings by Entity Type

### Tasks

| Question | Finding |
|----------|---------|
| Does `rank` reproduce UI order within a parent? | **Yes.** OR-01→OR-05 exact UI order. Confirmed across all 4 nesting levels. |
| Is rank unique within parent? | **Yes.** Zero within-parent duplicates across 3062 tasks. Globally, rank=0 appears 334 times — always under different parents. |
| Rank value range/gaps? | Full signed 32-bit: -2,140,575,383 to 2,147,483,638. Consecutive siblings gap by 65536 (0x10000). Older data uses wider spacing (power-of-2 midpoint). |
| Negative ranks? | **935 tasks.** Normal — midpoint-insertion uses full signed range. |
| Does flat `ORDER BY rank` interleave depths? | **Yes.** rank=8487040 appears at depths 0, 1, 2, and 3. Flat ORDER BY rank is useless. |
| Sequential vs parallel: rank differs? | **No.** Both use the same integer rank. |
| `creationOrdinal` role? | **NULL for all test tasks.** Dead column for recent data. |

### Projects

| Question | Finding |
|----------|---------|
| Ordered by `rank` within folder? | **Yes.** 363 active projects, all correctly ordered. |
| Folder-less projects? | Rank unique within the `pi.folder IS NULL` group. |
| Rank unique within folder? | **Yes.** Zero duplicates. |

### Folders

| Question | Finding |
|----------|---------|
| Ordered by `rank` within parent? | **Yes.** 80 folders, zero within-parent duplicates. |
| Top-level ordering? | 7 top-level folders: Core, Life, Job, Hobby, Sandbox, Templates, Synced Preferences — correct by rank. |

### Tags (Context table)

| Question | Finding |
|----------|---------|
| Ordered by `rank` within parent? | **Yes.** 76 tags, zero within-parent duplicates. |
| Top-level ordering? | 28 top-level tags, all correct. |

### TaskToTag (join table)

| Question | Finding |
|----------|---------|
| `rankInTask` (TEXT) format? | **Binary-encoded bytes** (e.g. `\x00\x04`). Fractional-indexing scheme. Byte-level comparison = correct sort. |
| `rankInTag` (TEXT) format? | **Effectively unused.** NULL for 5001/5007 rows. |
| Controls tag display order? | **Yes** — `rankInTask` determines tag order on a task. `rankInTag` (tasks within tag view) is dead. |

## Performance

| Query | Avg | Min | Max |
|-------|-----|-----|-----|
| Full CTE (3062 tasks, ORDER BY sort_path) | 4.7ms | 3.8ms | 6.2ms |
| Simple ORDER BY rank, id (no CTE) | 1.2ms | 1.0ms | 1.5ms |
| CTE + project filter + available | 3.7ms | 3.2ms | 4.5ms |
| Lightweight CTE (sort_path only) + JOIN | 4.3ms | 3.6ms | 5.1ms |

**CTE overhead**: ~4x slower than simple ORDER BY, but only ~5ms absolute. Well under the 100ms target. No performance concern.

## Recommended ORDER BY Clauses for `query_builder.py`

### Tasks (the main one)

Prepend the lightweight CTE to every task query. Change the FROM/JOIN and add ORDER BY:

```python
_TASK_ORDER_CTE = (
    "WITH RECURSIVE task_order(id, sort_path) AS ("
    "  SELECT t.persistentIdentifier, printf('%010d', t.rank + 2147483648)"
    "  FROM Task t"
    "  JOIN ProjectInfo pi ON t.persistentIdentifier = pi.task"
    "  UNION ALL"
    "  SELECT t.persistentIdentifier,"
    "         o.sort_path || '/' || printf('%010d', t.rank + 2147483648)"
    "  FROM Task t"
    "  JOIN task_order o ON t.parent = o.id"
    ") "
)

# Then in build_list_tasks_sql:
# 1. Prepend _TASK_ORDER_CTE
# 2. Add JOIN: "JOIN task_order o ON t.persistentIdentifier = o.id"
# 3. Add: "ORDER BY o.sort_path" before LIMIT/OFFSET
```

### Projects

No CTE needed — projects are flat within folders:
```sql
ORDER BY pi.folder, t.rank ASC, t.persistentIdentifier ASC
```

### Folders

No CTE needed — direct parent-child:
```sql
ORDER BY f.parent, f.rank ASC, f.persistentIdentifier ASC
```

### Tags

No CTE needed — direct parent-child:
```sql
ORDER BY c.parent, c.rank ASC, c.persistentIdentifier ASC
```

## Edge Cases

- **Negative ranks**: Normal. The `+ 2147483648` shift in sort_path handles them correctly.
- **Inbox tasks (106 roots, 177 total)**: NOT reached by the project-anchored CTE. **Strategy B validated**: extend the CTE with a second anchor for inbox roots (`parent IS NULL AND containingProjectInfo IS NULL AND NOT a project`), prefix with `ZZZZZZZZZZ/` to sort after projects. Inbox has real nesting (up to 4 levels), and the recursive step handles it identically to project trees. One gotcha: the recursive step picks up completed children — filter with `dateCompleted IS NULL` in the outer WHERE (already done in the combined CTE). Performance: 0.8ms inbox-only, 6.0ms combined.
- **Orphan tasks (71 non-inbox)**: Parent exists in DB but parent itself is an orphan (cascading chain from deleted/corrupted project trees). Not reachable by CTE. These are edge-case data — not expected in normal operation.
- **Action groups**: Correctly traversed by the CTE recursive step (verified 10/10 sampled).
- **rank=0**: Most common global value (334 tasks) but always unique within parent. The CTE handles this fine since sort_path includes the full ancestor chain.

## Validated Assumptions

### 32-bit rank range — CONFIRMED SAFE

`printf('%010d', rank + 2147483648)` is safe. All tables fit within signed 32-bit:

| Table | Min rank | Max rank | Max shifted | Digits |
|-------|----------|----------|-------------|--------|
| Task | -2,140,575,383 | 2,147,483,638 | 4,294,967,286 | 10 |
| Folder | -2,143,888,531 | 2,118,123,520 | 4,265,607,168 | 10 |
| Context | -1,610,612,736 | 2,147,483,167 | 4,294,966,815 | 10 |

Max unsigned 32-bit = 4,294,967,295 = exactly 10 digits. SQLite's flexible INTEGER *could* store 64-bit, but OmniFocus uses midpoint insertion with 65536 gaps — a 32-bit scheme by design.

**Headroom note**: Task max rank is only 9 below the 32-bit ceiling (0 insertion slots). This isn't a problem — OmniFocus rebalances ranks during sync. But it confirms the scheme is 32-bit, not wider.

### `rankInTask` binary encoding — FULLY DECODED

Byte-level fractional indexing scheme:

- **Sequential tags**: 2-byte big-endian integers — `0x0001`, `0x0002`, `0x0003`, ...
- **Insertions**: 3rd midpoint byte — between `0x0003` and `0x0004` → `0x00033F` (63 ≈ 25% of `[0, 255]`)
- **Byte comparison**: `ORDER BY rankInTask` = correct sort order (verified: byte sort == integer sort)
- **Distribution**: 82% 2-byte (sequential), 18% 3-byte (insertions)
- **Older data**: Wider initial spacing (e.g. `0x9788`, `0xE8AC`) — same scheme, different starting points

For future writes: find neighbor bytes, compute midpoint. Same algorithm as integer rank, just in byte space. Standard fractional-indexing pattern (Figma, Google Docs, etc.).

### `rankInTag` — CONFIRMED DEAD

NULL for 5001/5007 rows (99.9%). OmniFocus does not persist custom task ordering within tag views. The 6 non-NULL values are likely legacy data.

## Model Impact

- Whether to expose `rank`/`position` on models → connects to [pending TODO](../../.planning/todos/pending/2026-03-08-add-position-field-to-expose-child-task-ordering.md)
  - Raw `rank` values (e.g. -1,342,177,280) are not human-friendly
  - Options: expose raw rank for sorting, or compute 1-based ordinal via `ROW_NUMBER() OVER (PARTITION BY parent ORDER BY rank)` — more useful for agents
  - The `sort_path` itself could be exposed if consumers need to compare positions across different parents

## Verification Checklist

- [x] CTE reproduces exact UI outline order — verified GM-TestProject (13 tasks, 4 levels) and GM-TestProject2 (4 tasks)
- [x] Multi-project queries group by project, maintain outline order within each
- [x] Deterministic pagination — `ORDER BY sort_path` with LIMIT/OFFSET produces stable pages
- [x] Negative ranks handled — `+ 2147483648` shift verified
- [x] Performance — 4.7ms avg for full CTE, well under 100ms target
- [x] Action groups — correctly traversed by recursive step
- [x] Works for all entity types — tasks (CTE), projects/folders/tags (simple `ORDER BY parent, rank`)

## Scripts

| Script | Phase | What it checks |
|--------|-------|---------------|
| `1-rank-analysis/rank_semantics.py` | 1 | Rank values, statistics, gaps, uniqueness |
| `1-rank-analysis/rank_range_validation.py` | 1+ | 32-bit range safety, printf overflow check |
| `2-hierarchy/hierarchy_ordering.py` | 2 | Flat vs CTE ordering, creationOrdinal, depth interleaving |
| `2-hierarchy/multi_project_cte.py` | 2+ | Multi-project CTE, filtered queries, performance, edge cases, proposed SQL |
| `3-other-entities/entity_ordering.py` | 3 | Projects, folders, tags, TaskToTag rank columns |
| `2-hierarchy/inbox_ordering.py` | 2+ | Inbox CTE, nesting depth, Strategy B combined CTE, coverage check |
| `3-other-entities/rankintask_decoding.py` | 3+ | rankInTask binary encoding, fractional indexing scheme, byte sort proof |

All scripts: read-only (`?mode=ro`), self-contained, runnable for verification.
