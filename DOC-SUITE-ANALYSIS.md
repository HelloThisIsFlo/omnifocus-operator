# Doc Suite Analysis — v1.3 + v1.3.1 + v1.3.2 "Full Catchup"

## How to Use This File

This file is the output of a research session that analyzed what v1.3 through v1.3.2 changed in tool documentation vs what existing doc-regression scenarios cover. It contains everything a fresh agent needs to co-write new scenarios with the user without re-doing the research.

**Workflow:** Run `/doc-suite-updater` in a new session. The skill auto-detects this file and enters Worker mode — it will find the next unchecked chunk, present trap concepts, co-write scenarios with the user, and mark the chunk done.

**Important:** Worker sessions are collaborative — the agent proposes trap concepts and drafts scenarios, but the user shapes the final content. The seed provides starting points, not prescriptive instructions.

**Scope:** Full catchup covering three milestones:
- **v1.3 Read Tools** (Phases 34-38) — 7 new list/read tools
- **v1.3.1 First-Class References** (Phases 39-44) — $inbox, rich references, name resolution
- **v1.3.2 Date Filtering** (Phases 45-50) — date filter syntax, availability trimming, naive-local datetime, OmniFocus settings API

**Git diff range:** `v1.2.3..HEAD` (no v1.3.2 tag yet)

---

## Progress

- [ ] Chunk 1 — list-tasks: Date filters & shortcuts (NEW SUITE)
- [ ] Chunk 2 — list-tasks: Availability, lifecycle & base filters
- [ ] Chunk 3 — list-projects (NEW SUITE)
- [ ] Chunk 4 — Write tool updates (add-tasks.md + edit-tasks.md)
- [ ] **Delete this file** (all chunks done, everything merged)

---

## Chunks — Task List

### Chunk completion protocol

After co-writing the scenarios for a chunk, the agent does NOT commit. Instead:

1. **Summarize changes** — list every file modified, scenarios added, scenarios updated
2. **Offer validation** — "Want me to run these new scenarios through doc-regression to test if the traps work?"
3. **Wait for sign-off** — user reviews the changes (and validation results if applicable)
4. **On approval**: commit the scenario changes, then update the Progress checklist above (check the box)

---

### Chunk 1: list-tasks — Date filters & shortcuts (NEW SUITE)

**Suites:** `.claude/skills/doc-regression/scenarios/list-tasks.md` (create new)

**Must include:** Suite header matching existing format (`# List Tasks — Doc Regression Scenarios`)

**Trap concepts to explore:**
- SS-03: "overdue tasks" — agent may try removed `urgency` filter instead of `due: "overdue"`
- SS-04: Calendar week vs rolling week — `{this: "w"}` (calendar-aligned) vs `{last: "1w"}` (rolling 7 days)
- SS-05: "any completed tasks" — `completed: "any"` not `completed: true` (boolean errors with migration guidance)
- IR-01: completed/dropped date filter auto-includes lifecycle state in results (no separate availability setting needed)
- IR-02: "soon" includes overdue — `due: "soon"` means `due < now + threshold`, not just the gap between now and threshold
- IR-03: "this month" = calendar month (1st-31st), not "last 30 days" — period vs rolling distinction
- ST-01: Equivalent forms — `due: "overdue"` (string) vs `due: {before: "now"}` (object) — both valid, model should pick the cleaner one
- SS-07: Date-only in absolute range — `{after: "2026-03-01", before: "2026-03-31"}` — both bounds inclusive, date-only resolves to start/end of day

**Est. scope:** ~7-8 new scenarios.

---

### Chunk 2: list-tasks — Availability, lifecycle & base filters

**Suites:** `.claude/skills/doc-regression/scenarios/list-tasks.md` (continue)

**Trap concepts to explore:**
- FC-01: availability "blocked" vs defer filter — "show me unavailable tasks" → `availability: ["blocked"]`, NOT `defer: {after: "now"}`; defer is timing-only (1 of 4 blocking reasons)
- FC-03: "remaining" default — no availability filter means `["remaining"]` = `["available", "blocked"]`; completed/dropped still excluded
- FC-06: inInbox vs project: "$inbox" — functionally equivalent, but contradictory combination errors
- IR-05: Omitting availability filter ≠ "all tasks" — completed/dropped still excluded by default; need `completed: "any"` to include them
- SS-01: "tasks I can work on this week" — `availability: ["available"]` + `due: {this: "w"}`? Or just `due: {this: "w"}`? Agent must decide if availability restriction is wanted
- SS-02: "what's becoming available soon" → `defer: {next: "1w"}` (timing), NOT `availability: ["blocked"]` (state)
- DC-01: Default limit is 50 — request for "all my tasks" needs `limit: null` to remove cap
- DC-02: Tags use OR logic — `tags: ["Work", "Urgent"]` matches tasks with EITHER tag, not both

**Est. scope:** ~6-7 new scenarios.

---

### Chunk 3: list-projects (NEW SUITE)

**Suites:** `.claude/skills/doc-regression/scenarios/list-projects.md` (create new)

**Must include:** Suite header matching existing format (`# List Projects — Doc Regression Scenarios`)

**Trap concepts to explore:**
- FC-07: list_projects availability uses same enum as list_tasks (`available`, `blocked`, `remaining`) — NOT the `active`/`on_hold`/`done`/`dropped` from v1.3 spec (those were removed)
- ST-02: list_projects has `folder` and `reviewDueWithin` which list_tasks doesn't; agent may try `project` filter on list_projects (doesn't exist — projects ARE projects)
- SS-08: "projects due for review" → `reviewDueWithin: "now"` (overdue reviews) or `reviewDueWithin: "1w"` (due within a week); this is review schedule, NOT project due date
- SS-09: Folder name resolution uses case-insensitive substring — `folder: "Work"` matches "Work", "Homework", "Network" etc.
- DC-04: Date filters on projects use effective (inherited) values from parent folders — same behavior as list_tasks

**Est. scope:** ~5-6 new scenarios.

---

### Chunk 4: Write tool updates (add-tasks.md + edit-tasks.md)

**Suites:** `.claude/skills/doc-regression/scenarios/add-tasks.md`, `.claude/skills/doc-regression/scenarios/edit-tasks.md`

**Trap concepts to explore (new scenarios):**
- ST-03: $inbox usage across tools — `add_tasks` parent: omit OR `"$inbox"`; `edit_tasks` move: `ending: "$inbox"` or `beginning: "$inbox"`. Agent may try `parent: null` on add_tasks (warns) or `ending: null` on edit_tasks (errors)
- SS-06: Date-only write input — `dueDate: "2026-03-15"` enriched with user's OmniFocus default due time (not midnight). Agent should know date-only is acceptable
- DC-03: Naive-local datetime — `dueDate: "2026-03-15T17:00:00"` (no Z, no offset) is now the preferred format. Timezone offsets still accepted but not required
- FC-08: `actions.move.after` — sibling positioning exists alongside `before`, `beginning`, `ending`. "After" is for ordering among siblings, not moving into a container

**Stale scenarios to review:**
- add-tasks scenarios 1-7 (date-focused): Expected payloads should use **naive-local datetimes** (no Z, no offset) as the default correct format. If any Expected payloads include timezone offsets, update to naive-local. Grading should MUST naive-local for agent-generated dates, SHOULD accept timezone offsets only when the prompt contains data that already has timezone info (e.g., fetched from a calendar API). Date semantic traps (deferDate vs dueDate vs plannedDate) remain fully valid.
- edit-tasks date scenarios: same naive-local update as add-tasks.
- edit-tasks scenario 20 ($inbox): verify consistency with v1.3.1 `$inbox` behavior. The scenario may already be correct since it tests `ending: "$inbox"`.

**Est. scope:** ~3-4 new scenarios + ~2-3 updates.

---

## Reference Material

Everything below is research output — the chunks above reference it.

---

## What v1.3 + v1.3.1 + v1.3.2 Changed in Tool Documentation

### v1.3 — Read Tools (Phases 34-38)

**New tools added:**
- `list_tasks` — SQL-backed filtered task queries with AND-logic filters, pagination
- `list_projects` — SQL-backed filtered project queries
- `list_tags` — browse tags with availability filter
- `list_folders` — browse folders with availability filter
- `list_perspectives` — browse perspectives (custom only, built-in not yet available)

**New concepts:**
- SQL vs bridge fallback (agent-transparent)
- Availability enum: `available`, `blocked`, `remaining` (shorthand for available+blocked)
- Name-based resolution for entity filters (case-insensitive substring, ID priority)
- AND logic between filters, OR logic for tags
- Pagination with `limit`/`offset` and `total`/`hasMore` response fields

### v1.3.1 — First-Class References (Phases 39-44)

**No new tools.** Major contract renovation:

- **`$inbox` as first-class value:** Reserved `$` prefix for system locations. `$inbox` works in:
  - `add_tasks` parent field (explicit inbox targeting)
  - `edit_tasks` move actions (beginning/ending)
  - `list_tasks` project filter (`project: "$inbox"`)
- **Rich references:** All entity reference outputs changed from bare IDs to `{id, name}` pairs (ProjectRef, TaskRef, FolderRef, TagRef)
- **Task output changes:**
  - New `project` field (containing project at any depth, never null; inbox = `{id: "$inbox", name: "Inbox"}`)
  - `parent` field changed to tagged discriminator: `{project: {...}}` or `{task: {...}}`, never null
  - `inInbox` boolean removed from output (derivable from `project.id == "$inbox"`)
- **Name resolution for writes:** `add_tasks` parent and `edit_tasks` move accept names, case-insensitive substring matching
- **Breaking changes:**
  - `ending: null` / `beginning: null` → error (use `$inbox` explicitly)
  - `parent: null` on add_tasks → works but warns (use `$inbox` or omit)

### v1.3.2 — Date Filtering (Phases 45-50)

**Seven new date filter fields on list_tasks and list_projects:** `due`, `defer`, `planned`, `completed`, `dropped`, `added`, `modified`

Each accepts:
- **String shortcuts:** `"today"` (any field), `"overdue"` (due only), `"soon"` (due only), `"any"` (completed/dropped only)
- **Shorthand objects:** `{this: "d"/"w"/"m"/"y"}` (calendar-aligned), `{last: "3d"/"2w"/"m"/"1y"}` (rolling), `{next: "3d"/"2w"/"m"/"1y"}` (rolling)
- **Absolute range:** `{before: ISO/"now", after: ISO/"now"}` — both inclusive

**Breaking changes:**
- `urgency` filter removed from list_tasks (educational error → `due: "overdue"` / `due: "soon"`)
- `completed: true/false` (boolean) → educational error guiding to date filter form
- `COMPLETED`/`DROPPED` removed from AvailabilityFilter enum
- `availability: "any"` / `availability: "all"` → educational error

**Naive-local datetime (Phase 49):**
- All date inputs now accept naive-local format: `"2026-03-15T17:00:00"` (no Z, no offset)
- Timezone offsets still accepted, silently converted to local
- JSON Schema uses `str` type (no `format: "date-time"`)
- This replaces the earlier "require timezone info" rule from v1.3

**OmniFocus settings API (Phase 50):**
- Date-only write inputs enriched with user's OmniFocus default times (not midnight)
- Due-soon threshold from OmniFocus preferences (no env var)
- Restart required for preference changes

**Availability vs defer guidance:**
- Every defer filter returns a hint about availability equivalents
- Tool descriptions explain the distinction

---

## Tool Documentation Inventory

Current state of every tool's documentation, with scenario coverage status.

### get_all

**Description summary:** Returns full OmniFocus database. Last-resort/debugging tool; prefer list_tasks/list_projects.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| (no input fields) | — | — | No parameters; no meaningful payload trap |

### get_task

**Description summary:** Look up single task by ID. Returns full task object with effective fields, parent/project refs, tags.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| id | string (required) | none | Trivial payload — just an ID string |

### get_project

**Description summary:** Look up single project by ID. $inbox is not a real project and cannot be looked up here.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| id | string (required) | none | Trivial payload; $inbox rejection mentioned in description |

### get_tag

**Description summary:** Look up single tag by ID.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| id | string (required) | none | Trivial payload — just an ID string |

### add_tasks

**Description summary:** Create tasks in OmniFocus. 1 item per call. Tags by name/ID. Naive-local dates. RepetitionRule requires all 3 root fields.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| name | string (req) | 1-7, 14, 16-18, 20-22 | Well covered |
| parent | string | 19, 20 | Missing $inbox explicit usage |
| tags | [string] | 17, 22 | Array syntax covered; no ambiguous name trap |
| dueDate | string | 1, 4, 5, 7, 8, 13 | Well covered for semantics |
| deferDate | string | 1, 2, 5 | Covered — hidden-until semantics |
| plannedDate | string | 1, 3, 6, 12 | Covered — intent semantics |
| flagged | boolean | 15 | Single scenario |
| estimatedMinutes | number | 14, 17 | Prose extraction focus |
| note | string | 16 | Single scenario |
| repetitionRule | object | 8-13 | Well covered — all frequency types, schedule, basedOn, end |

### edit_tasks

**Description summary:** Edit tasks using patch semantics. 1 item per call. Omit=preserve, null=clear, value=update. Tag actions exclusive modes.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| id | string (req) | 1-23 | Required on all |
| name | string | none | Renaming never tested |
| flagged | boolean (no null) | 1, 3 | Covered |
| note | string/null | 1, 2, 23 | Covered — null=clear |
| dueDate | string/null | 1, 2, 4, 23 | Covered — null/omit |
| deferDate | string/null | 1, 2, 5 | Covered |
| plannedDate | string/null | 1, 2, 6 | Covered |
| estimatedMinutes | number/null | 1, 2, 23 | Covered — null=clear |
| repetitionRule | object/null | 8-15, 23 | Extensive coverage |
| actions.tags.replace | [string]/null | 2, 16, 18 | Covered |
| actions.tags.add | [string] | 17, 23 | Covered |
| actions.tags.remove | [string] | 17, 23 | Covered |
| actions.move.beginning | string | 21, 23 | Covered |
| actions.move.ending | string | 20, 23 | Covered — includes $inbox |
| actions.move.before | string | 19 | Covered |
| actions.move.after | string | none | **UNCOVERED** |
| actions.lifecycle | "complete"/"drop" | 22 | Only "drop" tested; "complete" uncovered |

### list_tasks

**Description summary:** List and filter tasks. AND logic. Date filters on 7 fields (shortcuts, shorthand, absolute). Availability vs defer distinction. Pagination.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| inInbox | boolean | none | NEW tool — no scenarios exist |
| flagged | boolean | none | |
| project | string | none | Name resolution + $inbox |
| tags | [string] | none | OR logic |
| estimatedMinutesMax | integer | none | |
| availability | ["available"/"blocked"/"remaining"] | none | "remaining" is default |
| search | string | none | Substring on name + notes |
| due | string/object | none | Shortcuts: "overdue", "soon", "today" |
| defer | string/object | none | Guidance hints on every use |
| planned | string/object | none | |
| completed | string/object | none | Auto-includes lifecycle state |
| dropped | string/object | none | Auto-includes lifecycle state |
| added | string/object | none | |
| modified | string/object | none | |
| limit | integer/null | none | Default 50; null = all |
| offset | integer | none | Requires limit |

### list_projects

**Description summary:** List and filter projects. AND logic. Same date filter syntax as list_tasks. Folder filter. reviewDueWithin for review schedule.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| availability | ["available"/"blocked"/"remaining"] | none | NEW tool — no scenarios exist |
| folder | string | none | Name resolution, substring |
| reviewDueWithin | string | none | Duration format: "now", "3d", "2w", etc. |
| flagged | boolean | none | |
| search | string | none | |
| due | string/object | none | Same syntax as list_tasks |
| defer | string/object | none | |
| planned | string/object | none | |
| completed | string/object | none | Auto-includes |
| dropped | string/object | none | Auto-includes |
| added | string/object | none | |
| modified | string/object | none | |
| limit | integer/null | none | Default 50 |
| offset | integer | none | |

### list_tags

**Description summary:** List and filter tags. Flat list with parent ref for hierarchy.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| availability | ["available"/"blocked"/"dropped"/"ALL"] | none | Different enum from list_tasks! |
| search | string | none | |
| limit | integer/null | none | |
| offset | integer | none | |

### list_folders

**Description summary:** List and filter folders. Flat list with parent ref for hierarchy.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| availability | ["available"/"dropped"/"ALL"] | none | Different enum — no "blocked" |
| search | string | none | |
| limit | integer/null | none | |
| offset | integer | none | |

### list_perspectives

**Description summary:** List perspectives. Custom only, built-in not yet available.

| Field | Type | Covered by Scenario(s) | Notes |
|-------|------|----------------------|-------|
| search | string | none | |
| limit | integer/null | none | |
| offset | integer | none | |

---

## Gap Analysis by Suite

### add-tasks (22 scenarios) — MINOR UPDATES

**Uncovered fields/behaviors:**

| Field/Behavior | Why it needs a scenario | Trap potential |
|---------------|----------------------|----------------|
| parent: "$inbox" | v1.3.1 added $inbox as explicit value; omit vs "$inbox" vs null all route to inbox differently | medium — three ways to say inbox, two correct, one warns |
| Date-only input | v1.3.2 Phase 50: date-only strings get OmniFocus default time, not midnight | medium — agents may assume midnight |
| Naive-local datetime | v1.3.2 Phase 49: timezone no longer required; naive format preferred | low — not a trap per se, but affects grading of existing scenarios |

**Stale scenarios:**
- Scenarios 1-7 (date-focused): Expected payloads should show naive-local datetimes (no Z, no offset) as the default correct format. Grading should MUST naive-local for agent-generated dates; SHOULD accept timezone offsets only when the prompt contains data that already has timezone info. Date semantic traps remain fully valid.

### edit-tasks (23 scenarios) — MINOR UPDATES

**Uncovered fields/behaviors:**

| Field/Behavior | Why it needs a scenario | Trap potential |
|---------------|----------------------|----------------|
| actions.move.after | Sibling positioning — exists in schema, never tested | medium — agents may confuse with "ending" |
| lifecycle: "complete" | Common operation, only "drop" tested | low — straightforward from docs |
| name (rename) | Simple field but untested | low — straightforward |
| $inbox in move with null | v1.3.1: `ending: null` now errors; `ending: "$inbox"` is correct | medium — null vs "$inbox" confusion |

**Stale scenarios:**
- Scenario 20 ($inbox): Verify alignment with v1.3.1 `$inbox` semantics. Likely already correct since it uses `ending: "$inbox"`.
- Date format staleness: same as add-tasks — Expected payloads should default to naive-local datetimes.

### list-tasks — **NEW SUITE NEEDED**

This is the biggest gap. list_tasks is the most complex tool with the most trap potential.

**Uncovered fields/behaviors:**

| Field/Behavior | Why it needs a scenario | Trap potential |
|---------------|----------------------|----------------|
| due: "overdue" | Replaced urgency filter; agents may try old syntax | high — breaking change with educational error |
| due: "soon" | Includes overdue (not just the gap); uses OmniFocus threshold | high — semantic subtlety |
| completed: "any" | Auto-includes lifecycle state; replaces boolean completed | high — breaking change |
| {this: "w"} vs {last: "1w"} | Calendar week vs rolling 7 days — different results | high — subtle distinction |
| {last: "3d"} | 3 full past days + partial today | medium — boundary semantics |
| {after: date, before: date} | Both inclusive; date-only resolves to full day | medium — inclusivity |
| availability: default | "remaining" = available+blocked; completed/dropped excluded | high — implicit exclusion |
| availability vs defer | Different questions (state vs timing); agents conflate | high — key educational point |
| project: "$inbox" | System location filter; equivalent to inInbox: true | medium — two syntaxes |
| tags: [OR logic] | Multiple tags = any match, not all | medium — common assumption |
| limit: null | Removes 50-item cap; required for "show me everything" | medium — default trap |
| "now" in absolute ranges | {before: "now"} is equivalent to "overdue" | low — equivalent forms |

### list-projects — **NEW SUITE NEEDED**

Shares many patterns with list_tasks but has unique fields.

**Uncovered fields/behaviors:**

| Field/Behavior | Why it needs a scenario | Trap potential |
|---------------|----------------------|----------------|
| reviewDueWithin: "now" | Review schedule, NOT due date; agent may confuse | high — semantic confusion |
| folder: name resolution | Substring matching may over-match | medium |
| Date filters on projects | Same syntax as list_tasks; effective from folders | low — same patterns |
| No "project" filter | list_projects doesn't have a "project" filter (projects ARE projects) | low — structural |

### list-tags — UP TO DATE (no scenarios needed)

Simple tool with trivial input payload. The availability enum difference (`"ALL"`, `"dropped"`) from list_tasks is notable but the trap would be better tested on list_tasks (where agents might try list_tags enum values).

### list-folders — UP TO DATE (no scenarios needed)

Even simpler than list_tags. Availability enum difference is minor. No meaningful payload trap.

### list-perspectives — UP TO DATE (no scenarios needed)

Only has `search`, `limit`, `offset`. No meaningful trap potential.

### get-tools (get_all, get_task, get_project, get_tag) — UP TO DATE (no scenarios needed)

Input is either empty (get_all) or just `{id: "string"}`. No payload construction trap. The `$inbox` rejection on get_project is behavioral (not a payload construction issue — the agent would still send a valid `{id: "$inbox"}` payload, it's just the wrong tool choice).

### Suites that DON'T need changes

| Suite | Why it's fine |
|-------|---------------|
| get_all | No input parameters — nothing to construct |
| get_task | Input is just `{id: string}` — trivial payload |
| get_project | Input is just `{id: string}` — trivial payload; $inbox error is tool selection, not payload construction |
| get_tag | Input is just `{id: string}` — trivial payload |
| list_tags | Input is simple (availability, search, pagination) — no non-obvious semantics |
| list_folders | Input is simpler than list_tags — no meaningful trap |
| list_perspectives | Input is just search + pagination — no trap potential |

---

## Trap Idea Bank

Creative trap concepts organized by category. Workers use these as starting points for collaborative scenario writing.

### Field Confusion

| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| FC-01 | "Unavailable tasks" → availability: "blocked", NOT defer filter. Defer is timing-only (1 of 4 blocking reasons) | list_tasks | availability, defer | hard | Most common agent mistake; availability covers ALL blocking reasons |
| FC-03 | "remaining" means available+blocked, NOT everything. completed/dropped still excluded | list_tasks | availability | medium | Default is misleading — "remaining" sounds like "all remaining" |
| FC-06 | inInbox: true vs project: "$inbox" — equivalent but contradictory combo errors | list_tasks | inInbox, project | medium | Two ways to filter inbox; combining them wrong causes confusing error |
| FC-07 | list_tags uses "ALL" and "dropped" in availability enum; list_tasks doesn't have these | list_tags vs list_tasks | availability | low | Cross-tool enum inconsistency |
| FC-08 | actions.move.after positions AMONG SIBLINGS, not "move into container" | edit_tasks | actions.move.after | medium | Agents confuse "after" (sibling order) with "ending" (container) |

### Implicit Requirements

| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| IR-01 | Using completed/dropped date filter auto-includes those lifecycle states; no separate availability setting needed | list_tasks | completed, dropped | hard | Default behavior hides completed/dropped; filter both restricts AND includes |
| IR-02 | "soon" includes overdue — defined as due < now + threshold, not just the gap | list_tasks | due | medium | Agent may think "soon" means "not yet overdue but close" |
| IR-03 | {this: "w"} = calendar week (Mon-Sun), not "last 7 days"; {last: "1w"} = rolling 7 days | list_tasks | any date filter | hard | Subtle distinction; real-world consequences for weekly planning |
| IR-05 | No availability filter → ["remaining"] → completed/dropped excluded; need explicit date filters to include them | list_tasks | availability | medium | "Show all tasks" still hides completed/dropped without date filter |

### Semantic Subtlety

| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| SS-01 | "Tasks I can work on" → availability: ["available"], NOT just "remaining" or a date filter | list_tasks | availability | medium | Agent must distinguish actionability from date filtering |
| SS-02 | "What's becoming available soon" → defer: {next: "1w"} (timing), NOT availability filter (state) | list_tasks | defer | hard | Requires understanding defer-as-timing vs availability-as-state |
| SS-03 | "Overdue tasks" → due: "overdue", NOT urgency filter (removed); agent may try old syntax | list_tasks | due | medium | Breaking change migration; docs guide but trap is habit |
| SS-04 | "This week's tasks" → due: {this: "w"} (calendar-aligned Mon-Sun). "Last 7 days" → due: {last: "1w"} (rolling) | list_tasks | due | hard | Two ways to say "week" with different semantics |
| SS-05 | "Show me completed tasks" → completed: "any" (not completed: true, which is a boolean and errors) | list_tasks | completed | medium | Breaking change from boolean to date filter |
| SS-06 | Date-only write input gets OmniFocus default time, not midnight | add_tasks, edit_tasks | dueDate, deferDate, plannedDate | medium | Agent may think date-only means midnight |
| SS-08 | "Projects due for review" → reviewDueWithin: "now", NOT due filter. Review schedule ≠ project due date | list_projects | reviewDueWithin, due | hard | Two different "due" concepts on projects |
| SS-09 | Folder name resolution uses substring — "Work" matches "Work", "Homework", "Network" | list_projects | folder | medium | Substring matching may surprise |

### Structural Traps

| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| ST-01 | due: "overdue" (string shortcut) vs due: {before: "now"} (absolute) — both valid, shortcut preferred | list_tasks | due | low | Understanding equivalent forms |
| ST-02 | list_projects has folder + reviewDueWithin but NO project filter (projects ARE projects) | list_projects | folder | low | Agent may try list_tasks patterns on list_projects |
| ST-03 | $inbox in different contexts: add_tasks parent (omit or "$inbox"), edit_tasks move (ending: "$inbox"), list_tasks filter (project: "$inbox") | multi-tool | parent, move, project | medium | Three tools, three syntaxes for inbox |

### Null Semantics

| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| NS-04 | Tasks with NULL date excluded from that date filter (not matched). "Tasks without a due date" not expressible via date filter (no "none" shortcut yet) | list_tasks | any date filter | medium | Silent exclusion of null-date tasks |

### Default Confusion

| ID | Trap Concept | Tool | Fields | Difficulty | Why It Matters |
|----|-------------|------|--------|------------|---------------|
| DC-01 | Default availability is ["remaining"] = available+blocked; to include completed, need completed: "any" | list_tasks | availability, completed | medium | "Show all tasks" requires understanding the default |
| DC-02 | Default limit is 50; "show me all tasks" needs limit: null to remove cap | list_tasks | limit | medium | Agent may forget pagination and miss results |
| DC-03 | Naive-local datetime is the default correct format; agents should produce `"2026-03-15T17:00:00"` not `"2026-03-15T17:00:00Z"`. Timezone offsets acceptable only when prompt data already contains them (e.g., calendar API output) | add_tasks, edit_tasks | date fields | medium | Grading distinction: MUST naive-local by default, SHOULD accept offsets only when source data has them |
| DC-04 | Date-only write input → OmniFocus default time (varies by field: due→5pm, defer→12am, planned→9am typically) | add_tasks, edit_tasks | dueDate, deferDate, plannedDate | medium | Not midnight; varies per field type |

---

## Summary of Work

| Suite | Action | New Scenarios | Updates |
|-------|--------|--------------|---------|
| list-tasks.md | Create new | ~13-15 | 0 |
| list-projects.md | Create new | ~5-6 | 0 |
| add-tasks.md | Update existing | ~2 | ~1-2 |
| edit-tasks.md | Update existing | ~2 | ~1 |
| **Total** | | **~22-25** | **~2-3** |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Run `/doc-suite-updater` one more time — it will enter Completion mode and archive this file
2. The worktree branch is now ready for the user to review and merge to main
