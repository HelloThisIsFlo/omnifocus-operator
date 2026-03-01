# Milestone 5 — Writes [DRAFT]

## Goal

The server can create, edit, and delete tasks, and create and edit projects in OmniFocus. This milestone establishes the full write pipeline and completes the 17-tool API surface. After this, the daily review agent can do everything it needs without the user touching OmniFocus directly.

This is a draft milestone with open questions that will be resolved during GSD's discuss phase or during implementation. The structure below captures what's decided and flags what isn't.

## What to Build

### Write Pipeline

All write operations follow the same flow:

1. MCP tool receives the request (array of items)
2. Service layer validates against the snapshot (required fields, IDs exist, tags exist)
3. Service calls the bridge once per item — write payload goes in the request file (not the argument string)
4. After success, service tells the repository to mark the snapshot as stale
5. Next read triggers a fresh dump (lazy invalidation — not in-place update)

The bridge gains a `readRequest(id)` helper to read payloads from request files. Read operations still encode everything in the argument string; writes use request files because payloads are larger and more complex.

### Task Creation & Deletion

**`add_tasks([...])`** — creates tasks. Fields per item: `name` (required), `project` (ID), `parent_task_id` (ID, mutually exclusive with project), `tags` (names, must exist), `due_date`, `defer_date`, `planned_date`, `flagged`, `estimated_minutes`, `note`. If no project or parent_task_id, the task goes to inbox. Returns `[{ success, id, name }]`.

**`delete_tasks([...])`** — permanently removes tasks by ID. Deleting a parent task removes all children. Returns `[{ success }]`.

Both tools take and return arrays. Start with a single-item constraint (array of exactly one), then extend to batch once the pipeline is proven.

### Task Editing

**`edit_tasks([{ id, changes: {...} }])`** — modifies tasks using patch semantics:
- **Omit** a field = no change
- **`null`** = clear the field (e.g., `due_date: null` removes the deadline)
- **A value** = set it

The bridge implements this via `hasOwnProperty` checks on the changes object.

**Editable fields:** name, note, due_date, defer_date, planned_date, flagged, estimated_minutes, project (ID or null → inbox), parent_task_id (ID or null → un-nest), tags/add_tags/remove_tags (three mutually exclusive modes), availability (settable to `active`, `completed`, or `dropped` to change lifecycle state — note: the read model's computed values like `available`, `next`, `blocked` are NOT settable and are rejected as validation errors).

**Tag editing modes:**
- `tags: [...]` — replace all tags
- `add_tags: [...]` — append without removing
- `remove_tags: [...]` — remove specific tags
- `add_tags` + `remove_tags` together is allowed (remove first, then add — add wins on conflicts)
- `tags` with `add_tags` or `remove_tags` is a validation error

Same single-item-first pattern as creation/deletion — start with one, extend to batch.

### Project Creation & Editing

**`add_projects([...])`** — creates projects. Fields: `name` (required), `folder` (ID), `type` (`parallel`/`sequential`/`single_action`, default parallel), `due_date`, `defer_date`, `planned_date`, `flagged`, `estimated_minutes`, `note`, `tags`, `review_interval` ({steps, unit}).

**`edit_projects([{ id, changes: {...} }])`** — same patch semantics as task editing. Additional project-specific fields: `status` (`active`/`on_hold`/`done`/`dropped`), `type`, `folder` (ID or null → root), `review_interval` (object or null → reset to default), `reviewed` (`true` only — marks the project as reviewed, advancing next_review_date).

No `delete_projects` — project deletion is always manual in OmniFocus.

### Batch Operations

Items in a batch must be independent — no item can reference another item being created in the same batch. If an agent needs to create a parent→child hierarchy, it makes sequential tool calls.

## Open Questions

These will be resolved during GSD's discuss phase or during implementation:

### Partial Failure
When item 2 of 5 fails in a batch, what happens to items 3–5? Options under consideration:
- **Best effort** — continue processing, report per-item results
- **Stop on first failure** — simpler but loses work
- OmniFocus doesn't support transactions, so true rollback isn't possible

### Response Format for Batch Writes
Two options considered: (a) top-level success + data array, or (b) separate `added`/`errors` lists. Single-item uses option (a) trivially; batch shape needs a decision.

### Eager vs Lazy Snapshot Refresh
After invalidating the snapshot, should we trigger a background dump immediately (reduces latency on next read) or wait for the next read (simpler)? Leaning lazy.

### Bridge JS API Verification Needed
Several OmniFocus JS API calls in the bridge sketches are unverified:
- Task movement between projects (`assignedContainer`? `moveTasks`?)
- Un-nesting a task (`parent_task_id: null` intent)
- `markIncomplete()` on an already-incomplete task (does it throw?)
- Clearing fields with `null` assignment (vs separate clear methods)
- `Project.Status` enum for status changes
- `Project.ReviewInterval` constructor
- `deleteObject()` for task deletion
- Folder movement for projects

### Project Writes Sub-Split
Whether project writes need a single/batch sub-split is TBD. By the time we get here, batching is a proven pattern — may not need a separate phase.

### Mid-Edit Failures
A single edit can fail partway through its fields (e.g., tag replacement succeeds but movement fails). The bridge processes fields sequentially with no transaction. Known limitation — document it, don't over-engineer around it.

### Stale Snapshot During Sequential Writes
If an agent creates a parent task then immediately creates a child with the parent's ID, the child's validation checks a stale snapshot. The repository will trigger a fresh dump (~2.7s latency). Correct behavior, just worth noting.

## Key Acceptance Criteria

- Write pipeline works end-to-end: create a task, then verify it appears in `list_tasks`.
- Snapshot invalidation: after any successful write, the next read returns fresh data.
- Validation catches errors before hitting the bridge (missing name, unknown tags, mutually exclusive fields).
- Patch semantics work: omit leaves unchanged, null clears, value sets.
- All three tag editing modes work correctly with proper conflict resolution.
- Task lifecycle changes work: mark complete, drop, reactivate.
- Setting `availability: "available"` or `"next"` (computed values) is a validation error.
- Project creation with type, folder, and review interval.
- `reviewed: true` advances the review schedule.
- Deletion is permanent and removes children.
- Bridge reads payloads from request files correctly.
- Tool descriptions warn about permanent deletion and emphasize patch semantics.

## Tools After This Milestone

Eighteen (full API surface): all thirteen from Milestone 4, plus `add_tasks`, `delete_tasks`, `edit_tasks`, `add_projects`, `edit_projects`.

## Future Milestones (Not Planned for GSD Yet)

- **TaskPaper Output**: Alternative serialization format (~5x token reduction). Same data, different shape. Server config flag.
- **Production Hardening**: Retry logic, OmniFocus launch detection, configurable timeout, crash recovery, idempotency, startup validation.
