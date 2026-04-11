# UAT Suite Analysis — v1.3.2 "Date Filtering"

## How to Use This File

This file is the output of a research session that analyzed what v1.3.2 changed vs what existing UAT suites cover. It contains everything a fresh agent needs to update the suites without re-doing the research.

**Workflow:** Run `/uat-suite-updater` in a new session. The skill auto-detects this file and enters Worker mode — it will find the next unchecked chunk, do targeted research, execute the changes, and mark the chunk done.

**Important:** The agent still needs to do its own targeted research for the specific suites it's updating — the gap tables below are a starting point, not exhaustive. The agent should verify against planning docs, especially for exact warning/error strings.

---

## Progress

- [ ] Chunk 1 — Naive datetime contract + validation fixes
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

### Chunk 1: Naive datetime contract + validation fixes

**Suites:** validation-errors.md, task-creation.md, edit-operations.md, date-filtering.md

**What to do:**

#### validation-errors.md

1. **Fix Test 1b** (lines 41-42): Currently expects `dueDate: "2026-03-15"` (date-only) to ERROR. Per LOCAL-01/02/03 (Phase 49), date-only is now VALID and gets enriched with user's default time. Change the test to use an actually invalid format:
   - Old: `dueDate: "2026-03-15"` → expects error
   - New: `dueDate: "March 15, 2026"` or `dueDate: "2026/03/15"` → expects error about invalid date format
   - Update description and PASS criteria to reflect testing an invalid format, not date-only

2. **Verify Test 8e** (lines 184-186): Mixed shorthand+absolute `{this: "w", after: "..."}`. With the Phase 48 discriminated union:
   - Input with multiple keys routes to one model via callable Discriminator
   - The extra key is rejected by Pydantic's `extra="forbid"` on the concrete model
   - Verify the error message still matches the PASS criteria or update text as needed

3. **Verify Test 8f** (lines 188-190): Empty `{}` filter. Phase 49 updated the error text to mention naive datetime acceptance. Verify PASS criteria matches actual error text or update.

#### task-creation.md

4. **Add Test: Naive datetime acceptance** (after existing date tests, around line 100):
   - `add_tasks` with `items: [{ name: "TC-NaiveDT", dueDate: "2026-07-15T17:00:00" }]` (no Z, no offset)
   - PASS if: task created successfully; no error; `dueDate` in response matches input

5. **Add Test: Date-only enrichment with default time** (PREF-04):
   - `add_tasks` with `items: [{ name: "TC-DateOnly", dueDate: "2026-07-15" }]`
   - PASS if: task created; `dueDate` in response is NOT midnight but user's configured DefaultDueTime (typically 17:00 or 5:00 PM)
   - Note: User's DefaultDueTime may vary — test should verify time is NOT `T00:00:00`, proving enrichment happened

#### edit-operations.md

6. **Add Test: Naive datetime on edit** (after existing date tests):
   - `edit_tasks` with naive datetime `dueDate: "2026-07-15T14:00:00"` (no Z)
   - PASS if: edit succeeds; no error; updated `dueDate` matches input

#### date-filtering.md

7. **Add Test 7c: Defer hint on shorthand form** (after Test 7b, around line 212):
   - `list_tasks` with `defer: {last: "1w"}, search: "DF-"`
   - PASS if: DF-DeferToday appears (its deferDate at 06:00 today is within last week range); response warnings array includes defer hint text (BREAK-05: past range → suggests `availability: "available"`)

8. **Add Test 7d: Defer hint on absolute non-now form** (after Test 7c):
   - Create a far-future range: `defer: {after: "2090-01-01", before: "2099-12-31"}, search: "DF-"`
   - PASS if: DF-Blocked appears (deferDate 2099 is within this range); response warnings array includes defer hint text (BREAK-04: future range → suggests `availability: "blocked"`)

**Est. scope:** ~3 assertion fixes + ~5 new tests = 8 items total

---

## Reference Material

Everything below is research output — the chunks above reference it.

---

## What v1.3.2 Built

v1.3.2 "Date Filtering" shipped 6 phases (45-50) delivering:

### Theme 1: Date Filter Capabilities
- 7 new date filter fields on `list_tasks`: `due`, `defer`, `planned`, `completed`, `dropped`, `added`, `modified`
- String shortcuts: `"overdue"`, `"soon"`, `"today"` (due-specific); `"all"`, `"today"` (lifecycle)
- DateFilter object forms: `{this: "d"}`, `{last: "3d"}`, `{next: "1w"}`, `{before/after: "..."}`, `"now"`
- Field-specific shortcut restrictions enforced at contract layer

### Theme 2: Lifecycle Auto-Inclusion
- `completed`/`dropped` date filters automatically include those lifecycle states in results
- `completed: "all"` → all completed tasks regardless of date
- `availability: [], completed: "all"` → exclusively lifecycle results (no remaining tasks)

### Theme 3: Breaking Changes
- `COMPLETED`/`DROPPED` removed from AvailabilityFilter enum → use date filters instead
- `ALL` renamed to `REMAINING` (available + blocked)
- `availability: "all"/"any"` → generic Pydantic rejection (pre-release, no custom message)
- `completed: true` (boolean) → generic Pydantic rejection
- `urgency` filter → generic Pydantic rejection

### Theme 4: Discriminated Union (Phase 48)
- DateFilter refactored from flat 5-field model to 4-model discriminated union:
  - `ThisPeriodFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `AbsoluteRangeFilter`
- Callable Discriminator routes by key presence
- Empty `{}` routes to AbsoluteRangeFilter which rejects it with educational error
- Mixed keys (e.g., `{this: "w", after: "..."}`) route to one model, extra key rejected via `extra="forbid"`

### Theme 5: Naive-Local DateTime Contract (Phase 49)
- Write-side date fields and filter bounds use `str` type (no `format: "date-time"` in JSON Schema)
- **Naive datetime is the preferred format** — `"2026-07-15T17:00:00"` (no Z)
- Aware datetime accepted, silently converted to naive local
- Date-only accepted on write side (enriched with default time per Phase 50)
- All `now` timestamps use local timezone

### Theme 6: OmniFocus Settings Integration (Phase 50)
- New `get_settings` bridge command reads OmniFocus preferences via OmniJS
- Date-only write inputs enriched with user's configured default time:
  - `dueDate` → `DefaultDueTime` (factory default: 17:00)
  - `deferDate` → `DefaultStartTime` (factory default: 00:00)
  - `plannedDate` → `DefaultPlannedTime` (factory default: 09:00)
- DueSoon threshold sourced from OmniFocus preferences (not SQLite plist, not env var)
- Fallback to factory defaults + warning when OmniFocus unavailable

---

## Gap Analysis by Suite

### validation-errors.md (35 tests) — NEEDS UPDATES

**Existing v1.3.2 coverage:**
- Section 8 (Tests 8a-8f): DateFilter validation errors ✓
- Section 9 (Tests 9a-9c): Breaking change rejections ✓

**Assertion fixes needed:**

| Test | Issue | Fix |
|------|-------|-----|
| 1b | Expects date-only `"2026-03-15"` to error — but Phase 49 made date-only VALID | Change to actually invalid format like `"March 15, 2026"` |
| 8e | Mixed shorthand+absolute error — discriminated union may produce different error text | Verify error message matches, update PASS criteria if needed |
| 8f | Empty `{}` error — Phase 49 updated message text | Verify error message matches, update PASS criteria if needed |

**No new tests needed** — existing sections 8 and 9 cover the error surface adequately.

---

### task-creation.md (17 tests) — NEEDS UPDATES

**Current state:** Uses timezone-aware dates throughout (e.g., `"2026-03-15T17:00:00Z"`)

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| LOCAL-02 | Naive datetime acceptance | Verify `dueDate: "2026-07-15T17:00:00"` (no Z) creates task successfully |
| PREF-04 | Date-only enrichment | Verify `dueDate: "2026-07-15"` gets enriched with DefaultDueTime, not midnight |

---

### edit-operations.md (23 tests) — NEEDS UPDATES

**Current state:** Uses timezone-aware dates throughout

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| LOCAL-02 | Naive datetime on edit | Verify `dueDate: "2026-07-15T14:00:00"` (no Z) works on edit_tasks |

---

### date-filtering.md (35 tests) — NEEDS UPDATES

**Current v1.3.2 coverage:**
- Tests 7a, 7b: Defer hints for `{after: "now"}` and `{before: "now"}` ✓
- All other date filter forms already tested

**New scenarios needed:**

| Category | Test | Why |
|----------|------|-----|
| BREAK-04/05 | Defer hint on shorthand | `defer: {last: "1w"}` should produce W023 hint (past range) |
| BREAK-04/05 | Defer hint on absolute non-now | Far-future absolute range should produce W022 hint |

---

### Suites that DON'T need changes

| Suite | Why it's fine |
|-------|---------------|
| list-tasks.md | Tests 2g-2j already cover availability `[]`, redundancy warnings, lifecycle auto-inclusion |
| list-projects.md | No date filter features |
| simple-list-tools.md | No date filter features |
| read-lookups.md | No date filter features |
| move-operations.md | No date changes |
| lifecycle.md | No date filter changes |
| inheritance.md | Effective date inheritance already tested in date-filtering.md tests 4b, 4c |
| tag-operations.md | No date changes |
| repetition-rules.md | No date changes |
| integration-flows.md | No date changes |
| reads-combined.md | Composite — covers constituent suites |
| writes-combined.md | Composite — covers constituent suites |

---

## Warning/Error Inventory

Every new warning/error from v1.3.2 that needs at least one UAT test:

### Errors (Final Active Set)

| ID | Text Pattern | Covered By |
|----|-------------|------------|
| DATE_FILTER_INVALID_DURATION | `"Invalid duration '{value}' -- use a number followed by d/w/m/y..."` | validation-errors 8c |
| DATE_FILTER_ZERO_NEGATIVE | `"Duration count must be positive (got '{value}')..."` | validation-errors 8b |
| DATE_FILTER_REVERSED_BOUNDS | `"Invalid date range: 'after' ({after}) is later than 'before' ({before})..."` | validation-errors 8d |
| ABSOLUTE_RANGE_FILTER_EMPTY | `"AbsoluteRangeFilter requires at least one of: before or after..."` | validation-errors 8f |
| _validate_date_string (inline) | `"Invalid date format '{v}'. Expected ISO date ('2026-07-15'), ISO datetime ('2026-07-15T17:00:00'), or datetime with timezone..."` | validation-errors 1b (after fix) |
| this unit error | `"'this' only accepts single calendar units (d, w, m, y)..."` | validation-errors 8a |
| Breaking: availability enum | Generic Pydantic rejection for `"all"`, `"any"`, `"completed"`, `"dropped"` | validation-errors 9a, 9b |
| Breaking: boolean completed | Generic Pydantic rejection for `completed: true` | validation-errors 9c |

### Warnings (Final Active Set)

| ID | Text Pattern | Covered By |
|----|-------------|------------|
| DEFER_AFTER_NOW_HINT (W022) | `"Tip: This shows tasks with a future defer date. For all unavailable tasks regardless of reason, use availability: 'blocked'..."` | date-filtering 7a, 7d (to add) |
| DEFER_BEFORE_NOW_HINT (W023) | `"Tip: This shows tasks whose defer date has passed. For all currently available tasks, use availability: 'available'..."` | date-filtering 7b, 7c (to add) |
| AVAILABILITY_REMAINING_INCLUDES_AVAILABLE | `"'remaining' already includes 'available'..."` | list-tasks 2i |
| AVAILABILITY_REMAINING_INCLUDES_BLOCKED | `"'remaining' already includes 'blocked'..."` | list-tasks 2j |
| SETTINGS_FALLBACK_WARNING | `"Could not read OmniFocus preferences (app may not be running)..."` | **Not UAT-able** — requires OmniFocus to be unavailable |
| SETTINGS_UNKNOWN_DUE_SOON_PAIR | `"OmniFocus due-soon preference has an unrecognized value..."` | **Not UAT-able** — edge case |
| DUE_SOON_THRESHOLD_NOT_DETECTED | `"Due-soon threshold was not detected from OmniFocus preferences..."` | **Not UAT-able** — requires OmniFocus unavailable |

---

## Summary of Work

| Suite | Action | New Tests | Assertion Fixes |
|-------|--------|-----------|-----------------|
| validation-errors.md | Fix Test 1b, verify 8e/8f | 0 | 3 |
| task-creation.md | Add naive datetime + date-only enrichment tests | 2 | 0 |
| edit-operations.md | Add naive datetime test | 1 | 0 |
| date-filtering.md | Add defer hint tests for other filter forms | 2 | 0 |
| **Total** | | **~5** | **~3** |

---

## Final Cleanup

Once ALL chunks are complete and committed, and the user has validated everything:

1. Run `/uat-suite-updater` one more time — it will enter Completion mode and archive this file
2. The worktree branch is now ready for the user to review and merge to main
