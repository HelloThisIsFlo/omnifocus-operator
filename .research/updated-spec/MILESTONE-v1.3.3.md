# Milestone v1.3.3 -- Ordering & Move Fix

## Goal

Agents can see child task ordering and reliably reorder tasks within the same container. After this milestone, `get_task` and `list_tasks` responses include an `order` field, and `moveTo beginning/ending` works correctly even when the task is already in the target container. Depends on v1.3 query infrastructure. No new tools -- enhances existing tools.

## What to Build

### Add `order` Field to Task Responses

Expose child ordering via an integer field on task responses so agents can see sibling positioning.

- Read-only, informational -- not settable via `edit_tasks`
- When listing children of a parent, return them in display order with `order`
- Example: `[{"id": "abc", "name": "Design", "order": 0, "parent": {"id": "xyz", ...}}, ...]`
- Independent of actions.move -- purely read-side
- `order` is for programmatic use; visual hierarchy (e.g., TaskPaper) is a maybe-idea

**Research findings** (from [deep dive](../deep-dives/direct-database-access-ordering/RESULTS.md)):
- SQLite `rank` column is unique within parent, uses signed 32-bit with 65536 gaps between siblings
- Raw rank values (e.g. -1,342,177,280) are not agent-friendly — compute 1-based ordinal via `ROW_NUMBER() OVER (PARTITION BY parent ORDER BY rank)`
- Flat `ORDER BY rank` interleaves tasks from different depths — a recursive CTE with `sort_path` is needed for correct outline order across nesting levels
- CTE performance: ~5ms for 3062 tasks, well under 100ms target
- Inbox tasks need a second CTE anchor with `ZZZZZZZZZZ/` prefix to sort after projects
- Negative ranks, drag-and-drop reordering, action groups — all verified correct
- Projects/folders/tags are simpler — just `ORDER BY parent, rank` (no CTE needed)

See: `2026-03-08-add-position-field-to-expose-child-task-ordering.md`

### Fix Same-Container Move

When a task is already in a container and you call `moveTo beginning/ending` on that same container, OmniFocus API silently does nothing. Manually verified: `moveBefore`/`moveAfter` within the same container DOES work (confirmed 2026-03-12).

**Service-layer translation** -- express the same intent through equivalent API calls:

- **"Move to beginning of X"** -> find X's first child -> call **"move before [first child]"**
- **"Move to ending of X"** -> find X's last child -> call **"move after [last child]"**

**Scope: always-when-children-exist** (not just same-container):
- Apply translation whenever the target container has children, regardless of whether the task is already there
- One code path instead of two (no same-vs-different-container branching)
- Semantically identical from the caller's perspective

**Edge cases:**
- **Container has no children** -> no translation needed (`moveTo beginning/ending` on empty container works fine)
- **Batch moves** -> each sequential move needs re-query to find updated first/last child (acceptable with SQLite cache ~46ms)

**Implementation:** Service layer (`edit_tasks` flow). Bridge stays dumb -- receives `moveBefore`/`moveAfter`, which it already supports. No bridge changes needed.

**Dependency:** Requires query infrastructure from v1.3 to cheaply look up "first/last child of container X" without pulling the entire database.

**Verified**: `moveBefore`/`moveAfter` within the same container confirmed working via manual testing (2026-03-12). First/last child lookup uses `MIN(rank)`/`MAX(rank)` within parent — rank is unique within parent (zero duplicates across 3062 tasks, see [deep dive](../deep-dives/direct-database-access-ordering/RESULTS.md)).

See: `2026-03-12-fix-same-container-move-by-translating-to-movebefore-moveafter.md`

### Improve Move No-Op Warning Accuracy

Current move no-op detection only checks if the task is already a child of the target parent. It doesn't distinguish beginning vs ending position -- moving the last child to "beginning" gets flagged as a no-op when it would actually reorder.

**Fix:** Query sibling order via `rank` column to determine current ordinal position. Compare requested position against actual position before flagging no-op. Specifically: "beginning" is no-op only if task has `MIN(rank)` among siblings; "ending" only if `MAX(rank)`.

**Dependency:** Shares ordering data infrastructure with the `order` field and same-container move fix — all three use rank-within-parent queries.

See: `2026-03-09-move-no-op-warning-check-ordinal-position-not-just-container.md`

## Scope Decisions

- **Cross-path equivalence for ordering is relaxed.** If the bridge fallback returns siblings in a slightly different order than SQLite, that's acceptable. The bridge path is a degraded mode — correctness matters for filtering, not display order.
- **Batch re-query cost on bridge path is acceptable.** Each sequential move in a batch needs a fresh child list lookup. On SQLite (~46ms) this is negligible. On bridge-only mode it's slower, but since bridge is a fallback, degraded performance there is fine.
- **No new unknowns.** All three features share rank-within-parent infrastructure. The ordering deep dive (2026-03-31) answered every open question — CTE solution, performance, edge cases, inbox handling. The same-container move was manually verified (2026-03-12). This milestone is pure execution.

## Key Acceptance Criteria

- Task responses include an `order` integer field reflecting display order within the parent
- Siblings under the same parent have sequential, gap-free order values
- `moveTo beginning` on the same container reorders the task to first position (not silently ignored)
- `moveTo ending` on the same container reorders the task to last position
- Move to beginning/ending on a different container works as before (no regression)
- Move to empty container works without translation (no first/last child to reference)
- No-op warning only fires when the task is already in the requested position (not just the same container)
- All existing move and edit tests continue to pass

## Tools After This Milestone

Eleven (unchanged from v1.3.2): `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`.
