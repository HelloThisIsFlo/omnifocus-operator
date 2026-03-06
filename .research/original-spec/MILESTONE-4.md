# Milestone 4 — Perspectives & Field Selection

## Goal

The agent can see what the user sees in OmniFocus, switch perspectives, and request only the fields it needs to save tokens. This milestone introduces the first UI-aware tools and adds token efficiency across all read tools.

## What to Build

### Perspective Interaction

**`list_tasks(current_perspective_only: true)`** — reads live from the OmniFocus UI instead of the snapshot. The service layer calls the bridge directly (bypasses the repository — see architecture note below). Tasks are returned in the same Pydantic shape as snapshot tasks, including availability/urgency. All existing filters work on top of the perspective results. When computing availability/urgency for perspective tasks, the service layer uses the snapshot for cross-entity lookups (parent tasks, sequential siblings, project metadata). The perspective provides the task list; the snapshot provides the context for semantic status.

**`get_current_perspective()`** — returns the name of the currently active perspective in OmniFocus. Read-only, no side effects. Bridge call: `document.windows[0].perspective.name`.

**`show_perspective(name)`** — switches the user's active perspective in OmniFocus. Takes a perspective name (string, case-sensitive). Works for built-in and custom perspectives. This is the first tool with a visible UI side effect — the tool description must make this clear.

If the perspective isn't found: return an error directing the agent to `list_perspectives()`.

### Architecture: UI Operations Bypass the Repository

This milestone introduces a second data path. The service layer gets a reference to the bridge (alongside its existing repository reference) for UI commands only:

- **Data operations** (existing): MCP → Service → Repository → Bridge
- **UI operations** (new): MCP → Service → Bridge (no snapshot involvement)

UI operations don't affect the snapshot and aren't cached.

### Bridge Script Changes

Three new commands added to the bridge script:

**`read_view`** — reads `document.windows[0].content.rootNode.children`, recursively traversing the content tree to extract Task objects. Returns tasks in the same format as the dump (same fields, same serialization helpers). Projects in the view are silently skipped — only tasks are returned.

**`set_perspective`** — looks up a perspective by name across `Perspective.all`, sets `document.windows[0].perspective` to the match. Returns success or error.

**`get_perspective`** — returns `document.windows[0].perspective.name`. Simple read, no side effects.

These go through the same file-based IPC as other bridge commands. No dedup lock needed — UI operations capture live state, and parallel perspective reads are unlikely.

### Field Selection

An optional `fields` parameter (list of field name strings) on all `list_*` and `get_*` tools. When provided, only those fields plus `id` (always included) are returned.

Rules:
- `id` is always included, even if not listed.
- Invalid field names are silently ignored with a server-side warning log.
- Field names use snake_case (matching Pydantic model names).
- `availability` and `urgency` are independent top-level fields — each can be requested individually.
- Nested objects (`review_interval`, `repetition_rule`) are atomic — no sub-field selection. Request the top-level name, get the full object.
- Projection happens post-filter, pre-serialization. Filters run against full objects — you can filter on `flagged` without including it in the output fields.
- Omitting `fields` returns everything (fully backward compatible).

## Key Acceptance Criteria

- `list_tasks(current_perspective_only: true)` returns live perspective tasks with the same Task model shape (including availability/urgency).
- `current_perspective_only` combines with all existing filters.
- Default `list_tasks()` (without `current_perspective_only`) works exactly as before — no behavior change.
- `show_perspective` visibly switches the OmniFocus perspective. Works for both built-in and custom.
- `get_current_perspective` returns the active perspective name.
- Unknown perspective returns a clear error directing to `list_perspectives()`.
- Perspective name matching is case-sensitive.
- Task serialization from `read_view` matches the dump format exactly.
- Field projection works on all `list_*` and `get_*` tools.
- `id` always included in projected output.
- Invalid field names don't break results (warning logged).
- Projection doesn't affect filtering — can filter on fields not in output. Specifically: filtering on `availability` or `urgency` works even when those fields are excluded from `fields`; the response contains only the requested fields plus `id`.
- Tool descriptions make clear that `current_perspective_only` reads live from OmniFocus UI and that `show_perspective` changes what the user sees.

## Tools After This Milestone

Thirteen: `list_all`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `get_task`, `get_project`, `get_tag`, `count_tasks`, `count_projects`, `show_perspective`, `get_current_perspective`.
