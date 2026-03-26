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
| `has_children` | bool | Parent tasks vs leaf tasks |
| `estimated_minutes_max` | int | Tasks with estimated duration <= this value |
| `availability` | enum | `available`, `blocked` |
| `search` | string | Case-insensitive substring match on name and notes (SQL LIKE) |
| `limit` | int | Maximum number of results to return (default: no limit) |
| `offset` | int | Skip this many results before returning (default: 0). Requires `limit`. |

**Date filters:**

Seven date filter fields, each accepts a **string shortcut** or **object** (`string | DateFilter`):

| Field | Filters on | String shortcuts |
|-------|-----------|-----------------|
| `due` | effective due date | `"overdue"` (before now), `"soon"` (configurable threshold) |
| `defer` | effective defer date | -- |
| `planned` | planned date | -- |
| `completed` | completion date | `"any"` / `"true"` (all completed, no date restriction) |
| `dropped` | drop date | `"any"` / `"true"` (all dropped, no date restriction) |
| `added` | creation date | -- |
| `modified` | last modified date | -- |

Using `completed` or `dropped` as a filter automatically includes those tasks in results (excluded by default). `"any"` and `"true"` are interchangeable.

**Object form — shorthand group** (pick exactly one of `this`, `last`, `next`):

| Key | Value format | Meaning | Examples |
|-----|-------------|---------|---------|
| `this` | `unit` | Current calendar period | `"d"` (today), `"w"` (this week), `"m"`, `"y"` |
| `last` | `[N]unit` | Past N periods | `"3d"`, `"w"` (= last week), `"2m"` |
| `next` | `[N]unit` | Future N periods | `"3d"`, `"w"`, `"1m"` |

Units: `d` (day), `w` (week), `m` (month), `y` (year). Count defaults to 1 when omitted (`"w"` = `"1w"`). Zero or negative count → error with guidance ("use `last` instead of `next` with negative value").

**Object form — absolute group** (one or both of `before`, `after`):

| Key | Accepts |
|-----|---------|
| `before` | ISO8601 datetime or `"now"` |
| `after` | ISO8601 datetime or `"now"` |

Shorthand and absolute groups are mutually exclusive per field. If both `before` and `after` are specified, `after` must be earlier than `before`. Errors are educational.

**Date filter design decisions:**
- Date filters on `due` and `defer` use effective (inherited) values, not direct-only. Filtering on direct `due_date` alone misses ~45% of overdue tasks.
- `"soon"` depends on configurable due-soon threshold — real functionality, not syntactic sugar.
- `"overdue"` is equivalent to `{"before": "now"}` but more intention-revealing.
- `urgency` filter removed — absorbed into `due: "overdue"` and `due: "soon"`.
- `completed` boolean removed — replaced by `completed` date filter (`"any"`/`"true"` for all, object for date-restricted).
- `availability` trimmed to `available`/`blocked` only — `completed`/`dropped` states expressed via date filters.
- Follows the MoveAction discriminated-key pattern and the `review_due_within` `[N]unit` duration format.
- Substring search only -- no fuzzy matching. Fuzzy deferred to v1.4.1.

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
- Date filters use a `string | object` union. String shortcuts for semantic queries (`"overdue"`, `"soon"`, `"any"`/`"true"`), object form for shorthand periods (`this`/`last`/`next` with `[N]unit`) or absolute bounds (`before`/`after` with ISO8601 or `"now"`). Inspired by the MoveAction discriminated-key pattern and the `review_due_within` duration format.
- `urgency` filter removed — absorbed into `due: "overdue"` and `due: "soon"`. `availability` trimmed to `available`/`blocked` — `completed`/`dropped` expressed via date filters.
- Counts reuse the same filtering logic as list tools. One code path prevents count/list divergence.
- SQL-level filtering is the primary path. In-memory filtering exists only for bridge fallback.
- No fuzzy search. Substring matching via SQL LIKE is sufficient for now. Fuzzy deferred to v1.4.1.
- Pagination via `limit`/`offset` on `list_tasks` and `list_projects`. SQL uses `LIMIT ? OFFSET ?`. Bridge fallback slices in-memory. `offset` without `limit` is an error. `count_*` tools are unaffected (always return total count for the filters).

## Key Acceptance Criteria

- Each filter works individually against real OmniFocus data.
- Filters combine with AND: `flagged` + `due: "overdue"` returns only tasks matching both.
- Date filters on `due` and `defer` use effective (inherited) values (verified with tasks that have inherited dates).
- Completed/dropped excluded by default; using `completed`/`dropped` date filter includes them automatically.
- `completed: "any"` and `completed: "true"` are interchangeable — both include all completed tasks.
- `due: "soon"` respects the configured due-soon threshold.
- `due: "overdue"` returns tasks with effective due date before now.
- Date filter shorthand: `{"this": "w"}`, `{"last": "3d"}`, `{"next": "1m"}` all resolve correctly.
- Date filter absolute: `{"before": "now"}`, `{"after": "2026-03-01"}` work. Both together define a range.
- Zero or negative count in shorthand (e.g., `{"next": "0d"}`) returns an educational error.
- Shorthand and absolute groups are mutually exclusive per field — mixing returns an error.
- SQL queries use parameterized values (no injection).
- Filtered SQL queries are measurably faster than full snapshot (~6ms vs ~46ms).
- Default `list_projects()` returns remaining (active + on_hold), not done/dropped.
- `review_due_within: 'now'` returns projects overdue for review. Invalid values return helpful error messages.
- Status shorthands work: `remaining`, `available`, `all`.
- `get_task` with a known ID returns the full Task object (from v1.2 -- no regression).
- `count_tasks()` equals `len(list_tasks())` for the same filters.
- Substring search finds case-insensitive matches in name and notes.
- Tool descriptions are detailed enough for an LLM to call correctly — especially date filter syntax.
- Bridge fallback produces identical results to SQL path for the same filters.
- `list_tasks(limit: 5)` returns at most 5 results. `list_tasks(limit: 5, offset: 5)` returns the next page.
- `count_tasks()` returns total count regardless of `limit`/`offset` — agents can compute total pages.

## Tools After This Milestone

Thirteen: `list_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `count_tasks`, `count_projects`.
