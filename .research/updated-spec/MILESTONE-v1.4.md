# Milestone v1.4 -- Output, UI & Remaining Tools

## Goal

Complete the full 18-tool API surface. The agent can see what the user sees in OmniFocus, switch perspectives, request only the fields it needs, get output in TaskPaper format for token efficiency, and manage projects. After this milestone, the server exposes everything the daily review agent needs.

## What to Build

### Perspective Interaction

**`get_current_perspective()`** -- returns the name of the currently active perspective in OmniFocus. Read-only, no side effects. Bridge call: `document.windows[0].perspective.name`.

**`show_perspective(name)`** -- switches the user's active perspective in OmniFocus. Takes a perspective name (string, case-sensitive). Works for built-in and custom perspectives. This is the first tool with a visible UI side effect -- the tool description must make this clear. If the perspective isn't found: return an error directing the agent to `list_perspectives()`.

**`list_tasks(current_perspective_only: true)`** -- reads live from the OmniFocus UI instead of the snapshot. The service layer calls the bridge directly (bypasses the repository -- UI operations capture live state). Tasks are returned in the same Task model shape, including availability/urgency. All existing filters work on top of the perspective results.

When computing availability/urgency for perspective tasks, the service layer uses the snapshot for cross-entity lookups (parent tasks, sequential siblings, project metadata). The perspective provides the task list; the snapshot provides the context.

**Architecture: UI Operations Bypass the Repository**

This milestone introduces a second data path:
- **Data operations** (existing): MCP -> Service -> Repository -> Bridge/SQLite
- **UI operations** (new): MCP -> Service -> Bridge (no snapshot involvement)

UI operations don't affect the snapshot and aren't cached.

**Bridge script changes:**
- **`read_view`** -- reads `document.windows[0].content.rootNode.children`, traverses content tree to extract Task objects. Returns tasks in the same format as the dump. Projects in the view are silently skipped.
- **`set_perspective`** -- looks up perspective by name across `Perspective.all`, sets it on `document.windows[0]`. Returns success or error.
- **`get_perspective`** -- returns `document.windows[0].perspective.name`.

### Field Selection

Optional `fields` parameter (list of field name strings) on all `list_*` and `get_*` tools. When provided, only those fields plus `id` (always included) are returned.

**Rules:**
- `id` is always included, even if not listed
- Invalid field names are silently ignored with a server-side warning log
- Field names use snake_case (matching Pydantic model names)
- `availability` and `urgency` are independent top-level fields
- Nested objects (`review_interval`, `repetition_rule`) are atomic -- no sub-field selection
- Projection happens post-filter, pre-serialization. Filters run against full objects.
- Omitting `fields` returns everything (backward compatible)

### TaskPaper Output Format

Alternative serialization format offering ~5x token reduction. Same data, different shape.

**Configuration:** Server-level setting (env var or config flag -- TBD). When active, all read tools return TaskPaper-formatted strings instead of JSON.

**Important:** TaskPaper must carry hierarchy information by default. The format naturally does this via indentation — ensure this is preserved so agents can see parent/child structure without extra queries. This complements the `order` integer field (v1.3) which provides programmatic ordering.

**Note:** Existing research on TaskPaper format lives in the co-work folder. Refer to that research during planning -- do not re-spec from scratch.

**Unknowns:**
- Exact TaskPaper format specification (refer to existing research)
- How field selection interacts with TaskPaper output
- Whether TaskPaper should be per-tool or server-wide

### Project Writes (Deferred from v1.2)

**`add_projects([...])`** -- creates projects. Fields: `name` (required), `folder` (ID), `type` (`parallel`/`sequential`/`single_action`, default parallel), `due_date`, `defer_date`, `planned_date`, `flagged`, `estimated_minutes`, `note`, `tags`, `review_interval` ({steps, unit}).

**`edit_projects([{ id, changes: {...} }])`** -- same patch semantics as `edit_tasks`. Additional project-specific fields:
- `status` (`active`/`on_hold`/`done`/`dropped`) -- needs `Project.Status` enum in OmniJS (**unverified**)
- `type` (parallel/sequential/single_action) -- sets `sequential` + `containsSingletonActions`
- `folder` (ID or null -> root) -- folder movement
- `review_interval` (object or null -> reset to default) -- needs `Project.ReviewInterval` constructor (**unverified**)
- `reviewed` (`true` only) -- marks project as reviewed, advancing next_review_date (**unverified**: likely `markReviewed()`)

No `delete_projects` -- project deletion is always manual in OmniFocus.

**Prerequisite:** OmniJS API verification spike for the three unverified APIs before implementation.

### Task Deletion (Deferred from v1.2)

**`delete_tasks([...])`** -- permanently removes tasks by ID. Deleting a parent task removes all children. Returns `[{ success }]`.

The tool description must warn about permanent deletion.

### Mutually Exclusive Tag Enforcement

OmniJS allows assigning multiple mutually exclusive sibling tags to a task. OmniFocus only enforces exclusivity at the UI level. Agents using `add_tasks` or `edit_tasks` can create tasks in states the UI wouldn't normally allow.

- Investigate whether tag exclusivity metadata is accessible via OmniJS or SQLite
- Decide: validate before writing, or warn after?
- Low severity -- OmniFocus self-corrects when user later touches the tag group via UI

See: `2026-03-08-enforce-mutually-exclusive-tags-at-service-layer.md`

## Key Acceptance Criteria

- `show_perspective` visibly switches the OmniFocus perspective (built-in and custom)
- `get_current_perspective` returns the active perspective name
- `list_tasks(current_perspective_only: true)` returns live perspective tasks with the same Task model shape
- `current_perspective_only` combines with all existing filters
- Default `list_tasks()` (without `current_perspective_only`) works exactly as before
- Unknown perspective returns a clear error directing to `list_perspectives()`
- Field projection works on all `list_*` and `get_*` tools
- `id` always included in projected output
- Projection doesn't affect filtering
- Project creation with type, folder, and review interval works
- `reviewed: true` advances the review schedule
- Task deletion is permanent and removes children
- All 18 tools work end-to-end

## Tools After This Milestone

Eighteen (full API surface): all thirteen from v1.3, plus `show_perspective`, `get_current_perspective`, `add_projects`, `edit_projects`, `delete_tasks`.
