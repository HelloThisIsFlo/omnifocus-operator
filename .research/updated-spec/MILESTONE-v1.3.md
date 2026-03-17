# Milestone v1.3 -- Read Tools

## Goal

The agent can query tasks with filters, browse the full organizational structure (projects, tags, folders, perspectives), and get quick counts. After this milestone, the agent can ask "show me flagged inbox tasks that are overdue", "which projects are due for review?", or "how many tasks are in this project?" -- and get fast, precise answers via SQL queries.

This combines the original Milestone 2 (Filtering & Search) and Milestone 3 (Entity Browsing). The two-axis status model (the hardest part of M2) was already shipped in v1.1, making the combined scope achievable.

## What to Build

### `list_tasks(...)` with SQL Filters

One new MCP tool with optional filter parameters. Primary path uses SQL WHERE clauses against the SQLite cache. Bridge fallback uses in-memory filtering against the snapshot. Filters combine with AND logic. Completed/dropped tasks are excluded by default.

**Filters:**

| Filter | Type | Behavior |
|--------|------|----------|
| `inbox` | bool | Tasks with no project assignment |
| `flagged` | bool | Flagged tasks |
| `project` | string | Case-insensitive partial match on project name |
| `tags` | list (OR) | Tasks with at least one of the specified tags |
| `due_before` | ISO8601 | Effective due date before this timestamp |
| `due_after` | ISO8601 | Effective due date after this timestamp |
| `completed` | bool | Include completed/dropped (default: false) |
| `has_children` | bool | Parent tasks vs leaf tasks |
| `estimated_minutes_max` | int | Tasks with estimated duration <= this value |
| `availability` | enum | `available` (includes blocked? TBD), `blocked`, `completed`, `dropped` |
| `urgency` | enum | `due_soon` (includes overdue), `overdue`, `none` |
| `search` | string | Case-insensitive substring match on name and notes (SQL LIKE) |
| `limit` | int | Maximum number of results to return (default: no limit) |
| `offset` | int | Skip this many results before returning (default: 0). Requires `limit`. |

**Key design decisions:**
- Date filters use `effective_due_date` (inherited values), not `due_date` (direct-only). Filtering on `due_date` alone misses ~45% of overdue tasks.
- `availability: 'available'` semantic: should it include or exclude blocked? The original spec included blocked tasks under "available" for the filter, but this may be revisited. The two-axis model makes these orthogonal.
- `urgency: 'due_soon'` includes overdue tasks (inclusive semantics).
- Substring search only -- no fuzzy matching. Fuzzy deferred to v1.5+.

**SQL implementation (HybridRepository):**
- Build WHERE clauses dynamically from filter parameters
- Use parameterized queries (no SQL injection)
- Leverage SQLite indexes for common filter combinations
- Target: <6ms for filtered queries vs 46ms full snapshot

**Bridge fallback (BridgeRepository):**
- Load full snapshot, apply filters in-memory (Python)
- Same filter semantics, different execution path

### `list_projects(...)` with Filters

| Filter | Type | Behavior |
|--------|------|----------|
| `status` | list (OR) | Concrete: `active`, `on_hold`, `done`, `dropped`. Shorthands: `remaining` (active + on_hold, **the default**), `available` (active only), `all`. |
| `folder` | string | Case-insensitive partial match on folder name |
| `review_due_within` | string | Projects where `nextReviewDate <= now + duration`. Format: `now`, `<number><unit>` (d/w/m/y). E.g., `1w`, `2m`. Invalid values return a human-readable error. Month/year arithmetic is naive (~30d, ~365d). Projects with no review schedule are excluded. |
| `flagged` | bool | Flagged projects |
| `limit` | int | Maximum number of results to return (default: no limit) |
| `offset` | int | Skip this many results before returning (default: 0). Requires `limit`. |

### `list_tags(status?)`

Default: active only. Filter: `status` list with OR logic (`active`, `on_hold`, `dropped`).

### `list_folders(status?)`

Same pattern as tags.

### `list_perspectives()`

No filters. Returns all perspectives (built-in + custom) with `id` (null for built-ins), `name`, and `builtin` flag.

### Count Tools

**`count_tasks(...)`** and **`count_projects(...)`** -- same filter parameters as their `list_*` counterparts, return a single integer. Implemented as `len(filtered_results)` or `SELECT COUNT(*)` -- one code path to prevent count/list divergence.

### Due-Soon Threshold Configuration

Configurable threshold for what counts as "due soon." Options: `today`, `24h`, `2d`, `3d`, `4d`, `5d`, `1w`. Should match the user's OmniFocus "Due Soon" preference. On mismatch, log a warning.

**Configuration mechanism:** TBD (env var vs server config flag vs MCP resource). Decide during planning.

### Pydantic Model Considerations

All models are already defined from v1.0/v1.1. This milestone adds:
- `project_name` as a derived field on Task (resolved from snapshot/join)
- Ensure all entity models cover every field needed by the filters

### Hierarchy

All hierarchy is flat with ID references (parent_id, folder_id, project_id). No nested JSON.

## Key Design Decisions

- Status values are already translated to snake_case from v1.1.
- Project `type` is a derived enum: `sequential`, `parallel`, or `single_action`.
- Counts reuse the same filtering logic as list tools. One code path prevents count/list divergence.
- SQL-level filtering is the primary path. In-memory filtering exists only for bridge fallback.
- No fuzzy search. Substring matching via SQL LIKE is sufficient for now. Fuzzy deferred to v1.5+.
- Pagination via `limit`/`offset` on `list_tasks` and `list_projects`. SQL uses `LIMIT ? OFFSET ?`. Bridge fallback slices in-memory. `offset` without `limit` is an error. `count_*` tools are unaffected (always return total count for the filters).

## Key Acceptance Criteria

- Each filter works individually against real OmniFocus data.
- Filters combine with AND: flagged + due_before returns only tasks matching both.
- `effective_due_date` used for date filters (verified with tasks that have inherited due dates).
- Completed/dropped excluded by default, included with `completed: true`.
- SQL queries use parameterized values (no injection).
- Filtered SQL queries are measurably faster than full snapshot (~6ms vs ~46ms).
- Default `list_projects()` returns remaining (active + on_hold), not done/dropped.
- `review_due_within: 'now'` returns projects overdue for review. Invalid values return helpful error messages.
- Status shorthands work: `remaining`, `available`, `all`.
- `get_task` with a known ID returns the full Task object (from v1.2 -- no regression).
- `count_tasks()` equals `len(list_tasks())` for the same filters.
- Substring search finds case-insensitive matches in name and notes.
- Tool descriptions are detailed enough for an LLM to call correctly.
- Bridge fallback produces identical results to SQL path for the same filters.
- `list_tasks(limit: 5)` returns at most 5 results. `list_tasks(limit: 5, offset: 5)` returns the next page.
- `count_tasks()` returns total count regardless of `limit`/`offset` — agents can compute total pages.

## Tools After This Milestone

Thirteen: `list_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `count_tasks`, `count_projects`.
