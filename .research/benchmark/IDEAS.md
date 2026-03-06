# Bridge Performance: Ideas to Explore

Captured from benchmark results (2026-03-06). Not urgent — revisit when
implementing writes or if cache hit rate proves insufficient.

## Benchmark Summary

~2000 tasks, OmniFocus 4, M-series Mac. Full results in two runs
(consistent across both).

| Variant | Internal (avg ms) | Delta from prev | Notes |
|---------|------------------|-----------------|-------|
| 01_noop | 0 | — | IPC baseline: ~130ms wall |
| 02a_iterate_only | 1322 | +1322 | Iteration floor (no property access) |
| 02_ids_only | 1420 | +98 | `.id.primaryKey` costs ~100ms |
| 03_core | 1471 | +51 | name/note: ~50ms for 500KB more data |
| 04_with_dates | 1727 | +256 | `toISOString()` on all dates |
| 05_with_enums | 1814 | +87 | Enum comparisons |
| 09_no_relations | 1864 | +50 | Full data minus all relationships |
| 06_tasks_only | 2583 | — | Full tasks, empty others |
| 08_filtered | 2301 | — | Full snapshot, skip completed/dropped |
| 07_full | 2701 | — | Baseline |

### Key deltas

| What | Cost (ms) | How measured |
|------|-----------|-------------|
| Object hydration (iteration floor) | 1322 | 02a |
| All relationship traversal | **837** | 07 − 09 |
| Filtering completed/dropped | **−400** | 07 − 08 (only 15% faster) |
| Non-task entities | 118 | 07 − 06 |

## Idea 1: Derive relationships in Python

**Benchmark result**: Dropping ALL relationships saves 837ms (07→09:
2701→1864ms). That's 31% — meaningful but not transformative.

**Problem**: We can't simply drop relationships. Tasks need project,
parent, and tag associations. The question is whether we can get them
more cheaply.

### What we can definitely drop

- **url**: Constructible from primary key in Python. Free savings on
  every entity. (Need to verify exact URL format matches.)

### What needs an alternative data source

- **task→tags**: The bridge currently does `t.tags.map()` for each of
  ~2000 tasks. Alternative: build the mapping from the **tag side** —
  iterate ~50 tags, access `tag.tasks` to get associated task PKs, then
  invert in Python. Fewer traversals if tag count << task count. BUT:
  `tag.tasks` may return full task objects, triggering the same hydration.
  **Needs a benchmark variant to verify.**
- **task→project / task→parent**: `pk(t.containingProject)` and
  `pk(t.parent)` follow object references. These can't be inferred from
  other data without the bridge providing them — a task's project isn't
  knowable from the project list alone. Could try: a single pass that
  returns just `{taskPk, projectPk, parentPk}` tuples as a flat array,
  separate from the main mapping. Unclear if this would be cheaper.
- **project→folder, tag→parent, folder→parent**: Same issue — graph
  edges that only the bridge knows.

### Verdict

Partial wins are possible (url, maybe tags), but the core relationships
(parent, project) must come from the bridge. Estimated realistic savings:
200-400ms. Only pursue if cache misses become a pain point.

## Idea 2: Filter at OmniFocus level

**Benchmark result**: 08_filtered saves only ~400ms (15%) despite
filtering out a significant number of tasks. The `.filter()` call still
iterates every object (triggering hydration), so we only save the
per-object mapping cost on filtered-out tasks — NOT the hydration cost.

**Conclusion**: Filtering is a modest win, not a game-changer. The
hydration floor dominates regardless. Still worth offering as a
`snapshot({includeCompleted: false})` parameter if the agent doesn't
need completed tasks, but don't expect dramatic improvement.

## Idea 3: Write invalidation strategies

Read-only is solved: load cache once, read forever in Python. Writes are
the hard problem. Options to explore:

### 3a. Optimistic write-through

1. Agent requests a write (e.g., complete task X)
2. Bridge executes the write in OmniFocus
3. Python updates its local cache optimistically (mark X as completed)
4. No full re-snapshot needed

**Pro**: Writes are fast (~200ms for IPC + single mutation).
**Con**: Cache can drift if OmniFocus applies side effects we don't model
(e.g., completing a parent task when all children are done, project status
changes, repeating tasks spawning new instances).

### 3b. Write then selective re-read

1. Bridge executes the write
2. Bridge returns the affected object(s) in the response — re-read just
   the modified task/project, not a full snapshot
3. Python patches its cache with the returned data

**Pro**: Catches OmniFocus-applied side effects on the modified object.
**Con**: Doesn't catch cascade effects on *other* objects (parent status,
project completion). Could miss OmniFocus-generated objects (new repeating
task instance).

### 3c. Write then full re-snapshot

1. Bridge executes the write
2. Immediately do a full snapshot refresh

**Pro**: Guarantees consistency. Simple.
**Con**: Every write costs 2.7s. If the agent does 5 writes in a row
(batch task creation), that's 13.5s of blocking.

### 3d. Write-batch then snapshot

1. Queue multiple writes, execute them all in one bridge call
2. Single snapshot refresh after the batch completes

**Pro**: Amortizes the 2.7s cost across N writes.
**Con**: More complex IPC protocol. Partial failure semantics (what if
write 3 of 5 fails?).

### 3e. Dirty flag + lazy refresh

1. Writes execute immediately, mark cache as dirty
2. Cache stays dirty until next read operation
3. Next read triggers a re-snapshot before returning

**Pro**: No wasted refreshes if agent does write-write-write-read.
**Con**: First read after writes is slow. Agent might not expect that.

### 3f. Bridge-side guard rails

Regardless of invalidation strategy, the bridge should reject writes
that reference stale state:

- **Existence check**: Before modifying task X, verify X still exists
  and is in the expected state. Return a clear error if not. This is
  cheap — single object lookup by PK in OmniFocus.
- **Version/sequence number**: Snapshot includes a monotonic version.
  Write requests carry the version they're based on. Bridge rejects if
  OmniFocus state has changed. (May be overkill for v1.)

This doesn't solve cache freshness but prevents silent corruption.

## Recommended approach

For the initial write implementation, start with **3e (dirty flag + lazy
refresh)** combined with **3f (guard rails)**:

- Simple to implement
- No wasted re-snapshots during write bursts
- Guard rails catch the dangerous edge cases (writing to deleted tasks)
- Can upgrade to 3a (optimistic) or 3d (batching) later if perf matters

The 2.7s refresh cost only matters if the agent frequently interleaves
reads and writes. In practice, agents tend to batch: read state, think,
execute several writes, read state again. The dirty-flag approach aligns
naturally with this pattern.

## Open questions

- Does `tag.tasks` trigger per-task hydration, or are tasks already
  cached by the OmniFocus runtime after `flattenedTasks` iteration?
  (Benchmark variant needed.)
- What is the exact OmniFocus URL format? Is `omnifocus:///task/{pk}`
  correct, or does it use a different scheme?
- How does OmniFocus handle concurrent access — if the user modifies
  tasks in the UI while the agent is writing, what happens?
