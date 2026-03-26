# Milestone v1.3.1 -- Date Filtering

## Goal

Agents can filter tasks by any date dimension — due, defer, planned, completion, drop, creation, and modification dates. After this milestone, the agent can ask "what's overdue?", "tasks completed last week", "what's due soon?", or "tasks added in the last 3 days" — using shorthand periods, absolute bounds, or semantic shortcuts. Depends on v1.3 query infrastructure (SQL WHERE clause building, filter combination).

## What to Build

### Date Filter Fields on `list_tasks`

Seven new filter parameters on `list_tasks`, each accepts a **string shortcut** or **object** (`string | DateFilter`):

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

### Object Form — Shorthand Group

Pick exactly one of `this`, `last`, `next`:

| Key | Value format | Meaning | Examples |
|-----|-------------|---------|---------|
| `this` | `unit` | Current calendar period | `"d"` (today), `"w"` (this week), `"m"`, `"y"` |
| `last` | `[N]unit` | Past N periods | `"3d"`, `"w"` (= last week), `"2m"` |
| `next` | `[N]unit` | Future N periods | `"3d"`, `"w"`, `"1m"` |

Units: `d` (day), `w` (week), `m` (month), `y` (year). Count defaults to 1 when omitted (`"w"` = `"1w"`). Zero or negative count → error with guidance ("use `last` instead of `next` with negative value").

### Object Form — Absolute Group

One or both of `before`, `after`:

| Key | Accepts |
|-----|---------|
| `before` | ISO8601 datetime or `"now"` |
| `after` | ISO8601 datetime or `"now"` |

Shorthand and absolute groups are mutually exclusive per field. If both `before` and `after` are specified, `after` must be earlier than `before`. Errors are educational.

### String Shortcuts

| Shortcut | On field | Equivalent to | Notes |
|----------|----------|---------------|-------|
| `"overdue"` | `due` | `{"before": "now"}` | Sugar, but very intention-revealing |
| `"soon"` | `due` | within configured due-soon threshold | Real functionality — agent can't compute this |
| `"any"` / `"true"` | `completed` | no date restriction, include all completed | Replaces old `completed: true` boolean |
| `"any"` / `"true"` | `dropped` | no date restriction, include all dropped | Symmetric with completed |

### Due-Soon Threshold Configuration

Configurable threshold for what counts as "due soon." Options: `today`, `24h`, `2d`, `3d`, `4d`, `5d`, `1w`. Should match the user's OmniFocus "Due Soon" preference. On mismatch, log a warning.

**Configuration mechanism:** TBD (env var vs server config flag vs MCP resource). Decide during planning.

### Validation Rules

1. Per date field: **shorthand OR absolute**, not both — mixing returns an educational error
2. Shorthand: exactly one of `this`/`last`/`next`
3. Absolute: if both `before` and `after`, then `after` must be earlier than `before`
4. Zero or negative count → error with guidance
5. String shortcuts are field-specific — `"soon"` only valid on `due`, `"any"`/`"true"` only on `completed`/`dropped`

### SQL Implementation

- Extend v1.3's WHERE clause builder with date predicates
- Shorthand periods resolved to absolute timestamps server-side before SQL generation
- `"soon"` resolved using configured threshold
- `"now"` resolved to current timestamp at query time
- Parameterized queries (no SQL injection)

### Bridge Fallback

- Same date filter semantics applied in-memory against the snapshot
- Period resolution identical to SQL path — shared utility functions

### Changes to Existing Filters

- `urgency` filter removed — absorbed into `due: "overdue"` and `due: "soon"`
- `completed` boolean removed — replaced by `completed` date filter
- `availability` trimmed to `available`/`blocked` only — `completed`/`dropped` states now expressed via date filters

### `count_tasks` Extension

`count_tasks` gains the same date filter parameters. One code path shared with `list_tasks` (from v1.3 design).

## Key Design Decisions

- Date filters on `due` and `defer` use effective (inherited) values, not direct-only. Filtering on direct `due_date` alone misses ~45% of overdue tasks.
- `"soon"` depends on configurable due-soon threshold — real functionality, not syntactic sugar.
- `"overdue"` is equivalent to `{"before": "now"}` but more intention-revealing.
- Follows the MoveAction discriminated-key pattern (`this`/`last`/`next` as mutually exclusive keys) and the `review_due_within` `[N]unit` duration format — both already in the codebase.
- `string | object` union per field keeps the common case terse (`due: "overdue"`) while supporting full expressiveness (`due: {"after": "2026-03-01", "before": "2026-03-31"}`).

## Key Acceptance Criteria

- Date filters on `due` and `defer` use effective (inherited) values (verified with tasks that have inherited dates).
- Completed/dropped excluded by default; using `completed`/`dropped` date filter includes them automatically.
- `completed: "any"` and `completed: "true"` are interchangeable — both include all completed tasks.
- `due: "soon"` respects the configured due-soon threshold.
- `due: "overdue"` returns tasks with effective due date before now.
- Date filter shorthand: `{"this": "w"}`, `{"last": "3d"}`, `{"next": "1m"}` all resolve correctly.
- Date filter absolute: `{"before": "now"}`, `{"after": "2026-03-01"}` work. Both together define a range.
- Zero or negative count in shorthand (e.g., `{"next": "0d"}`) returns an educational error.
- Shorthand and absolute groups are mutually exclusive per field — mixing returns an error.
- Invalid string shortcuts on wrong fields (e.g., `defer: "soon"`) return educational error.
- Date filters combine with AND with each other and with v1.3 base filters.
- `count_tasks` with date filters returns correct count.
- Bridge fallback produces identical results to SQL path for date filters.
- Tool descriptions document date filter syntax clearly enough for an LLM to call correctly.

## Tools After This Milestone

Thirteen (unchanged from v1.3): `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `count_tasks`, `count_projects`.
