# UAT Suite Analysis — v1.3.2 "Date Filtering"

## How to Use This File

This file is the output of a research session that analyzed what v1.3.2 changed vs what existing UAT suites cover. It contains everything a fresh agent needs to update the suites without re-doing the research.

**Workflow:** Run `/uat-suite-updater` in a new session. The skill auto-detects this file and enters Worker mode — it will find the next unchecked chunk, do targeted research, execute the changes, and mark the chunk done.

**Important:** The agent still needs to do its own targeted research for the specific suites it's updating — the gap tables below are a starting point, not exhaustive. The agent should verify against planning docs, especially for exact warning strings.

**Context:** This is a re-seed. The original seed had chunks 1-2 completed (created the `date-filtering.md` suite with 32 tests) and chunks 3-4 remaining. After rebasing on gap-closure fixes (plans 47-03 through 47-06), the analysis was regenerated from scratch. The date-filtering suite is now UP TO DATE — the remaining work is about availability migration and validation errors.

---

## Progress

- [x] Chunk 1 — list_tasks Availability Migration
- [x] Chunk 2 — Date Filter Validation + Composites
- [ ] **Delete this file** (all chunks done, everything merged)

---

## Chunks — Task List

### Chunk completion protocol

After finishing the suite edits for a chunk, the agent does NOT commit. Instead:

1. **Present assumptions** — list any assumptions about live behavior that the suite relies on (exact warning text, filter results, edge cases)
2. **Offer self-verification** — "Want me to run these checks myself against your live OmniFocus?" If approved, the agent creates minimal test tasks via MCP, runs the checks, reports results, and cleans up (see Worker Mode Step 4 in the skill for the full protocol). If a discrepancy is found, the agent updates the suite before proceeding.
3. **Summarize changes** — list every file modified, tests added, assertions fixed, and verification results if applicable
4. **Wait for sign-off** — user reviews the changes
5. **On approval**: commit the suite changes, then update the Progress checklist above (check the box)

---

### Chunk 1: list_tasks Availability Migration

**Suites:** `list-tasks.md`

**Why:** v1.3.2 removed `COMPLETED`, `DROPPED`, and `ALL` from the `list_tasks` AvailabilityFilter enum. New valid values are `available`, `blocked`, `remaining`. Empty list `[]` is now valid (returns 0 items). Two new redundancy warnings (W-004, W-005) were added for REMAINING overlap.

**What to do:**

**Tests to REMOVE** (availability values no longer valid for list_tasks):

| Test | Was | Why Remove |
|------|-----|------------|
| 2b | `availability: ["available", "blocked", "completed"]` | "completed" not valid; lifecycle inclusion now via date filters (see date-filtering tests 2a-2f) |
| 2c | `availability: ["available", "blocked", "dropped"]` | "dropped" not valid; lifecycle inclusion via date filters |
| 2d | `availability: ["available", "blocked", "completed", "dropped"]` | Both invalid; old "all four states" concept replaced by lifecycle date filters |
| 2f | `availability: ["ALL"]` | ALL removed from enum; no single-value equivalent |
| 2g | `availability: ["ALL", "available"]` | ALL invalid; old redundancy warning no longer applicable |

**Tests to REWRITE:**

| Test | Was | Becomes |
|------|-----|---------|
| 5b | `tags: [tag-a], availability: [..., "completed"]` — combo with COMPLETED | `tags: [tag-a], completed: "all"` — same AND-logic test but using lifecycle date filter instead of explicit availability. PASS if: LT-Tagged-A, LT-Tagged-AB, AND LT-Completed appear (LT-Completed has tag-a and is made visible by the `completed` date filter's auto-inclusion) |
| 8d | `availability: []` → error | Move from section 8 (error tests) to section 2 (availability). Now a positive test: `availability: []` → items empty, total 0, hasMore false. This is valid behavior — empty availability means "show tasks in zero availability states." |

**NEW tests to ADD** (in section 2, after test 2e which stays unchanged):

1. **Test 2f (new): REMAINING shorthand**
   - `list_tasks` with `availability: ["remaining"], search: "LT-"`
   - PASS if: same result set as test 2a (default availability) — `remaining` = available + blocked. LT-Completed and LT-Dropped excluded. All other LT-* tasks present.

2. **Test 2g (new): Empty availability — zero items**
   - `list_tasks` with `availability: [], search: "LT-"`
   - PASS if: `items` is empty array; `total: 0`; `hasMore: false`. Empty list is valid and returns nothing — useful when combined with lifecycle date filters for exclusive queries.

3. **Test 2h (new): Exclusive lifecycle query — only completed**
   - `list_tasks` with `availability: [], completed: "all", search: "LT-"`
   - PASS if: ONLY LT-Completed appears. No remaining tasks. The lifecycle auto-include adds COMPLETED on top of the empty availability base, producing exclusively lifecycle results.

4. **Test 2i (new): REMAINING + available redundancy — W-004**
   - `list_tasks` with `availability: ["available", "remaining"], search: "LT-"`
   - PASS if: warning text includes "'remaining' already includes 'available'" (or equivalent); results still include all remaining tasks (filter works despite redundancy)

5. **Test 2j (new): REMAINING + blocked redundancy — W-005**
   - `list_tasks` with `availability: ["blocked", "remaining"], search: "LT-"`
   - PASS if: warning text includes "'remaining' already includes 'blocked'" (or equivalent); results still include all remaining tasks

**Report table updates:**
- Remove rows for old 2b, 2c, 2d, 2f, 2g
- Add rows for new 2f through 2j
- Update 5b row description to reflect lifecycle date filter combo
- Move old 8d row to section 2 (reworded as positive test)
- The 8d slot in section 8 is simply gone (3 null/empty tests remain: 8a, 8b, 8c)
- Renumber section 8 if needed (8a→8a, 8b→8b, 8c→8c — no change since 8d was last)

**Est. scope:** ~5 removed + 2 rewritten + 5 new = ~12 test changes.

---

### Chunk 2: Date Filter Validation + Composites

**Suites:** `validation-errors.md`, `reads-combined.md`, `SKILL.md`

**Why:** v1.3.2 introduced DateFilter validation (8 error types) and breaking-change rejections (4 error types). The validation-errors suite needs new tests covering these. Also, the date-filtering suite count in composites is wrong (says 17, actual is 32), and list-tasks count will change from Chunk 1.

**What to do in validation-errors.md:**

**Test to REMOVE:**

| Test | Was | Why |
|------|-----|-----|
| 5d | `availability: []` on list_tasks → error "cannot be empty" mentioning `["ALL"]` | No longer an error for list_tasks (returns 0 items). ALL also no longer exists. Concept still tested via simple-list-tools test 6b (list_folders). |

**Test to UPDATE:**

| Test | Change |
|------|--------|
| 3b | Update assertion: valid availability values for list_tasks are now `available`, `blocked`, `remaining` (not `available`, `blocked`, `completed`, `dropped`). The error text should reflect the new enum. |

**NEW tests — DateFilter validation (add as section 8):**

All run INDIVIDUALLY. All use `list_tasks`. All must NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`.

1. **Test 8a: DateFilter — invalid "this" unit**
   - `list_tasks` with `due: {this: "2w"}`
   - PASS if: error mentions that `this` only accepts single calendar units (d, w, m, y); does NOT accept count+unit

2. **Test 8b: DateFilter — zero/negative count**
   - `list_tasks` with `due: {next: "0d"}`
   - PASS if: error mentions zero or negative count; suggests using correct unit/count or `last` for going backwards

3. **Test 8c: DateFilter — invalid duration unit**
   - `list_tasks` with `due: {last: "3x"}`
   - PASS if: error mentions invalid unit `x`; lists valid units (d, w, m, y)

4. **Test 8d: DateFilter — after > before ordering**
   - `list_tasks` with `due: {after: "2026-03-15T12:00:00Z", before: "2026-03-10T12:00:00Z"}`
   - PASS if: error mentions 'after' must be before or equal to 'before'; shows the actual values

5. **Test 8e: DateFilter — mixed shorthand and absolute**
   - `list_tasks` with `due: {this: "w", after: "2026-03-01T00:00:00Z"}`
   - PASS if: error mentions cannot mix shorthand (this/last/next) and absolute (before/after)

6. **Test 8f: DateFilter — empty object**
   - `list_tasks` with `due: {}`
   - PASS if: error mentions DateFilter requires either shorthand or absolute bounds

**NEW tests — Breaking change validation (add as section 9):**

All run INDIVIDUALLY. All use `list_tasks`. All must NOT contain `type=`, `pydantic`, `input_value`, or `_Unset`.

1. **Test 9a: Removed availability value — "all"**
   - `list_tasks` with `availability: ["all"]`
   - PASS if: error rejects "all" as invalid; valid values shown are `available`, `blocked`, `remaining`

2. **Test 9b: Removed availability value — "completed"**
   - `list_tasks` with `availability: ["completed"]`
   - PASS if: error rejects "completed" as invalid; same valid-value guidance

3. **Test 9c: Boolean completed — removed**
   - `list_tasks` with `completed: true`
   - PASS if: error rejects boolean; the `completed` field expects a string shortcut or DateFilter object, not a boolean

**Report table updates:**
- Remove 5d row
- Update 3b row description
- Add section 8 rows (8a-8f: DateFilter validation)
- Add section 9 rows (9a-9c: breaking change validation)

**What to do in reads-combined.md:**

Update the composite suite table:

| Change | Old | New |
|--------|-----|-----|
| Suite A (List Tasks) test count | 47 | 46 (Chunk 1 removes 5, adds 5, converts 1: net -1) |
| Suite B (Date Filtering) test count | 17 | 32 (was always 32, count was wrong) |
| Suite E (Validation & Errors) test count | 27 | 35 (removes 1, adds 9: net +8) |
| Total | 147 | 169 |

**What to do in SKILL.md:**

Update the suite table row for Date Filtering:

| Change | Old | New |
|--------|-----|-----|
| Date Filtering test count | 17 | 32 |
| Reads Combined test count | 147 | 169 |
| List Tasks test count | 47 | 46 |
| Validation & Errors test count | 27 | 35 |

Also verify the Date Filtering "Covers" description matches the actual suite content (32 tests cover: shortcuts, lifecycle, shorthand, absolute bounds, combos, defer hints, non-due fields, edge cases, inherited dates).

**Est. scope:** ~1 removed + 1 updated + 9 new tests + 4 count fixes = ~15 changes.

---

## Reference Material

Everything below is research output — the chunks above reference it.

---

## What v1.3.2 Built

**Milestone goal:** Agents can filter tasks by any date dimension using string shortcuts, shorthand periods, or absolute bounds.

### Theme 1: Date Filter Infrastructure (Phase 45)
- 7 date dimensions: due, defer, planned, completed, dropped, added, modified
- 3 input forms: string shortcuts (`"overdue"`, `"soon"`, `"today"`, `"all"`), shorthand periods (`{this: "w"}`, `{last: "3d"}`, `{next: "1w"}`), absolute bounds (`{before: "...", after: "..."}`)
- `DateFilter` contract model with mutual-exclusion validation
- Field-specific shortcut enums: `DueDateShortcut` (overdue/soon/today), `LifecycleDateShortcut` (all/today), `DateFieldShortcut` (today)
- Pure `resolve_date_filter()` function converting all forms to absolute datetime range
- Config centralization: `OPERATOR_WEEK_START`, `OPERATOR_DUE_SOON_THRESHOLD`

### Theme 2: Pipeline Integration (Phase 46)
- Service pipeline `_resolve_date_filters()` with single `now` snapshot per query
- SQL date predicates on 7 effective CF epoch columns
- Bridge in-memory filtering with identical semantics
- Lifecycle auto-inclusion: `completed`/`dropped` date filter automatically adds those availability states
- `get_due_soon_setting()` reads OmniFocus Settings table (Hybrid) or env var (BridgeOnly)
- `ResolvedDateBounds` dataclass with datetime bounds + warnings list
- Due-soon fallback: defaults to TODAY when threshold unavailable, emits warning

### Theme 3: Breaking Changes & Cross-Path (Phase 47)
- AvailabilityFilter trimmed: removed COMPLETED, DROPPED, ALL; kept AVAILABLE, BLOCKED; added REMAINING
- `LifecycleDateShortcut.ANY` renamed to `ALL` (reads more naturally)
- Empty availability list `[]` now valid for list_tasks (returns 0 items)
- Defer hint warnings for `{after: "now"}` and `{before: "now"}` patterns
- Availability redundancy warnings for REMAINING overlap
- Cross-path equivalence tests (SQL = bridge for all date filter variants)
- Tool descriptions updated with date filter syntax guide

---

## Gap Analysis by Suite

### date-filtering.md (32 tests) — UP TO DATE

Created by previous seed chunks 1-2. Covers all 7 date dimensions, all 3 input forms, lifecycle auto-inclusion, defer hints, combos, inherited dates, edge cases.

**No changes needed.** The suite was written for correct behavior; the code has since been fixed to match (plans 47-03 through 47-06 closed the "soon" crash, "today" non-due crash, and lifecycle IS NULL OR gap).

One note: test count in reads-combined.md and SKILL.md says 17 — wrong, should be 32. Fixed in Chunk 2.

---

### list-tasks.md (47 tests) — NEEDS UPDATES

**Core issue:** Tests 2b-2d, 2f-2g, 5b use availability values (`completed`, `dropped`, `ALL`) that were removed from the list_tasks AvailabilityFilter in Phase 47. Test 8d expects `availability: []` to error, but it's now valid.

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| REMAINING | `availability: ["remaining"]` equals default | New enum member; prove it works |
| Empty availability | `availability: []` returns 0 items | New valid behavior; enables exclusive lifecycle queries |
| Exclusive lifecycle | `availability: [], completed: "all"` | Key new pattern: ONLY completed tasks, no remaining |
| Redundancy W-004 | `["available", "remaining"]` → warning | New warning not yet covered |
| Redundancy W-005 | `["blocked", "remaining"]` → warning | New warning not yet covered |

**Existing tests that need assertion updates / removal:**
- 2b (COMPLETED in availability) → remove; covered by date-filtering 2a
- 2c (DROPPED in availability) → remove; covered by date-filtering 2b
- 2d (all four states) → remove; covered by date-filtering 2a+2b
- 2f (ALL shorthand) → remove; ALL no longer valid
- 2g (ALL mixed) → remove; ALL no longer valid
- 5b (tag + COMPLETED combo) → rewrite using `completed: "all"` instead of availability
- 8d (availability: [] error) → convert to positive test in section 2

---

### validation-errors.md (27 tests) — NEEDS UPDATES

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| DateFilter: invalid this unit | `due: {this: "2w"}` | E-001 — new error type |
| DateFilter: zero count | `due: {next: "0d"}` | E-002 — new error type |
| DateFilter: invalid unit | `due: {last: "3x"}` | E-003 — new error type |
| DateFilter: after > before | Range ordering | E-005 — new error type |
| DateFilter: mixed groups | Shorthand + absolute | E-006 — new error type |
| DateFilter: empty | `due: {}` | E-008 — new error type |
| Breaking: availability "all" | `availability: ["all"]` | E-016 — removed value |
| Breaking: availability "completed" | `availability: ["completed"]` | Removed value |
| Breaking: completed boolean | `completed: true` | E-015 — boolean rejected |

**Existing tests that need assertion updates:**
- 3b: valid availability values changed (now available/blocked/remaining)
- 5d: `availability: []` no longer errors for list_tasks → remove

---

### list-projects.md (33 tests) — NO CHANGES NEEDED

The AvailabilityFilter trimming (COMPLETED/DROPPED/ALL removal) applies to `list_tasks` only. `list_projects` retains its own availability definitions because it has no date filter alternative for accessing completed/dropped projects. Tests 2b-2g remain valid.

---

### simple-list-tools.md (23 tests) — NO CHANGES NEEDED

Tags, folders, and perspectives use their own availability types with `dropped` and `ALL` still valid. Not affected by the list_tasks AvailabilityFilter changes.

---

### reads-combined.md — COUNT FIX ONLY

Date-filtering test count wrong: says 17, should be 32. List-tasks and validation-errors counts change after Chunks 1 and 2.

---

### Suites that DON'T need changes

| Suite | Why it's fine |
|-------|---------------|
| read-lookups.md | get_task/project/tag by ID — not affected by filter changes |
| task-creation.md | add_tasks — no availability or date filter involvement |
| edit-operations.md | Field editing — no availability filter changes |
| tag-operations.md | Tag add/remove/replace — not affected |
| move-operations.md | Move operations — not affected |
| lifecycle.md | Complete/drop operations — behavior unchanged |
| inheritance.md | Effective field inheritance — not affected by filter enum changes |
| integration-flows.md | Write-through tests use get_task/get_all, not list_tasks filters |
| repetition-rules.md | Repetition rule CRUD — not affected |
| writes-combined.md | Composite of write suites — none affected |

---

## Warning/Error Inventory

Every new warning/error from v1.3.2 that needs at least one UAT test:

### Errors

| ID | Text Pattern (from spec/planning docs) | Trigger | Covered By |
|----|-----------------------------------------|---------|------------|
| E-001 | "period unit '2w' for 'this' -- use one of: d, w, m, y" | `{this: "2w"}` — count+unit on `this` field | **Chunk 2** test 8a |
| E-002 | "Duration 'X' has zero or negative count" | `{next: "0d"}` or `{last: "-1w"}` | **Chunk 2** test 8b |
| E-003 | "Duration '3x' uses invalid unit 'x'. Valid units: d, w, m, y" | `{last: "3x"}` | **Chunk 2** test 8c |
| E-004 | Parsing error (invalid date) | `{before: "2026-13-01"}` | Low priority — standard Pydantic datetime parsing |
| E-005 | "'after' must be before or equal to 'before'" | `{after: "...", before: "..."}` where after > before | **Chunk 2** test 8d |
| E-006 | "Cannot mix shorthand and absolute date bounds" | `{this: "w", after: "..."}` | **Chunk 2** test 8e |
| E-007 | "Shorthand must have exactly one key" | `{this: "w", last: "3d"}` | Covered by E-006 conceptually (same validator); lower priority |
| E-008 | "DateFilter requires either shorthand or absolute bounds" | `due: {}` | **Chunk 2** test 8f |
| E-009–E-011 | Pydantic type union rejection | Wrong shortcut for field (e.g., `defer: "overdue"`) | Schema-level; not custom messages. Lower priority. |
| E-012 | Startup validation error for invalid OPERATOR_DUE_SOON_THRESHOLD | Invalid env var value | Config edge case — not UAT-testable without env var control |
| E-013 | "Cannot resolve 'soon': due-soon threshold not configured" | `due: "soon"` with no threshold available | Operational edge case — user always has OmniFocus running |
| E-014 | Generic Pydantic "Extra inputs not permitted" | `urgency: "overdue"` (field removed) | Lower priority — field never existed in public schema |
| E-015 | Generic Pydantic "Input should be..." | `completed: true` (boolean) | **Chunk 2** test 9c |
| E-016 | Generic Pydantic "Input should be 'available', 'blocked', or 'remaining'" | `availability: ["all"]` | **Chunk 2** test 9a |
| E-017 | Same as E-016 | `availability: ["any"]` | Covered by E-016 conceptually |

### Warnings

| ID | Text Pattern (from spec/planning docs) | Trigger | Covered By |
|----|-----------------------------------------|---------|------------|
| W-001 | "Due-soon threshold was not detected. Defaulting to today." | `due: "soon"` with threshold unavailable | Not UAT-testable (user has OmniFocus) |
| W-002 | "Tip: This shows tasks with a future defer date..." | `defer: {after: "now"}` | date-filtering test 7a |
| W-003 | "Tip: This shows tasks whose defer date has passed..." | `defer: {before: "now"}` | date-filtering test 7b |
| W-004 | "'remaining' already includes 'available'" | `availability: ["available", "remaining"]` | **Chunk 1** test 2i |
| W-005 | "'remaining' already includes 'blocked'" | `availability: ["blocked", "remaining"]` | **Chunk 1** test 2j |

---

## Summary of Work

| Suite | Action | New Tests | Assertion Fixes | Removals |
|-------|--------|-----------|-----------------|----------|
| list-tasks.md | Availability migration | 5 | 2 (rewrite 5b, convert 8d) | 5 |
| validation-errors.md | DateFilter + breaking change tests | 9 | 1 (update 3b) | 1 |
| reads-combined.md | Count fix | 0 | 3 (count corrections) | 0 |
| SKILL.md | Count fix | 0 | 4 (count corrections) | 0 |
| **Total** | | **~14** | **~10** | **~6** |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Run `/uat-suite-updater` one more time — it will enter Completion mode and archive this file
2. The worktree branch is now ready for the user to review and merge to main
