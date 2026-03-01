# Milestone 2 — Filtering & Search

## Goal

The service layer stops being a passthrough. `list_tasks` gains field-level filters, semantic status decomposition, and fuzzy text search. After this milestone, an agent can ask "show me flagged inbox tasks that are overdue" or "find that task about basketball" — and get useful answers.

## What to Build

### New Tool: `list_tasks`

One new MCP tool with optional filter parameters. All filtering runs in-memory against the snapshot. Filters combine with AND logic. Completed/dropped tasks are excluded by default.

### Basic Field Filters

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
| `estimated_minutes_max` | int | Tasks with estimated duration ≤ this value (minutes) |

`project_name` is a derived field — resolved by the service layer from the snapshot's project collection using the raw project ID from the bridge. Not a direct bridge field.

Date filters use `effective_due_date` (inherited values), not `due_date` (direct-only).

### Semantic Status Decomposition

OmniFocus's raw `taskStatus` conflates "can I work on this?" with "how urgent is it?" The service layer decomposes it into two axes.

**`availability`** — Can this task be acted on?

- **available** — workable right now. Raw `Available`, `Next`, `DueSoon`, or `Overdue` when no blocking condition exists.
- **next** — first available task in a project. Subset of available.
- **blocked** — not workable. Raw `Blocked`, or raw `Overdue` with a blocking condition.
- **completed** / **dropped** — terminal states.

**`urgency`** — How close is the deadline?

- **overdue** — effective due date is in the past.
- **due_soon** — effective due date is within the DueSoon threshold.
- **none** — no deadline pressure.

**Blocking conditions.** For tasks with raw `Overdue` status, the service layer checks whether the task is actually blocked. A task is blocked if any of these apply:
- Future defer date (`deferDate > now`)
- Preceding incomplete task in a sequential project
- Incomplete children (parent task with unfinished child tasks)

**Urgency recovery.** For tasks with raw `Available`, `Next`, or `Blocked` status, the service layer checks `effectiveDueDate` to compute urgency — because OmniFocus doesn't report urgency for these statuses. For `DueSoon` and `Overdue`, the urgency is already known from the raw value.

**The critical recovery logic.** OmniFocus's raw `taskStatus` follows a strict priority hierarchy (Overdue > Blocked > DueSoon > Next > Available), and it hides information in two cases:
- **Overdue masks Blocked**: A task can show `Overdue` while being genuinely unworkable. The service layer uses the blocking conditions above to recover true availability.
- **Blocked masks DueSoon**: A blocked task approaching its deadline shows `Blocked`. The service layer checks `effectiveDueDate` to recover urgency.

**Mapping from raw `taskStatus`:**

| Raw `taskStatus` | `availability` | `urgency` | Notes |
|---|---|---|---|
| Available | available | check `effectiveDueDate` | Could be due_soon if threshold differs from OmniFocus setting |
| Next | next | check `effectiveDueDate` | Same as Available |
| DueSoon | available | due_soon | |
| Overdue | check blocking conditions | overdue | May actually be blocked — recover via blocking condition checks |
| Blocked | blocked | check `effectiveDueDate` | DueSoon hidden — recover urgency from dates |
| Completed | completed | none | |
| Dropped | dropped | none | |

The `taskStatus` behavior was empirically tested against real OmniFocus data — these findings are well-established.

**Tag-based blocking is deferred.** OmniFocus also blocks tasks with on-hold tags, but this requires cross-entity lookup. Acceptable trade-off for now — on-hold tags are rarely used.

**DueSoon threshold** is a server configuration value (`--due-soon-threshold`), defaulting to `today` (midnight tonight). Options: `today`, `24h`, `2d`, `3d`, `4d`, `5d`, `1w`. On mismatch with OmniFocus's setting, log a warning pointing to the server config flag.

**Filter parameters:**

- `availability` — single value: `available` (includes next), `next`, `blocked`, `completed`, `dropped`
- `urgency` — single value: `due_soon` (includes overdue), `overdue`, `none`

Note the inclusive semantics: `available` includes `next`, `due_soon` includes `overdue`.

The raw `taskStatus` is stored internally but not exposed in the Task model's serialized output.

### Search

The `search` parameter (string) searches task name and notes with two tiers:

1. **Exact substring** (case-insensitive) — fast and predictable.
2. **Fuzzy match** — catches typos and partial recall. Use a proven approach (token-based scoring, edit distance). Exact matches rank higher than fuzzy.

Edge cases to handle: emoji in task names (searchable by text, ignorable during matching), unicode normalization (accented characters match base form), case folding on fuzzy matches.

This is not full-text search. No indexing, no stemming, no relevance scoring. Just substring + fuzzy, in-memory.

### Pydantic Model Updates

Expand the Task model with:
- `availability` (enum), `urgency` (enum) — computed by the service layer
- `project_name` — derived from snapshot
- All effective_* date fields, completion_date, estimated_minutes, in_inbox, sequential, has_children, repetition_rule (already in the dump, just ensure the model includes them)

## Key Acceptance Criteria

- Each filter works individually against the sample database.
- Filters combine with AND: flagged + due_before returns only tasks matching both.
- `effective_due_date` used for date filters (verified with tasks that have inherited due dates).
- Completed/dropped excluded by default, included with `completed: true`.
- Availability correctly handles the Overdue+blocked recovery: a task with raw `Overdue` and a future defer date gets `availability: blocked, urgency: overdue`.
- Blocked+DueSoon recovery: a task with raw `Blocked` and effective due date within threshold gets `urgency: due_soon`.
- `availability: 'available'` returns tasks with raw `Available`, `Next`, `DueSoon`, and `Overdue` (when not blocked) — intuitive, not literal.
- `urgency: 'due_soon'` includes overdue tasks.
- DueSoon threshold mismatch logged as a warning (not an error).
- Substring search finds exact matches; fuzzy search catches typos.
- Emoji and unicode handled gracefully.
- Search combines with other filters.
- Tool description is detailed enough for an LLM to call correctly based solely on the description.

## Tools After This Milestone

Two: `list_all`, `list_tasks`.
