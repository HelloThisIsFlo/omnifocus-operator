# UAT Suite Analysis — v1.3.2 "Date Filtering"

## How to Use This File

This file is the output of a research session that analyzed what v1.3.2 changed vs what existing UAT suites cover. It contains everything a fresh agent needs to update the suites without re-doing the research.

**Workflow:** Run `/uat-suite-updater` in a new session. The skill auto-detects this file and enters Worker mode — it will find the next unchecked chunk, do targeted research, execute the changes, and mark the chunk done.

**Important:** The agent still needs to do its own targeted research for the specific suites it's updating — the gap tables below are a starting point, not exhaustive. The agent should verify against actual source code, especially for exact warning strings.

---

## Progress

- [ ] Chunk 1 — Date Filtering Suite: Shortcuts & Lifecycle
- [ ] Chunk 2 — Date Filtering Suite: Absolute Bounds, Combos & Warnings
- [ ] Chunk 3 — Availability Migration: list_tasks
- [ ] Chunk 4 — Date Filter Validation + list_projects [] fix + Composites
- [ ] **Delete this file** (all chunks done, everything merged)

---

## Chunks — Task List

### Chunk completion protocol

After finishing the suite edits for a chunk, the agent does NOT commit. Instead:

1. **Summarize changes** — list every file modified, tests added, assertions fixed
2. **Tell the user what to review** — which suite files to read, what to look for
3. **Suggest spot-checks** — specific things the user can try in OmniFocus via the MCP tools
4. **Wait for validation** — user reviews, tries the spot-checks, gives thumbs up or requests changes
5. **On approval**: commit the suite changes, then update the Progress checklist above (check the box)

---

### Chunk 1: Date Filtering Suite — Shortcuts & Lifecycle

**Suites:** NEW `.claude/skills/uat-regression/tests/date-filtering.md`

**What to do:**

Create a new test suite for `list_tasks` date filtering — the biggest new feature in v1.3.2. This chunk covers string shortcuts, lifecycle date filters, and shorthand periods.

**Setup requirements:**
- Tasks with known dates (dueDate, deferDate, plannedDate) — both past and future
- A completed task and a dropped task (reuse from other suites or create fresh)
- At least one task with NO due date (to verify exclusion behavior)
- Tasks should use `DF-` prefix for search isolation
- All tasks under a single inbox parent `UAT-DateFiltering`

**Tests to write (~15):**

| # | Category | Test | What to verify |
|---|----------|------|----------------|
| 1a | Due shortcuts | `due: "overdue"` | Tasks with effectiveDueDate before now returned; tasks with no due date excluded; future due dates excluded |
| 1b | Due shortcuts | `due: "soon"` | Tasks due within threshold returned; includes overdue tasks (overdue is subset of soon) |
| 1c | Due shortcuts | `due: "today"` | Tasks due today only; equivalent to `due: {this: "d"}` |
| 2a | Lifecycle | `completed: "all"` | All completed tasks returned regardless of completion date; auto-includes completed availability |
| 2b | Lifecycle | `dropped: "all"` | All dropped tasks returned; auto-includes dropped availability |
| 2c | Lifecycle | `completed: "today"` | Only tasks completed today (if any); auto-inclusion still active |
| 2d | Lifecycle | `completed: {last: "1w"}` | Tasks completed within last 7 days |
| 2e | Lifecycle auto-include | `completed: "all"` without setting availability | Completed tasks appear without explicit availability — date filter triggers auto-inclusion |
| 2f | Lifecycle + empty avail | `availability: ["available"], completed: "all"` | Active available tasks AND all completed tasks — both filters applied |
| 3a | Shorthand | `due: {this: "w"}` | Tasks due within current calendar week (week start per OPERATOR_WEEK_START) |
| 3b | Shorthand | `due: {last: "3d"}` | Tasks due in last 3 full days + partial today |
| 3c | Shorthand | `due: {next: "1w"}` | Tasks due within rest of today + next 7 full days |
| 3d | Non-due field | `defer: "today"` | Tasks with defer date today |
| 3e | Non-due field | `added: "today"` | Tasks added today (test tasks just created should match) |
| 4a | Soon ⊃ overdue | `due: "soon"` on tasks that are overdue | Overdue tasks ALSO appear in "soon" results — "soon" means `due < now + threshold`, overdue is a strict subset |
| 4b | Inherited dates | `due: "overdue"` on task with inherited effective due | Task has no direct dueDate but effectiveDueDate inherited from project. Must appear in results. |
| 4c | Inherited dates | `due: {before: "<future>"}` on inherited task | Same inherited-date task caught by absolute filter too |

**Suite conventions to follow:**
- Search isolation: include `search: "DF-"` on every test
- 1-item limit where possible to control response size
- Every lifecycle test verifies auto-inclusion by NOT setting availability (or using default)
- "PASS if" criteria on every test
- Tests that verify warnings must quote the expected warning substring
- Setup needs a project with a dueDate and a child task with no direct dueDate (for inheritance tests 4b/4c)

**W021 note:** The due-soon fallback warning (W021: "Due-soon threshold was not detected") is NOT testable in standard UAT — the hybrid repo always reads the setting from SQLite. This is covered by automated tests only. If a future "interactive fallback mode" UAT section is added, it could go there (user manually sets env vars and restarts server).

**Est. scope:** ~17 new tests, 1 new file.

---

### Chunk 2: Date Filtering Suite — Absolute Bounds, Combos & Warnings

**Suites:** `.claude/skills/uat-regression/tests/date-filtering.md` (append to file from Chunk 1)

**What to do:**

Add sections for absolute date bounds, combined date filters, defer hint warnings, multi-dimension filters, and edge cases to the date filtering suite.

**Tests to write (~15):**

| # | Category | Test | What to verify |
|---|----------|------|----------------|
| 5a | Absolute | `due: {before: "<future-date>"}` | Tasks with due date before the given date returned |
| 5b | Absolute | `due: {after: "<past-date>"}` | Tasks with due date after the given date returned |
| 5c | Absolute | `due: {after: "<date-A>", before: "<date-B>"}` | Tasks within range; both bounds inclusive |
| 5d | Absolute | `due: {before: "now"}` | Equivalent to "overdue" — same result set as test 1a |
| 5e | Absolute | `due: {after: "now"}` | Tasks with future due dates only |
| 6a | Combos | `due: "overdue"` + `project: "<name>"` | Date filter AND base filter; only overdue tasks in that project |
| 6b | Combos | `completed: "all"` + `search: "<term>"` | Completed tasks matching search |
| 6c | Combos | `due: "today"` + `flagged: true` | Tasks due today AND flagged |
| 6d | Combos | Multiple date dims: `due: "today"` + `defer: {before: "now"}` | Both date filters applied with AND logic |
| 7a | Defer hints | `defer: {after: "now"}` | Warning W022: "Tip: This shows tasks with a future defer date. For all unavailable tasks regardless of reason, use availability: 'blocked'." |
| 7b | Defer hints | `defer: {before: "now"}` | Warning W023: "Tip: This shows tasks whose defer date has passed. For all currently available tasks, use availability: 'available'." |
| 8a | Other fields | `modified: {last: "1w"}` | Tasks modified within last week returned |
| 8b | Other fields | `planned: "today"` | Tasks with planned date today |
| 9a | Edge: no date | `due: "overdue"` on tasks without dueDate | Tasks with no due date excluded (not treated as overdue) |
| 9b | Edge: round-trip | Filter → `get_task` on result | Dates on returned task are consistent with filter expectations |

**Notes for the worker:**
- Tests 5a-5e need concrete date values from setup tasks. Use known dueDate values from setup.
- Test 5d equivalence: compare result set with test 1a from Chunk 1.
- Defer hint tests (7a, 7b): these are WARNINGS, not errors — the query still executes and returns results. The hint is appended to the warnings array.
- For test 6d, the task needs both a due date (today) and a defer date (in the past) to match.

**Also add:**
- Report Table Rows section covering ALL tests from both Chunk 1 and Chunk 2
- A setup note about what dates to set on test tasks to make all tests work (this may require adjusting the Chunk 1 setup section)

**Est. scope:** ~15 new tests appended to existing file.

---

### Chunk 3: Availability Migration — list_tasks

**Suites:** `.claude/skills/uat-regression/tests/list-tasks.md`

**What to do:**

The `AvailabilityFilter` enum was trimmed in v1.3.2:
- **Removed:** `completed`, `dropped`, `ALL`
- **Kept:** `available`, `blocked`
- **Added:** `remaining` (expands to available + blocked; is the new default)

Lifecycle state is now expressed exclusively via date filters on `list_tasks`. Tests that used `availability: ["completed"]` etc. must be rewritten to use date filters instead.

**Three overridden requirements** (accepted by Flo): no custom educational errors for `urgency`, `completed: true`, or `availability: "all"` — these hit the Pydantic boundary with generic validation errors. No backward compat needed (pre-release project).

**Assertion fixes (~7):**

1. **Test 2b (Include COMPLETED):** Was `availability: ["available", "blocked", "completed"]`. Rewrite to: `completed: "all", search: "LT-"` — PASS if LT-Completed appears, LT-Dropped does NOT.

2. **Test 2c (Include DROPPED):** Was `availability: ["available", "blocked", "dropped"]`. Rewrite to: `dropped: "all", search: "LT-"` — PASS if LT-Dropped appears, LT-Completed does NOT.

3. **Test 2d (All four states):** Was `availability: ["available", "blocked", "completed", "dropped"]`. Rewrite to: `completed: "all", dropped: "all", search: "LT-"` — PASS if ALL LT-* tasks appear.

4. **Test 2f (ALL shorthand):** Was `availability: ["ALL"]`. Rewrite to: `availability: ["remaining"], search: "LT-"` — PASS if all available + blocked tasks appear (same as default). Note: this no longer includes completed/dropped. To get "everything", combine with `completed: "all", dropped: "all"`.

5. **Test 2g (ALL mixed warning):** Was `availability: ["ALL", "available"]`. Rewrite to test REMAINING redundancy instead: `availability: ["remaining", "available"], search: "LT-"` — PASS if warning W029: "'remaining' already includes 'available'"; results still include all available+blocked tasks.

6. **Test 5b (Tag + COMPLETED combo):** Was `tags: [...], availability: ["available", "blocked", "completed"]`. Rewrite to: `tags: ["<tag-a-name>"], completed: "all", search: "LT-"` — PASS if LT-Tagged-A, LT-Tagged-AB, AND LT-Completed all appear.

7. **Test 8d (availability: [] — behavior change):** `availability: []` is now **ACCEPTED** on list_tasks (the `_reject_empty_availability` validator was removed in Phase 47). Empty list means "no active-state tasks" — returns nothing unless date filters add lifecycle tasks. Rewrite from an error test to a behavior test: `list_tasks` with `availability: [], search: "LT-"` — PASS if: `items` is empty (no active tasks match empty availability); `total: 0`. Then test the combo: `availability: [], completed: "all", search: "LT-"` — PASS if: only LT-Completed appears (empty availability + lifecycle inclusion = completed-only query).

**New tests (~3):**

1. **Test 2f-new: REMAINING explicit** — `availability: ["remaining"], search: "LT-"` — PASS if: same result as default (2a); available + blocked tasks appear, completed/dropped excluded.

2. **Test 2g-new: REMAINING + BLOCKED redundancy** — `availability: ["remaining", "blocked"], search: "LT-"` — PASS if: warning W030 "'remaining' already includes 'blocked'"; results still correct.

3. **Test 2h: "completed" as availability value — error** — Run INDIVIDUALLY: `availability: ["completed"], search: "LT-"` — PASS if: Pydantic enum validation error (clean, no internals); "completed" is not a valid AvailabilityFilter value. No custom educational error (override accepted).

**Also update:**
- Suite description (line 3): add "date filtering" and "remaining" to the feature list
- Test 2a description: clarify default is REMAINING which expands to available + blocked
- Test 3f (Inbox warning): verify PASS criteria — the warning text may have changed (now says `inInbox=true` only, no longer mentions `$inbox`). Worker agent should check `LIST_TASKS_INBOX_PROJECT_WARNING` in `warnings.py`.

**Est. scope:** ~3 new tests + ~7 assertion fixes.

---

### Chunk 4: Date Filter Validation + list_projects [] fix + Composites

**Suites:** `.claude/skills/uat-regression/tests/list-projects.md`, `.claude/skills/uat-regression/tests/validation-errors.md`, `.claude/skills/uat-regression/tests/reads-combined.md`

**What to do — list_projects.md:**

**IMPORTANT — Known gap, DO NOT rewrite availability tests.** `list_projects` shares the trimmed `AvailabilityFilter` (available, blocked, remaining) but has NO date filters. This means completed/dropped projects cannot be queried via `list_projects` at all — this is a known gap that will be addressed in a future phase (separate from v1.3.2).

Tests 2b, 2c, 2d, 2f, 2g, and 6c use removed enum values ("completed", "dropped", "ALL") and **will fail when run**. This is correct — the failures document the gap. **Leave these tests as-is.** Do NOT convert them to error tests or remove them.

**One fix needed:**

1. **Test 9c (availability: [] — behavior change):** Same as list_tasks test 8d — `availability: []` is now **ACCEPTED** (validator removed in Phase 47). Rewrite from error test to behavior test: `list_projects` with `availability: []` — PASS if: `items` is empty (no projects match empty availability); no error raised.

**What to do — validation-errors.md:**

Add a new section "8. v1.3.2 Date Filter Validation" with 8 tests for the new date filter error messages:

| # | Test | Input | Expected Error Pattern |
|---|------|-------|----------------------|
| 8a | Mixed groups | `list_tasks` with `due: {last: "3d", before: "2026-04-01"}` | "Cannot mix shorthand (this/last/next) with absolute (before/after)" |
| 8b | Multiple shorthand | `list_tasks` with `due: {this: "w", last: "3d"}` | "Only one shorthand key allowed per date filter" |
| 8c | Empty date filter | `list_tasks` with `due: {}` | "Date filter must specify at least one key" |
| 8d | Invalid duration | `list_tasks` with `due: {last: "3x"}` | "Invalid duration '3x'" with format guidance |
| 8e | Invalid this-unit | `list_tasks` with `due: {this: "week"}` | "Invalid period unit 'week' for 'this'" with valid units |
| 8f | Zero count | `list_tasks` with `due: {last: "0d"}` | "Duration count must be positive" |
| 8g | Reversed bounds | `list_tasks` with `due: {after: "2026-12-31", before: "2026-01-01"}` | "Invalid date range: 'after' ... is later than 'before'" |
| 8h | Invalid absolute | `list_tasks` with `due: {before: "not-a-date"}` | "Invalid date value 'not-a-date'" with format guidance |

All 8 tests run INDIVIDUALLY (they error). Standard validation suite conventions apply: no `type=`, `pydantic`, `input_value`, `_Unset` in any error message.

**Also add:**
- Report table rows for the new section
- Update suite description to mention v1.3.2 date filter errors

**What to do — reads-combined.md:**

- Add date filtering suite as section **E** in the composite table
- Update total test count (130 → 130 + date filtering count from chunks 1+2)
- Keep existing A-D order unchanged

**Est. scope:** ~8 new tests + ~1 assertion fix + 1 structural update.

---

## Reference Material

Everything below is research output — the chunks above reference it.

---

## What v1.3.2 Built

**Phase 45 — Date Models & Resolution (completed 2026-04-07):**
- `DateFilter` contract model with 5 optional fields (this/last/next/before/after), mutual exclusion between shorthand and absolute groups
- `DueDateShortcut` enum: overdue, soon, today
- `LifecycleDateShortcut` enum: all, today (renamed from "any" to "all" in Phase 47)
- 7 new date filter fields on `ListTasksQuery`: due, defer, planned, completed, dropped, added, modified
- Pure `resolve_date_filter()` function converting all input forms to absolute bounds
- `DueSoonSetting` enum: 7 discrete OmniFocus threshold options
- `Settings` class via pydantic-settings: `OPERATOR_WEEK_START`, `OPERATOR_DUE_SOON_THRESHOLD`
- 8 new error constants, 10 new description constants

**Phase 46 — Pipeline & Query Paths (completed 2026-04-08):**
- `get_due_soon_setting()` on repository protocol (hybrid reads SQLite, bridge reads env var)
- SQL date predicates using effective CF epoch columns (effectiveDateDue, effectiveDateToStart, etc.)
- Bridge in-memory date filtering using Python comparisons on Task model attributes
- `_resolve_date_filters()` pipeline step in `_ListTasksPipeline`
- Lifecycle auto-inclusion: completed/dropped date filters automatically add availability states
- `DomainLogic` extraction: resolve_date_filters(), expand_task_availability(), expand_review_due()

**Phase 47 — Cross-Path Equivalence & Breaking Changes (completed 2026-04-08):**
- `AvailabilityFilter` trimmed: removed COMPLETED, DROPPED, ALL; added REMAINING
- `LifecycleDateShortcut.ANY` → `.ALL` (value: "all")
- REMAINING expands to [AVAILABLE, BLOCKED] at service layer
- `availability: []` now ACCEPTED on list_tasks and list_projects (validators removed) — enables `availability: [], completed: "all"` for lifecycle-only queries
- Defer hints: W022 (after=now) and W023 (before=now) appended as tips
- Tool descriptions updated with date filter syntax documentation
- Cross-path equivalence tests with inherited effective dates
- Three BREAK requirements overridden (no custom educational errors for urgency, completed:true, availability:"all")

---

## Gap Analysis by Suite

### date-filtering.md (NEW — 0 tests) — NEEDS CREATION

This is the biggest gap. v1.3.2 adds 7 date filter dimensions to `list_tasks` with 3 input forms each, lifecycle auto-inclusion, warnings, and hints. No existing suite covers any of this.

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Due shortcuts | overdue, soon, today | Core feature — 3 most common date queries |
| Lifecycle shortcuts | completed: "all", dropped: "all" | The ONLY way to include lifecycle tasks in v1.3.2 |
| Lifecycle date range | completed: {last: "1w"}, completed: "today" | Scoped lifecycle inclusion |
| Auto-inclusion | completed filter without setting availability | Verifies the auto-inclusion mechanism |
| Shorthand periods | this/last/next with d/w/m units | Period resolution across all input forms |
| Absolute bounds | before/after with dates and "now" | Absolute date range filtering |
| Combined filters | date + project, date + search, date + flagged | AND logic with existing base filters |
| Multi-dimension | due + defer, due + completed | Multiple date filters on same query |
| Defer hints | defer: {after/before: "now"} | W022/W023 tip warnings |
| Soon fallback | due: "soon" without threshold | W021 fallback warning |
| No-date exclusion | due filter on tasks without dueDate | Tasks without dates are excluded, not matched |
| Round-trip | filter → get_task verification | Dates on returned tasks match expectations |
| Non-due fields | added, modified, planned, defer "today" | Coverage across all 7 dimensions |
| Inherited dates | task with no direct due but effective due from project | Verifies date filters use effective (inherited) values end-to-end |
| Soon ⊃ overdue | overdue task appears in "soon" results | Counterintuitive but intentional — "soon" = `due < now + threshold` |

---

### list-tasks.md (47 tests) — NEEDS UPDATES

**Tests that WILL FAIL with current code (removed enum values):**

| Test | Current Input | Problem | Fix |
|------|--------------|---------|-----|
| 2b | `availability: ["available", "blocked", "completed"]` | "completed" not in AvailabilityFilter | Use `completed: "all"` date filter |
| 2c | `availability: ["available", "blocked", "dropped"]` | "dropped" not in AvailabilityFilter | Use `dropped: "all"` date filter |
| 2d | `availability: ["available", "blocked", "completed", "dropped"]` | Both removed | Use `completed: "all", dropped: "all"` |
| 2f | `availability: ["ALL"]` | "ALL" not in AvailabilityFilter | Use `availability: ["remaining"]` |
| 2g | `availability: ["ALL", "available"]` | "ALL" not valid | Test REMAINING+available redundancy (W029) |
| 5b | `tags: [...], availability: [..., "completed"]` | "completed" not valid | Use `completed: "all"` |

**Tests that may need assertion updates:**

| Test | Issue |
|------|-------|
| 2a | Description says "default is AVAILABLE + BLOCKED" — still true but default is now REMAINING |
| 3f | Warning text may no longer mention `$inbox` (only `inInbox=true`) |
| 8d | `availability: []` is now ACCEPTED (validator removed) — rewrite as behavior test, not error test |

**New tests needed:**

| Test | Why |
|------|-----|
| REMAINING explicit | Verify `["remaining"]` produces same results as default |
| REMAINING + BLOCKED redundancy | W030 warning |
| "completed" as availability error | Enum validation error (no custom educational error — override accepted) |

---

### list-projects.md (33 tests) — KNOWN GAP (DO NOT REWRITE)

`list_projects` shares the trimmed `AvailabilityFilter` but has NO date filters. This is a **known gap** — completed/dropped projects are not queryable in v1.3.2. A future phase will either restore these enum values on list_projects or add date filters.

**Tests that WILL FAIL (leave as-is — failures document the gap):**

| Test | Current Input | Why it fails |
|------|--------------|-------------|
| 2b | `availability: ["available", "blocked", "completed"]` | "completed" removed from AvailabilityFilter |
| 2c | `availability: ["available", "blocked", "dropped"]` | "dropped" removed |
| 2d | `availability: ["available", "blocked", "completed", "dropped"]` | Both removed |
| 2f | `availability: ["ALL"]` | "ALL" removed |
| 2g | `availability: ["ALL", "dropped"]` | "ALL" and "dropped" removed |
| 6c | `availability: ["completed"]` | "completed" removed |

**One behavior change (DOES need updating):**

| Test | Issue |
|------|-------|
| 9c | `availability: []` is now ACCEPTED (validator removed) — rewrite as behavior test |

---

### validation-errors.md (27 tests) — NEEDS UPDATES

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| Date filter: mixed groups | shorthand + absolute in same filter | E031 — new validation |
| Date filter: multiple shorthand | two shorthand keys | E032 |
| Date filter: empty | `due: {}` | E033 |
| Date filter: invalid duration | `{last: "3x"}` | E034 |
| Date filter: invalid this-unit | `{this: "week"}` | E035 |
| Date filter: zero count | `{last: "0d"}` | E036 |
| Date filter: reversed bounds | after > before | E037 |
| Date filter: invalid absolute | `{before: "not-a-date"}` | E038 |

**Existing tests that may need assertion updates:**
- Test 3b (invalid availability): verify error message format is still clean with trimmed enum

---

### simple-list-tools.md (23 tests) — UP TO DATE

Uses `TagAvailabilityFilter` and `FolderAvailabilityFilter` which are UNCHANGED in v1.3.2. Tag tools still have ALL shorthand. Folder tools still have ALL shorthand. No changes needed.

---

### Suites that DON'T need changes

| Suite | Why it's fine |
|-------|---------------|
| read-lookups.md | get_task/get_project/get_tag unaffected by date filtering |
| task-creation.md | add_tasks has no date filter parameters |
| edit-operations.md | edit_tasks has no date filter parameters |
| tag-operations.md | Tag semantics unchanged |
| move-operations.md | Move semantics unchanged |
| lifecycle.md | Tests write-side lifecycle actions, not read-side filtering |
| inheritance.md | Tests effective field inheritance for writes, not date-filtered reads |
| integration-flows.md | End-to-end write-through flows, no list filtering |
| repetition-rules.md | Repetition rule semantics unchanged |
| simple-list-tools.md | Tag/Folder/Perspective availability enums unchanged |
| writes-combined.md | Composite of unchanged write suites |

---

## Warning/Error Inventory

Every new warning/error from v1.3.2 that needs at least one UAT test:

### Errors

| ID | Text Pattern | Covered By |
|----|-------------|------------|
| E031 | "Cannot mix shorthand (this/last/next) with absolute (before/after)..." | Chunk 4 → validation-errors 8a |
| E032 | "Only one shorthand key allowed per date filter..." | Chunk 4 → validation-errors 8b |
| E033 | "Date filter must specify at least one key..." | Chunk 4 → validation-errors 8c |
| E034 | "Invalid duration '{value}'..." | Chunk 4 → validation-errors 8d |
| E035 | "Invalid period unit '{value}' for 'this'..." | Chunk 4 → validation-errors 8e |
| E036 | "Duration count must be positive..." | Chunk 4 → validation-errors 8f |
| E037 | "Invalid date range: 'after' ... is later than 'before'..." | Chunk 4 → validation-errors 8g |
| E038 | "Invalid date value '{value}'..." | Chunk 4 → validation-errors 8h |

### Warnings

| ID | Text Pattern | Covered By |
|----|-------------|------------|
| W021 | "Due-soon threshold was not detected. Defaulting to today." | Automated tests only — not triggerable in standard UAT (hybrid repo always reads SQLite setting) |
| W022 | "Tip: This shows tasks with a future defer date..." | Chunk 2 → date-filtering 7a |
| W023 | "Tip: This shows tasks whose defer date has passed..." | Chunk 2 → date-filtering 7b |
| W029 | "'remaining' already includes 'available'..." | Chunk 3 → list-tasks 2g (rewritten) |
| W030 | "'remaining' already includes 'blocked'..." | Chunk 3 → list-tasks new test |

---

## Combined Suite Strategy

**reads-combined.md** needs one structural change:

- Add section **E — Date Filtering** pointing to `date-filtering.md`
- Update total from 130 to 130 + (Chunk 1 tests + Chunk 2 tests)
- Existing A-D sections unchanged

No other composite changes needed. The `writes-combined.md` is unaffected.

---

## Summary of Work

| Suite | Action | New Tests | Assertion Fixes |
|-------|--------|-----------|-----------------|
| date-filtering.md | **Create** | ~32 | 0 |
| list-tasks.md | Update | ~3 | ~7 |
| list-projects.md | Leave as-is (known gap) | 0 | ~1 (test 9c only) |
| validation-errors.md | Update | ~8 | 0 |
| reads-combined.md | Structural | 0 | 0 |
| **Total** | | **~43** | **~8** |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Run `/uat-suite-updater` one more time — it will enter Completion mode and archive this file
2. The worktree branch is now ready for the user to review and merge to main
