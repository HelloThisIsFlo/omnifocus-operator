# Milestone v1.2 -- Writes & Lookups

## Goal

The server can look up individual entities by ID and create/edit tasks in OmniFocus. This milestone validates the write pipeline end-to-end -- the riskiest remaining architecture. After this, an agent can add tasks to inbox, set deadlines, move tasks between projects, and edit any task field.

Get-by-ID tools land first as a quick win and to enable clean write validation (instead of parsing the full 2.7MB `list_all` dump).

## What to Build

### Get-by-ID Tools

**`get_task(id)`**, **`get_project(id)`**, **`get_tag(id)`** -- look up one item by primary key. Returns the full object (same shape as `list_all` results, including computed fields like urgency/availability). If not found: clear error message.

**Implementation paths:**
- **HybridRepository (SQLite)**: `SELECT ... WHERE persistentIdentifier = ?` -- single row lookup
- **BridgeRepository**: Dict lookup from the in-memory snapshot (get full snapshot, index by ID)
- **InMemoryRepository**: Dict lookup from test data

These are the simplest possible MCP tools -- warm-up before write complexity.

### Write Pipeline

All write operations follow the same flow:

```
MCP tool -> Service (validate) -> Repository -> Bridge (execute) -> invalidate snapshot
```

1. MCP tool receives the request (array of items)
2. Service layer validates against the current snapshot (required fields, IDs exist, tags exist)
3. Repository delegates to the bridge -- write payload goes in the request file (not the argument string)
4. After success, repository marks the snapshot as stale
5. Next read detects staleness and loads fresh data:
   - HybridRepository: WAL mtime detection (already implemented in v1.1)
   - BridgeRepository: OmniFocus database mtime (already implemented in v1.0)

The bridge gains new commands (`add_task`, `edit_task`) and reads payloads from request files. Read operations still encode everything in the argument string; writes use request files because payloads are larger and more complex.

### Task Creation

**`add_tasks([...])`** -- creates tasks in OmniFocus. Fields per item:

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `name` | string | Yes | Task name |
| `project` | ID | No | Project to add to (mutually exclusive with `parent_task_id`) |
| `parent_task_id` | ID | No | Parent task (mutually exclusive with `project`) |
| `tags` | list of names | No | Must exist in OmniFocus |
| `due_date` | ISO8601 | No | |
| `defer_date` | ISO8601 | No | |
| `planned_date` | ISO8601 | No | |
| `flagged` | bool | No | |
| `estimated_minutes` | int | No | |
| `note` | string | No | |

- If no `project` or `parent_task_id`, the task goes to inbox
- Returns `[{ success, id, name }]`
- MCP tool takes and returns arrays (plural: `add_tasks`)
- Start with single-item constraint (array of exactly one), extend to batch once pipeline is proven

### Task Editing

**`edit_tasks([{ id, changes: {...} }])`** -- modifies tasks using patch semantics:
- **Omit** a field = no change
- **`null`** = clear the field (e.g., `due_date: null` removes the deadline)
- **A value** = set it

The bridge implements this via `hasOwnProperty` checks on the changes object.

**Editable fields (simple -- implement first):**

| Field | Type | Notes |
|-------|------|-------|
| `name` | string | |
| `note` | string or null | |
| `due_date` | ISO8601 or null | |
| `defer_date` | ISO8601 or null | |
| `planned_date` | ISO8601 or null | |
| `flagged` | bool | |
| `estimated_minutes` | int or null | |
| `project` | ID or null | Moves task. null = move to inbox |
| `parent_task_id` | ID or null | Re-parents task. null = un-nest |
| `tags` | list | Replace all tags |
| `add_tags` | list | Append without removing |
| `remove_tags` | list | Remove specific tags |

**Tag editing modes (mutually exclusive):**
- `tags: [...]` -- replace all tags
- `add_tags: [...]` -- append without removing
- `remove_tags: [...]` -- remove specific tags
- `add_tags` + `remove_tags` together is allowed (remove first, then add -- add wins on conflicts)
- `tags` with `add_tags` or `remove_tags` is a validation error

**Editable fields (lifecycle -- implement after research spike):**

| Field | Type | Notes |
|-------|------|-------|
| `availability` or TBD | enum | Lifecycle change: complete, drop, reactivate |

The lifecycle interface (field edit vs action-style API) is an open question. Before implementing, do a research spike on how OmniJS handles task completion, dropping, and reactivation. Investigate:
- What API does OmniJS expose? (`markComplete()`, `Task.Status`, direct property assignment?)
- What's the recommended approach?
- How do repeating tasks behave? (complete this instance vs complete the series)

### Bridge Script Changes

New commands added to the bridge script:

- **`get_task`** / **`get_project`** / **`get_tag`** -- per-entity lookup (can use existing dump logic filtered to one item, or direct lookup)
- **`add_task`** -- reads payload from request file, creates task, returns `{ success, id, name }`
- **`edit_task`** -- reads payload from request file, applies changes via `hasOwnProperty` checks, returns success/error

Write commands read their payload from the request file. Read commands (get-by-ID) can encode the ID in the argument string (existing pattern).

## Phasing Hint

Split implementation into phases ordered by complexity:

1. **Get-by-ID tools** (warm-up, low risk) -- `get_task`, `get_project`, `get_tag`
2. **`add_tasks`** (straightforward creation)
3. **`edit_tasks` -- simple field edits** (name, note, due_date, defer_date, flagged, estimated_minutes, tags, project/parent movement)
4. **`edit_tasks` -- lifecycle changes** (complete, drop, reactivate) -- after a research spike on OmniJS APIs to determine the right interface

## Open Questions

Carried from the original Milestone 5 spec. Resolve during planning or implementation.

### Partial Failure
When item 2 of 5 fails in a batch, what happens to items 3-5?
- **Best effort** -- continue processing, report per-item results
- **Stop on first failure** -- simpler but loses work
- OmniFocus doesn't support transactions, so true rollback isn't possible

### Batch Response Format
Two options: (a) top-level success + data array, or (b) separate `added`/`errors` lists. Single-item uses option (a) trivially; batch shape needs a decision.

### Bridge JS API Verification
Several OmniFocus JS API calls need verification before implementation:
- Task movement between projects (`assignedContainer`? `moveTasks`?)
- Un-nesting a task (`parent_task_id: null` intent)
- Clearing fields with `null` assignment (vs separate clear methods)
- `markIncomplete()` on an already-incomplete task (does it throw?)

### Repeating Task Edge Cases
- Completing a repeating task: does it complete this instance or the whole series?
- Dropping a repeating task: same question
- What API does OmniJS expose for this distinction?

### Lifecycle Interface
- Should task lifecycle changes (complete, drop, reactivate) go through an `availability` field in the edit payload, or through a separate action-style interface?
- Research spike needed before implementing (see Phasing Hint, phase 4)

## Key Acceptance Criteria

- `get_task` with a known ID returns the full Task object with availability/urgency. Unknown ID returns a clear error.
- `get_project` and `get_tag` follow the same pattern.
- Write pipeline works end-to-end: create a task via `add_tasks`, then verify it appears via `get_task` with the returned ID.
- Snapshot invalidation: after any successful write, the next read returns fresh data.
- Validation catches errors before hitting the bridge (missing name, unknown tags, mutually exclusive fields like project + parent_task_id, tags + add_tags).
- Patch semantics work: omit leaves unchanged, null clears, value sets.
- All three tag editing modes work correctly with proper conflict resolution.
- Task movement works: change project, re-parent, move to inbox.
- Bridge reads payloads from request files correctly.
- Tool descriptions are detailed enough for an LLM to call correctly.

## Tools After This Milestone

Six: `list_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`.

## Not Included (Deferred)

- `delete_tasks` -- deferred to v1.4. Strong `edit_tasks` with move/re-parent makes delete less urgent.
- `add_projects`, `edit_projects` -- deferred to v1.4. Project writes have unverified OmniJS APIs (Project.Status, Project.ReviewInterval, markReviewed) and are low priority for the user's workflow (tasks are promoted to projects manually).
