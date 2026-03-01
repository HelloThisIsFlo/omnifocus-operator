# Milestone 3 — Entity Browsing & Lookups

## Goal

The agent can explore the full organizational structure — projects, tags, folders, perspectives — and drill into specific items by ID or get quick counts. After this milestone, the agent can ask "which projects are due for review?", "how many overdue tasks?", or look up a specific task by ID.

## What to Build

### Four New List Tools

**`list_projects(...)`** with filters:

| Filter | Type | Behavior |
|--------|------|----------|
| `status` | list (OR) | Concrete: `active`, `on_hold`, `done`, `dropped`. Shorthands: `remaining` (active + on_hold, **the default**), `available` (active only), `all`. |
| `folder` | string | Case-insensitive partial match on folder name |
| `review_due_within` | string | Projects where `nextReviewDate <= now + duration`. Format: `now`, or `<number><unit>` (d/w/m/y). E.g., `1w`, `2m`. Invalid values return a human-readable error with format examples. Month/year arithmetic is naive (~30d, ~365d). Projects with no review schedule are excluded. |
| `flagged` | bool | Flagged projects |

**`list_tags(status?)`** — default: active only. Filter: `status` list with OR logic (`active`, `on_hold`, `dropped`).

**`list_folders(status?)`** — same pattern as tags.

**`list_perspectives()`** — no filters. Returns all perspectives (built-in + custom) with `id` (null for built-ins), `name`, and `builtin` flag.

### Pydantic Model Expansion

**Project**: id, name, note, status (lifecycle: `active`/`on_hold`/`done`/`dropped` — translated to snake_case), type (derived: `parallel`/`sequential`/`single_action` from `sequential` + `containsSingletonActions`), flagged, effective_flagged, due/defer/completion/drop dates with effective variants, estimated_minutes, has_children, next_review_date, last_review_date, review_interval ({steps, unit}), next_task_id, folder_id, tags, repetition_rule.

**Tag**: id, name, added, modified, status, active, effective_active, allows_next_action, parent_id.

**Folder**: id, name, added, modified, status, active, effective_active, parent_id.

**Perspective**: id, name, builtin.

All hierarchy is flat with ID references (parent_id, folder_id, project_id). No nested JSON.

### Single-Item Lookups

**`get_task(id)`**, **`get_project(id)`**, **`get_tag(id)`** — look up one item by primary key from the snapshot. Returns the full object (same shape as `list_*` results, including computed fields). If not found: clear error message.

### Count Tools

**`count_tasks(...)`** and **`count_projects(...)`** — same filter parameters as their `list_*` counterparts, return a single integer. Implemented as `len(filtered_results)` — no separate code path, no optimization needed (snapshot is in memory).

## Key Design Decisions

- Status values are translated from OmniFocus enums to snake_case (`Active` → `active`, `OnHold` → `on_hold`).
- Project `type` is a single derived enum: if `containsSingletonActions` is true → `single_action`; else if `sequential` is true → `sequential`; else → `parallel`. The raw fields are not exposed individually.
- Project `taskStatus` is available in the dump but NOT exposed — lifecycle `status` is sufficient for now.
- Counts reuse the same filtering logic as list tools. One code path prevents count/list divergence.

## Key Acceptance Criteria

- Default `list_projects()` returns remaining (active + on_hold), not done/dropped.
- `review_due_within: 'now'` returns projects overdue for review. `review_due_within: '1w'` returns projects due within 7 days. Invalid values return helpful error messages.
- Status shorthands work: `remaining`, `available`, `all`.
- Hierarchy is flat with ID references throughout.
- `get_task` with a known ID returns the full Task object with availability/urgency. Unknown ID returns a clear error.
- `count_tasks()` equals `len(list_tasks())` for the same filters.
- Pydantic models match every field in the bridge dump for each entity type.
- Tool descriptions are detailed enough for an LLM to call correctly.

## Tools After This Milestone

Eleven: `list_all`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `get_task`, `get_project`, `get_tag`, `count_tasks`, `count_projects`.
