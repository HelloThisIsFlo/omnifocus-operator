# Milestone v1.3.1 -- Date Filtering

## Goal

Agents can filter tasks by any date dimension — due, defer, planned, completion, drop, creation, and modification dates. After this milestone, the agent can ask "what's overdue?", "tasks completed last week", "what's due soon?", or "tasks added in the last 3 days" — using shorthand periods, absolute bounds, or semantic shortcuts. Depends on v1.3 query infrastructure (SQL WHERE clause building, filter combination).

## What to Build

### Date Filter Fields on `list_tasks`

Seven new filter parameters on `list_tasks`, each accepts a **string shortcut** or **object** (`string | DateFilter`):

| Field | Filters on | String shortcuts |
|-------|-----------|-----------------|
| `due` | effective due date (inherited) | `"today"`, `"overdue"`, `"soon"`, `"none"` |
| `defer` | effective defer date (inherited) | `"today"`, `"none"` |
| `planned` | effective planned date (inherited if applicable) | `"today"`, `"none"` |
| `completed` | effective completion date | `"today"`, `"any"` |
| `dropped` | effective drop date | `"today"`, `"any"` |
| `added` | creation date | `"today"` |
| `modified` | last modified date | `"today"` |

**Effective dates rule:** Wherever OmniFocus computes an effective (inherited) date, the filter uses it. The agent-facing field names omit "effective" — the system always does the right thing.

Using `completed` or `dropped` as a filter automatically includes those tasks in results (excluded by default).

**Null date rule:** Tasks without a value for the filtered date field are excluded from that filter's results. A task with no due date is not "overdue" — it has no deadline to miss. A task with no defer date is not "becoming available" — it was never deferred. This is SQL-natural (`NULL < x` → NULL/false) and semantically correct across all seven fields. Exception: `added` and `modified` always have values in OmniFocus — the null case doesn't arise for those two.

### Object Form — Shorthand Group

Pick exactly one of `this`, `last`, `next`:

| Key | Value format | Meaning | Examples |
|-----|-------------|---------|---------|
| `this` | `unit` | Current calendar period | `"d"` (today), `"w"` (this week), `"m"`, `"y"` |
| `last` | `[N]unit` | N full past days + partial today | `"3d"`, `"w"` (= past 7 days + today), `"2m"` |
| `next` | `[N]unit` | Rest of today + N full future days | `"3d"`, `"w"` (= today + next 7 days), `"1m"` |

Units: `d` (day), `w` (week), `m` (month), `y` (year). Count defaults to 1 when omitted (`"w"` = `"1w"`). Zero or negative count → error with guidance ("use `last` instead of `next` with negative value").

**Month/year arithmetic:** Naive approximation — 1 month ≈ 30 days, 1 year ≈ 365 days. Same convention as `review_due_within` in v1.3. Calendar-aware arithmetic (handling Feb 28/29, variable month lengths) is a future improvement (see FUTURE-IDEAS.md).

**Period resolution:**

- **`this`** is **calendar-aligned**. It answers "which period am I in?" — `{this: "w"}` on a Wednesday means Monday 00:00 through Sunday 23:59 (the current calendar week). `{this: "m"}` in March means March 1 through March 31.
- **`last`/`next`** are **day-snapped rolling from now**. They answer "how far back/forward?" — `{last: "3d"}` means 3 days ago at midnight through now. `{next: "3d"}` means now through 3 days from now at midnight.
  - **N counts full days beyond today.** Today is always included as a partial bonus day. `{last: "3d"}` = 3 full past days + the partial current day. `{next: "3d"}` = the rest of today + 3 full future days. This means the window touches N+1 calendar days, but the bias is intentional: in a task manager, showing slightly too much is a minor annoyance — missing a task you needed to see is painful.
  - **Lower/upper bounds snap to midnight; the "now" side stays at now.** `{last: "3d"}` starts at midnight 3 days ago (clean boundary) but ends at now (not tomorrow midnight — "last 3 days" shouldn't include tasks completed tonight). `{next: "3d"}` starts at now (not today midnight — you don't want past tasks) but ends at midnight 4 days from now (clean boundary).
  - `{last: "w"}` and `{next: "w"}` use the same logic with N=7 days (not calendar-week aligned — that's what `{this: "w"}` is for).

**Why the asymmetry with `this`:** "What did I complete this week?" naturally means the current Mon–Sun. But "what did I complete in the last 3 days?" almost always means "from 3 days ago until now", not "the 3 calendar days before today." `this` and `last`/`next` answer fundamentally different questions, so different resolution semantics are more intuitive than forced consistency.

**Week start:** ISO 8601 — weeks start on Monday (default). Configurable via `OPERATOR_WEEK_START` environment variable (`monday` or `sunday`). Affects `{this: "w"}` calendar alignment only.

**Timezone:** All date computations use naive local time (system timezone). OmniFocus supports per-event timezone annotations, but the filter system ignores them — all comparisons use local time. Non-local timezone support is a future improvement; if detected, log a warning.

**`"now"` snapshot:** `"now"` is evaluated once at query start. All date filters in the same query see the same timestamp. This prevents subtle inconsistencies when a query spans multiple date fields (e.g., `due: {before: "now"}` and `defer: {after: "now"}` use the same instant). This is a domain/service layer concern — the snapshot is created before filter resolution begins.

**Concrete examples** (assume it's Wednesday 2026-03-25 at 14:00):

| Expression | Resolves to | Days touched | Why |
|-----------|-------------|--------------|-----|
| `{this: "d"}` | `>= Wed 00:00, < Thu 00:00` | 1 (Wed) | Calendar-aligned today |
| `{this: "w"}` | `>= Mon 00:00, < next Mon 00:00` | 7 (Mon–Sun) | Calendar-aligned week |
| `{last: "1d"}` | `>= Tue 00:00, < now` | 2 (Tue + partial Wed) | "Last day" = yesterday + today. Not just today — that's `"today"`. |
| `{last: "3d"}` | `>= Sun 00:00, < now` | 4 (Sun, Mon, Tue + partial Wed) | 3 full past days + partial today |
| `{last: "1w"}` | `>= Tue (last wk) 00:00, < now` | 8 (7 full + partial today) | Rolling 7 days, not calendar week — that's `{this: "w"}` |
| `{next: "1d"}` | `>= now, < Fri 00:00` | 2 (partial Wed + Thu) | "Next day" = rest of today + tomorrow |
| `{next: "3d"}` | `>= now, < Sun 00:00` | 4 (partial Wed + Thu, Fri, Sat) | 3 full future days + rest of today |

### Object Form — Absolute Group

One or both of `before`, `after`:

| Key | Accepts | Boundary |
|-----|---------|----------|
| `before` | ISO8601 datetime, date-only, or `"now"` | Inclusive (<=) |
| `after` | ISO8601 datetime, date-only, or `"now"` | Inclusive (>=) |

**Accepted date formats:** Full datetime (`"2026-03-01T14:00:00"`), date-only (`"2026-03-01"`), or `"now"`. Timezone offsets in input are converted to local time. Parsing should be lenient — use a standard date parsing library.

**Date-only resolution:**
- `after` with date-only: resolves to `00:00:00` of that date (start of day)
- `before` with date-only: resolves to `00:00:00` of the **next** date (end of day) — so `before: "2026-03-31"` includes all of March 31 internally, even though the agent-facing contract just says "inclusive"
- This is an **implementation detail** — the agent sees both boundaries as inclusive and doesn't need to think about time-of-day. The implementation ensures "before March 31" means "through the end of March 31."

**Why both inclusive:** Agents naturally echo the user's dates. "Tasks due April 1 through April 14" → `{after: "2026-04-01", before: "2026-04-14"}` — just works, no off-by-one. Stress-tested with 300 agent-generated scenarios: exclusive upper bounds caused the most common error class (agents consistently forgot to add +1 day). Inclusive eliminates this entirely. Consistent with the project's "show a little too much rather than miss a task" philosophy.

Shorthand and absolute groups are mutually exclusive per field. If both `before` and `after` are specified, `after` must be strictly earlier than `before` — equal values match a single day (e.g., `{after: "2026-03-15", before: "2026-03-15"}` = just March 15). Errors are educational.

### String Shortcuts

| Shortcut | On field | Equivalent to | Notes |
|----------|----------|---------------|-------|
| `"today"` | all fields | `{this: "d"}` | Universal. Very natural — agents instinctively reach for this. |
| `"overdue"` | `due` | `{before: "now"}` | Sugar, but very intention-revealing |
| `"soon"` | `due` | `{before: "now + threshold"}` | Includes overdue — anything past its due date is by definition past "due soon." See rationale below. |
| `"any"` | `completed` | no date restriction, include all completed | Replaces old `completed: true` boolean |
| `"any"` | `dropped` | no date restriction, include all dropped | Symmetric with completed |
| `"none"` | `due`, `defer`, `planned` | tasks with no value for this field | Absence filtering — "show tasks with no due date." Only valid on fields where null is possible. `added`/`modified` always have values; `completed`/`dropped` absence = default behavior (excluded). |

### Due-Soon Threshold Configuration

Configurable threshold for what counts as "due soon." Options: `today`, `24h`, `2d`, `3d`, `4d`, `5d`, `1w`. Should match the user's OmniFocus "Due Soon" preference. On mismatch, log a warning.

**Configuration mechanism:** TBD (env var vs server config flag vs MCP resource). Decide during planning.

**`"soon"` includes overdue:** `"soon"` is defined as `{before: "now + threshold"}` — a single upper bound, not a window. Since overdue tasks have due dates before now, and now is before (now + threshold), overdue tasks are naturally included. This is intentional:
- When someone asks "what's due soon?", they implicitly mean "what needs attention deadline-wise?" — and overdue tasks need even MORE attention.
- The math is elegant: `"overdue"` = `due < now`, `"soon"` = `due < now + threshold`. "Overdue" is a strict subset of "soon." No special-casing, it falls out of the definition.
- An agent that wants ONLY the approaching-but-not-yet-overdue tasks can use `due: {after: "now", before: "<computed threshold timestamp>"}` — the agent must compute the absolute ISO8601 timestamp since `"now + threshold"` is not valid input syntax.
- In practice, overdue tasks shouldn't clutter results — if a user has 100 overdue tasks, they have a bigger problem than filter semantics.
- **This does NOT extend to `{next: ...}`.** `due: {next: "1w"}` is a time window (`>= now, < now + 7d`) — overdue tasks are excluded. `{next: ...}` must stay consistent across all 7 date fields, and "include overdue" is meaningless on `completed`, `added`, etc. `"soon"` is the exception because it's a threshold concept that only exists on `due`.

### Validation Rules

1. Per date field: **shorthand OR absolute**, not both — mixing returns an educational error
2. Shorthand: exactly one of `this`/`last`/`next`
3. Absolute: if both `before` and `after`, then `after` must be earlier than `before`
4. Zero or negative count → error with guidance
5. String shortcuts are field-specific — `"today"` is universal; `"overdue"` and `"soon"` only on `due`; `"any"` only on `completed`/`dropped`; `"none"` only on `due`/`defer`/`planned`
6. `"none"` on `added`/`modified` → educational error (always have values)
7. `"none"` on `completed`/`dropped` → educational error: "To get non-completed tasks, omit the `completed` filter — they're excluded by default. Use `completed: 'any'` to include all completed tasks."

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

- `urgency` filter parameter removed — absorbed into `due: "overdue"` and `due: "soon"`. The `urgency` field on the Task model is unchanged (still returned in responses as informational).
- `completed` boolean removed — replaced by `completed` date filter
- `availability` trimmed to `available`/`blocked` only — `completed`/`dropped` states now expressed via date filters

### Availability vs Defer — Critical Distinction

`availability` and `defer` answer fundamentally different questions:

- **`availability: "blocked"`** → "Can I act on this?" — **state** question. Covers ALL four blocking reasons in OmniFocus: future defer date, sequential project position, incomplete parent children, on-hold tag. The SQLite `blocked` column is pre-computed by OmniFocus.
- **`defer: {next: "1w"}`** → "What's becoming available when?" — **timing** question. Only matches tasks with a defer date in the specified window. Defer is just one of four blocking reasons.

**Why this matters:** An agent asked "show me tasks that aren't available yet" should use `availability: "blocked"`, not `defer: {after: "now"}`. The defer filter only catches one of four blocking reasons — it misses tasks blocked by sequential project position, incomplete parent dependencies, or on-hold tags. Getting this wrong silently omits ~75% of blocked tasks (depending on the database).

**When defer filtering IS the right choice:**
- "What's becoming available this week?" → `defer: {this: "w"}` — timing question about deferrals specifically
- "What's deferred to after vacation?" → `defer: {after: "2026-04-07"}` — planning/review question
- "Review my deferrals" → `defer: {after: "now"}` — deferral hygiene, reviewing/rescheduling (niche but valid)

**When availability IS the right choice:**
- "What can I work on right now?" → `availability: "available"`
- "What's blocked?" / "What's unavailable?" → `availability: "blocked"`

The system returns a guidance hint when `defer: {after: "now"}` or `defer: {before: "now"}` is used (see Warnings section below).

### `count_tasks` Extension

`count_tasks` gains the same date filter parameters. One code path shared with `list_tasks` (from v1.3 design).

### Agent Usage Patterns

Realistic scenarios showing how agents compose date filters. These patterns informed the design — each filter earns its place by answering a distinct question.

| Agent hears | Filters used | Why this composition |
|-------------|-------------|---------------------|
| "What's due this week?" | `due: {this: "w"}` | Calendar-aligned deadline check |
| "What's overdue?" | `due: "overdue"` | Semantic shortcut for `{before: "now"}` |
| "What can I work on right now?" | `availability: "available"` | State question — no dates needed |
| "What's blocked?" | `availability: "blocked"` | All 4 blocking reasons, not just defer |
| "How's my week looking?" | `due: {this: "w"}` + `defer: {this: "w"}` + `planned: {this: "w"}` | Deadlines + incoming deferred tasks + planned work = full picture |
| "Is next week going to be busy?" | `due: {next: "1w"}` + `defer: {next: "1w"}` (via `count_tasks`) | Deadline count + incoming load = workload forecast |
| "What did I plan for today?" | `planned: "today"` | Planning review |
| "What's becoming available soon?" | `defer: {next: "3d"}` or `defer: {this: "w"}` | Timing of deferrals — what's landing on my plate |
| "Review my deferrals" | `defer: {after: "now"}` | Deferral hygiene — see future defer dates to reschedule (niche; warning returned) |
| "Tasks I completed last week" | `completed: {last: "1w"}` | Completion review. Auto-includes completed tasks. |
| "What was added recently?" | `added: {last: "3d"}` | New task audit — all tasks have creation dates |
| "What changed today?" | `modified: "today"` | Activity review |
| "Due soon but I can't even start" | `due: "soon"` + `availability: "blocked"` | Proactive warning — deadline approaching on a blocked task. Agent should surface this. |
| "Deferred but never picked up" | `defer: {before: "now"}` + `availability: "available"` | Problem detection — tasks that un-deferred and are gathering dust |
| "Flagged items I've been ignoring" | `flagged: true` + `modified: {before: "<7 days ago ISO>"}` | Wallpaper flag detection — agent computes absolute date (no "older than N" shorthand) |
| "What did I drop this week?" | `dropped: {last: "1w"}` | Decision review — shows dropped with a date range, not just `"any"` |
| "What's due during my vacation?" | `due: {after: "2026-04-01", before: "2026-04-14"}` | Vacation planning (pair with defer query below) |
| "What's deferred into my vacation?" | `defer: {after: "2026-04-01", before: "2026-04-14"}` | Vacation planning — tasks becoming available while you're away |
| "I have 20 minutes free" | `availability: "available"` + `estimated_minutes_max: 20` | Free time triage — not a date query, but the most common composition |
| "Tasks with no due date" | `due: "none"` | Absence filtering — find unscheduled tasks for review |

**Key pattern:** "Can I act on this?" → `availability`. "When does something happen?" → date filter. Agents that conflate the two get wrong results — `defer: {after: "now"}` misses 3 of 4 blocking reasons.

**Composition note:** "How's my week looking?" is the most instructive example. The agent makes 3-4 separate calls to build a complete picture: deadlines (due), incoming work (defer), planned work (planned), and total available count (availability). Each filter contributes information the others can't provide. The defer filter specifically answers "what's landing on my plate?" — something availability alone can't tell you, because availability mixes tasks available since last week with tasks that just un-deferred.

### Warnings & Agent Guidance

The system returns educational hints for patterns that suggest the agent may be using the wrong filter. These are guidance, not errors — the query still executes.

| Pattern detected | Hint returned |
|-----------------|---------------|
| `defer: {after: "now"}` | "Tip: This shows tasks with a future defer date. For all unavailable tasks regardless of reason, use `availability: 'blocked'`. Defer is one of four blocking reasons." |
| `defer: {before: "now"}` | "Tip: This shows tasks whose defer date has passed. For all currently available tasks, use `availability: 'available'`." |

**Additional educational errors:**

| Invalid input | Error returned |
|--------------|---------------|
| `availability: "any"` | "Invalid availability value. Use 'available' or 'blocked'. To include all tasks regardless of availability, omit the availability filter." |
| `due: "none"` on `added` or `modified` | "added/modified dates always have values in OmniFocus — 'none' would always return empty results. Did you mean a different field?" |

**Why only these defer warnings:** Other defer filters (`defer: {this: "w"}`, `defer: {next: "3d"}`) are legitimate timing questions where the agent clearly wants deferral timing, not availability state. The `{after: "now"}` and `{before: "now"}` patterns are the ones most likely to be misused as availability proxies.

### Proposed Tool Descriptions

These are the MCP tool description texts that agents see at call time. They are the primary mechanism for teaching agents how to use date filters correctly.

**Tool-level description for `list_tasks`** (appended to existing description):

> Date filters: `due`, `defer`, `planned`, `completed`, `dropped`, `added`, `modified`. Each accepts a string shortcut or object.
>
> String shortcuts: `"today"` (any field), `due: "overdue"` (before now), `due: "soon"` (due-soon threshold — includes overdue), `completed: "any"` (all completed), `dropped: "any"` (all dropped), `due: "none"` / `defer: "none"` / `planned: "none"` (tasks with no value).
>
> Object — shorthand (pick one key): `{"this": "w"}` (calendar-aligned), `{"last": "3d"}` (N past days + partial today), `{"next": "1m"}` (rest of today + N future days). Units: d, w, m, y. Count defaults to 1.
>
> Object — absolute: `{"after": "2026-03-01", "before": "2026-03-31"}`. Both inclusive. Accepts `"now"`. Shorthand and absolute are mutually exclusive per field.
>
> Tasks with no value for a date field are excluded from that filter. Using `completed` or `dropped` filter auto-includes those tasks.
>
> Important: For "unavailable tasks", use `availability: "blocked"` — it covers all blocking reasons (defer, sequential position, parent dependencies, on-hold). `defer` filters are for timing questions ("what becomes available this week?"), not availability state.

**Per-parameter descriptions:**

| Parameter | Description |
|-----------|-------------|
| `due` | Filter by effective due date (inherited from parent if not set directly). Shortcuts: `"today"`, `"overdue"` (before now), `"soon"` (due within threshold — includes overdue), `"none"` (tasks with no due date). |
| `defer` | Filter by effective defer date (inherited). For timing questions ("what becomes available this week?"), not availability state — use `availability: "blocked"` for unavailable tasks. Shortcuts: `"today"`, `"none"`. |
| `planned` | Filter by effective planned date. Shortcuts: `"today"`, `"none"`. |
| `completed` | Filter by completion date. Automatically includes completed tasks (excluded by default). Shortcuts: `"any"` (all completed, no date restriction). |
| `dropped` | Filter by drop date. Automatically includes dropped tasks (excluded by default). Shortcuts: `"any"` (all dropped, no date restriction). |
| `added` | Filter by creation date. All tasks have a creation date. |
| `modified` | Filter by last modified date. All tasks have a modification date. |

## Key Design Decisions

- **All date filters use effective (inherited) values**, not direct-only. Wherever OmniFocus computes an effective date (due, defer, planned, completed, dropped), the filter checks that effective value. The agent never sees "effective" vs "direct" — they just say `due: "overdue"` and the system uses the right column. Filtering on direct `due_date` alone misses ~45% of overdue tasks.
- `"soon"` depends on configurable due-soon threshold — real functionality, not syntactic sugar.
- `"overdue"` is equivalent to `{"before": "now"}` but more intention-revealing.
- Follows the MoveAction discriminated-key pattern (`this`/`last`/`next` as mutually exclusive keys) and the `review_due_within` `[N]unit` duration format — both already in the codebase.
- `string | object` union per field keeps the common case terse (`due: "overdue"`) while supporting full expressiveness (`due: {"after": "2026-03-01", "before": "2026-03-31"}`).
- **Null dates excluded, not matched** — except via `"none"`. By default, a task with no due date is invisible to `due` filters. The `"none"` shortcut inverts this: `due: "none"` returns tasks with no due date. SQL-natural behavior for comparisons (`NULL < x` → false); `"none"` uses `IS NULL`.
- **`"today"` is universal, not field-specific.** Every date field accepts `"today"` because "tasks completed today", "added today", "modified today" are all natural. Equivalent to `{this: "d"}` but more intention-revealing.
- **Naive local time, not UTC.** All date computations use the system's local timezone. Simpler and matches what users expect. Non-local timezone support is a future improvement.
- **`"soon"` includes overdue.** Defined as `due < now + threshold` — a single upper bound. Overdue tasks are a strict subset of "soon" by the math. When someone asks "what's due soon?", hiding overdue tasks would be hiding the most urgent items. No double-counting concern: `"overdue"` ⊂ `"soon"`, so agents use one or the other depending on intent, not both.
- **`last`/`next` are day-snapped, not hour-rolling.** `{last: "3d"}` starts at midnight 3 days ago, not 72 hours ago — nobody thinks in rolling hours when they say "last 3 days." The distant boundary snaps to midnight (clean, stable); the near boundary is `now` (because "last 3 days" shouldn't include tonight, and "next 3 days" shouldn't include this morning). N counts full days beyond today — today is always an extra partial day. This means `{last: "7d"}` touches 8 calendar days, but the bias is deliberate: in a task manager, a missing task is painful, an extra task is a minor annoyance. `before`/`after` exists for when you need exact timestamp precision.
- **`defer` is for timing, `availability` is for state.** This is the most likely source of agent confusion. `availability: "blocked"` covers 4 blocking reasons (defer, sequential position, parent deps, on-hold tag). `defer` filtering only covers one. The tool descriptions and runtime warnings reinforce this distinction. Validated by multi-model testing: Sonnet correctly used `availability: "blocked"` for "not available" queries while Opus reached for `defer: {after: "now"}` — the spec now makes the correct choice obvious.

## Key Acceptance Criteria

- All date filters use effective (inherited) values where OmniFocus computes them (verified with tasks that inherit due/defer dates from parent projects).
- Completed/dropped excluded by default; using `completed`/`dropped` date filter includes them automatically.
- `completed: "any"` includes all completed tasks regardless of completion date.
- `due: "soon"` respects the configured due-soon threshold.
- `due: "overdue"` returns tasks with effective due date before now.
- Date filter shorthand: `{"this": "w"}` (calendar-aligned), `{"last": "3d"}` (day-snapped rolling), `{"next": "1m"}` (day-snapped rolling) all resolve correctly.
- `{this: "w"}` returns a different range than `{last: "1w"}` — calendar week vs rolling 7 days + partial today.
- `{last: "3d"}` starts at midnight 3 days ago and ends at now — N full past days + partial today. `{next: "3d"}` starts at now and ends at midnight 4 days from now — rest of today + N full future days.
- Date filter absolute: `{"before": "2026-03-31"}` and `{"after": "2026-03-01"}` are both inclusive. `{after: "2026-04-01", before: "2026-04-14"}` includes April 14.
- Date-only `before` values resolve to end-of-day internally (agent doesn't see this — just "inclusive").
- Zero or negative count in shorthand (e.g., `{"next": "0d"}`) returns an educational error.
- Shorthand and absolute groups are mutually exclusive per field — mixing returns an error.
- Invalid string shortcuts on wrong fields (e.g., `defer: "soon"`) return educational error.
- Date filters combine with AND with each other and with v1.3 base filters.
- `count_tasks` with date filters returns correct count.
- Bridge fallback produces identical results to SQL path for date filters.
- Tasks with no due date are excluded from `due` filters (not treated as overdue or due soon).
- Tasks with no defer date are excluded from `defer` filters.
- `defer: {after: "now"}` returns a guidance hint suggesting `availability: "blocked"` for availability questions.
- `due: "today"` is equivalent to `due: {this: "d"}` — works on all seven date fields.
- `due: "none"` returns tasks with no due date. `defer: "none"` returns tasks with no defer date.
- `"none"` on `added`/`modified` returns educational error (always have values).
- `"soon"` includes overdue tasks — `"overdue"` is a strict subset of `"soon"`.
- `availability: "any"` returns educational error suggesting to omit the filter.
- `"now"` is evaluated once per query — consistent timestamp across all date filters in the same call.
- Tool descriptions document date filter syntax clearly enough for an LLM to call correctly, including the availability vs defer distinction.

## Tools After This Milestone

Thirteen (unchanged from v1.3): `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`, `list_tasks`, `list_projects`, `list_tags`, `list_folders`, `list_perspectives`, `count_tasks`, `count_projects`.
