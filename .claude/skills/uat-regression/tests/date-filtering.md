# Date Filtering Test Suite

Tests `list_tasks` date filtering — due date shortcuts (overdue, soon, today), lifecycle date filters (completed, dropped with auto-inclusion), shorthand period syntax (this/last/next), absolute date bounds (before/after/range), combo filters (date + base filter AND logic), defer hint warnings (W022/W023), other date fields (modified, planned, defer, added), edge cases (no-date exclusion, round-trip), and inherited effective dates.

## Conventions

- **Search isolation.** Every test includes `search: "DF-"` to restrict results to test tasks only.
- **Read-only suite.** `list_tasks` is idempotent. No cleanup between tests — only after the suite completes.
- **Date sensitivity.** Tests depend on relative dates computed at setup time. If running after 10:30 PM local, tests 1b and 4a become unreliable — skip or reschedule. Test 7b assumes the suite runs after 06:00 local (DF-DeferToday's defer date must have passed).
- **Threshold-dependent.** Tests 1b and 4a depend on the user's OmniFocus "due soon" threshold, discovered during setup.

## Setup

### Step 1 — Due-Soon Threshold Discovery

Ask the user their OmniFocus due-soon threshold setting (Preferences > Dates & Times > "Due Soon means due within"). Recommend **Today** as the default — it's the OmniFocus factory default and the most common setting:

- **Today (calendar-aligned)** ← recommended default
- 24 hours (rolling)
- 2 days
- 3 days
- 4 days
- 5 days
- 1 week

Store the answer as **due-soon-threshold**.

### Step 2 — Late-Night Guard

Check the current local time. If after 10:30 PM:

> Due-soon tests are unreliable near midnight because date boundaries shift. Run these tests earlier in the day, or skip tests 1b and 4a for now.

If the user wants to proceed anyway, mark tests 1b and 4a as SKIP in the report.

### Step 3 — Compute Test Dates

Compute these ISO timestamps based on current time and the user's threshold:

| Reference | Formula | Purpose |
|-----------|---------|---------|
| `OVERDUE_DUE` | now - 2 hours | Past due date (overdue) |
| `SOON_DUE` | See strategy below | Within threshold, after now |
| `TODAY_DUE` | Today at 14:00 local (or now + 2h if past 14:00, cap at 23:00) | Due today, in the future |
| `FUTURE_DUE` | now + 30 days | Well beyond any threshold |
| `TODAY_DEFER` | Today at 06:00 local | Defer date clearly within today |
| `TOMORROW_DATE` | Tomorrow (date-only YYYY-MM-DD) | Absolute bound: captures today, excludes far future |
| `YESTERDAY_DATE` | Yesterday (date-only YYYY-MM-DD) | Absolute bound: everything from yesterday forward |
| `TODAY_DATE_STR` | Today (date-only YYYY-MM-DD) | Absolute bound and planned date reference |

**SOON_DUE strategy** (must be after now AND within threshold):
- **Today (calendar-aligned):** now + 1.5 hours (must be before midnight)
- **24 hours (rolling):** now + 12 hours
- **2+ days:** Tomorrow at 12:00 local

### Step 4 — Create Task Hierarchy

Create the inbox parent first:

```
UAT-DateFiltering (inbox parent)
```

Then create children in two batches:

**Batch A — Main tasks** (parent: UAT-DateFiltering):

```
+-- DF-Overdue          (dueDate: OVERDUE_DUE)
+-- DF-DueSoon          (dueDate: SOON_DUE)
+-- DF-DueToday         (dueDate: TODAY_DUE)
+-- DF-Future           (dueDate: FUTURE_DUE)
+-- DF-NoDue            (no dates — plain task)
+-- DF-Blocked          (deferDate: "2099-01-01T00:00:00Z" — far-future deferred)
+-- DF-Completed        (plain — will be completed in Step 5)
+-- DF-Dropped          (plain — will be dropped in Step 5)
+-- DF-DeferToday       (deferDate: TODAY_DEFER)
```

**Batch B — Inheritance chain** (parent: UAT-DateFiltering):

```
+-- DF-InheritParent    (dueDate: OVERDUE_DUE — same overdue date)
    +-- DF-InheritChild (no dates — inherits effectiveDueDate from parent)
```

Create DF-InheritParent first, then DF-InheritChild with parent set to DF-InheritParent's ID.

### Step 5 — Automated Setup Actions

1. `edit_tasks` on DF-Completed: `actions: { lifecycle: "complete" }`
2. `edit_tasks` on DF-Dropped: `actions: { lifecycle: "drop" }`
3. `edit_tasks` on DF-Overdue: `flagged: true`
4. `edit_tasks` on DF-DueToday: `flagged: true`
5. `edit_tasks` on DF-DueSoon: `plannedDate: "TODAY_DATE_STR"`

Verify via `get_task`:
- DF-Completed: `availability: "completed"`
- DF-Dropped: `availability: "dropped"`
- DF-InheritChild: `dueDate` is null, `effectiveDueDate` matches OVERDUE_DUE (inherited from DF-InheritParent)
- DF-Overdue: `flagged: true`
- DF-DueToday: `flagged: true`
- DF-DueSoon: `plannedDate` matches TODAY_DATE_STR

### Manual Actions

None — all setup is automated.

## Tests

> **Search isolation:** Every test includes `search: "DF-"` unless noted otherwise.

### 1. Due Date Shortcuts

#### Test 1a: due: "overdue"
1. `list_tasks` with `due: "overdue", search: "DF-"`
2. PASS if: DF-Overdue, DF-InheritParent, and DF-InheritChild all appear (all have overdue effective due dates); DF-Future does NOT appear; DF-NoDue does NOT appear; DF-DueSoon does NOT appear (its dueDate is after now); DF-DueToday does NOT appear (also after now)

#### Test 1b: due: "soon"
1. `list_tasks` with `due: "soon", search: "DF-"`
2. PASS if: DF-DueSoon appears (within threshold, after now); DF-Overdue ALSO appears (overdue is a subset of "soon" — "soon" means `effectiveDueDate < now + threshold`); DF-Future does NOT appear; DF-NoDue does NOT appear. DF-DueToday appears if its dueDate falls within the threshold (depends on setting — always true for 2+ day thresholds)

#### Test 1c: due: "today"
1. `list_tasks` with `due: "today", search: "DF-"`
2. PASS if: DF-DueToday appears; DF-Overdue appears (its dueDate is earlier today — still within midnight-to-midnight range); DF-Future does NOT appear; DF-NoDue does NOT appear. DF-DueSoon appears if SOON_DUE is also today (true for "today" threshold, false for 2+ day thresholds where SOON_DUE is tomorrow)

### 2. Lifecycle Filters

#### Test 2a: completed: "all"
1. `list_tasks` with `completed: "all", search: "DF-"`
2. PASS if: DF-Completed appears; DF-Dropped does NOT appear; all remaining (active + blocked) DF-* tasks also appear — `completed` filter auto-includes COMPLETED availability on top of default REMAINING

#### Test 2b: dropped: "all"
1. `list_tasks` with `dropped: "all", search: "DF-"`
2. PASS if: DF-Dropped appears; DF-Completed does NOT appear; all remaining DF-* tasks also appear

#### Test 2c: completed: "today"
1. `list_tasks` with `completed: "today", search: "DF-"`
2. PASS if: DF-Completed appears (completed during setup today); DF-Dropped does NOT appear; remaining DF-* tasks also appear (auto-inclusion still active)

#### Test 2d: completed: {last: "1w"}
1. `list_tasks` with `completed: {last: "1w"}, search: "DF-"`
2. PASS if: DF-Completed appears (completed today, within last 7 days); remaining DF-* tasks also appear

#### Test 2e: Lifecycle auto-inclusion — no explicit availability
1. Use results from test 2a (identical call: `completed: "all"` with default availability)
2. PASS if: DF-Completed appears despite `availability` not being explicitly set to include "completed" — the `completed` date filter automatically adds the COMPLETED availability state to whatever was specified (default REMAINING)

#### Test 2f: availability: ["available"] + completed: "all"
1. `list_tasks` with `availability: ["available"], completed: "all", search: "DF-"`
2. PASS if: DF-Completed appears (auto-included by lifecycle filter); DF-Blocked does NOT appear (only "available" requested, not "blocked"); DF-Dropped does NOT appear; available DF-* tasks appear normally

### 3. Shorthand Periods & Non-Due Fields

#### Test 3a: due: {this: "w"} — current calendar week
1. `list_tasks` with `due: {this: "w"}, search: "DF-"`
2. PASS if: DF-DueToday and DF-Overdue appear (both due this week); DF-DueSoon appears if SOON_DUE is this week (true for most thresholds); DF-Future does NOT appear (30 days out); DF-NoDue does NOT appear

#### Test 3b: due: {last: "3d"} — last 3 days
1. `list_tasks` with `due: {last: "3d"}, search: "DF-"`
2. PASS if: DF-Overdue appears (due 2h ago — within range [midnight 3 days ago, now]); DF-DueToday does NOT appear (its dueDate is after now, which is the upper bound of "last"); DF-Future does NOT appear; DF-NoDue does NOT appear

#### Test 3c: due: {next: "1w"} — rest of today + next 7 days
1. `list_tasks` with `due: {next: "1w"}, search: "DF-"`
2. PASS if: DF-DueSoon appears (after now, within next week); DF-DueToday appears (dueDate is after now but today); DF-Future does NOT appear (30 days out, beyond rest-of-today + 7 days); DF-Overdue does NOT appear (dueDate is before now, which is the lower bound of "next")

#### Test 3d: defer: "today"
1. `list_tasks` with `defer: "today", search: "DF-"`
2. PASS if: DF-DeferToday appears (deferDate is today); all other DF-* tasks do NOT appear (they either have no deferDate or deferDate in 2099)

#### Test 3e: added: "today"
1. `list_tasks` with `added: "today", search: "DF-"`
2. PASS if: all remaining (available + blocked) DF-* tasks appear (all were added today); DF-Completed and DF-Dropped do NOT appear (`added` is not a lifecycle field — no auto-inclusion)

### 4. Soon Includes Overdue & Inherited Dates

#### Test 4a: due: "soon" includes overdue tasks
1. `list_tasks` with `due: "soon", search: "DF-Overdue"`
2. PASS if: DF-Overdue appears — "soon" means `effectiveDueDate < now + threshold`, and since overdue tasks have `effectiveDueDate < now`, they satisfy `effectiveDueDate < now < now + threshold`

#### Test 4b: due: "overdue" on inherited effective date
1. `list_tasks` with `due: "overdue", search: "DF-InheritChild"`
2. PASS if: DF-InheritChild appears — it has no direct dueDate but inherits an overdue effectiveDueDate from DF-InheritParent. Date filters operate on effective (inherited) values.

#### Test 4c: Absolute filter on inherited date
1. `list_tasks` with `due: {before: "FUTURE_DUE_DATE"}, search: "DF-InheritChild"` (use the FUTURE_DUE date value from setup, formatted as date-only YYYY-MM-DD)
2. PASS if: DF-InheritChild appears — its inherited effectiveDueDate (overdue) is well before the given future date. Absolute date filters also work on inherited values.

### 5. Absolute Date Bounds

#### Test 5a: due: {before: "TOMORROW_DATE"}
1. `list_tasks` with `due: {before: "TOMORROW_DATE"}, search: "DF-"` (substitute the YYYY-MM-DD string computed in setup)
2. PASS if: DF-Overdue, DF-DueSoon, DF-DueToday, DF-InheritParent, DF-InheritChild all appear (all have due dates before the resolved upper bound — date-only `before` resolves to midnight of day-after-tomorrow); DF-Future does NOT appear (30 days out); DF-NoDue does NOT appear (no due date)

#### Test 5b: due: {after: "YESTERDAY_DATE"}
1. `list_tasks` with `due: {after: "YESTERDAY_DATE"}, search: "DF-"` (substitute the YYYY-MM-DD string computed in setup)
2. PASS if: DF-Overdue, DF-DueSoon, DF-DueToday, DF-Future, DF-InheritParent, DF-InheritChild all appear (all due dates are from today onward — after midnight yesterday, the resolved inclusive lower bound); DF-NoDue does NOT appear

#### Test 5c: due: {after: "now", before: "TOMORROW_DATE"} — range
1. `list_tasks` with `due: {after: "now", before: "TOMORROW_DATE"}, search: "DF-"`
2. PASS if: DF-DueSoon and DF-DueToday appear (due dates after now but before day-after-tomorrow midnight); DF-Overdue does NOT appear (due date is before now — outside inclusive lower bound); DF-Future does NOT appear (30 days out — outside upper bound); DF-InheritParent, DF-InheritChild do NOT appear (inherited overdue dates are before now); DF-NoDue does NOT appear

#### Test 5d: due: {before: "now"} — equivalent to overdue
1. `list_tasks` with `due: {before: "now"}, search: "DF-"`
2. PASS if: same result set as test 1a — DF-Overdue, DF-InheritParent, DF-InheritChild appear; all others excluded. `{before: "now"}` resolves to the same boundary as the "overdue" shortcut.

#### Test 5e: due: {after: "now"} — future only
1. `list_tasks` with `due: {after: "now"}, search: "DF-"`
2. PASS if: DF-DueSoon, DF-DueToday, DF-Future appear (all have due dates after now); DF-Overdue does NOT appear (due before now); DF-InheritParent, DF-InheritChild do NOT appear (inherited overdue = before now); DF-NoDue does NOT appear

### 6. Combo Filters (Date + Base)

#### Test 6a: due: "overdue" + flagged: true
1. `list_tasks` with `due: "overdue", flagged: true, search: "DF-"`
2. PASS if: DF-Overdue appears (overdue AND flagged); DF-InheritParent, DF-InheritChild do NOT appear (overdue but not flagged); DF-DueToday does NOT appear (flagged but not overdue). Proves AND logic between date filter and base filter.

#### Test 6b: completed: "all" + narrowed search
1. `list_tasks` with `completed: "all", search: "DF-Completed"`
2. PASS if: DF-Completed appears (lifecycle auto-inclusion makes completed tasks visible + search narrows to this one task); no other tasks appear

#### Test 6c: due: "today" + flagged: true
1. `list_tasks` with `due: "today", flagged: true, search: "DF-"`
2. PASS if: DF-Overdue and DF-DueToday both appear (both are due today AND flagged); DF-DueSoon does NOT appear (not flagged even if due today); DF-InheritParent, DF-InheritChild do NOT appear (not flagged)

#### Test 6d: Multi-dimension — defer + due (AND produces empty)
1. `list_tasks` with `defer: {before: "now"}, due: {before: "now"}, search: "DF-"`
2. PASS if: `items` array is empty and `total` is 0 — DF-DeferToday has defer before now but no due date (excluded by due filter); overdue tasks (DF-Overdue, DF-InheritParent, DF-InheritChild) have due before now but no defer date (excluded by defer filter). No single task satisfies both conditions. Warning W023 may be present (defer hint for `defer: {before: "now"}`). This proves AND logic across two date filter dimensions.

### 7. Defer Hint Warnings

#### Test 7a: defer: {after: "now"} — W022 hint
1. `list_tasks` with `defer: {after: "now"}, search: "DF-"`
2. PASS if: DF-Blocked appears (deferDate 2099 is after now); response warnings array includes text containing "Tip: This shows tasks with a future defer date. For all unavailable tasks regardless of reason, use availability: 'blocked'."

#### Test 7b: defer: {before: "now"} — W023 hint
1. `list_tasks` with `defer: {before: "now"}, search: "DF-"`
2. PASS if: DF-DeferToday appears (deferDate at 06:00 today has passed — assumes test runs after 06:00 local); response warnings array includes text containing "Tip: This shows tasks whose defer date has passed. For all currently available tasks, use availability: 'available'."

### 8. Other Date Fields

#### Test 8a: modified: {last: "1w"}
1. `list_tasks` with `modified: {last: "1w"}, search: "DF-"`
2. PASS if: all remaining (available + blocked) DF-* tasks appear (all created/modified today, well within 1 week); DF-Completed and DF-Dropped do NOT appear (`modified` is not a lifecycle field — no auto-inclusion of completed/dropped availability)

#### Test 8b: planned: "today"
1. `list_tasks` with `planned: "today", search: "DF-"`
2. PASS if: DF-DueSoon appears (plannedDate set to TODAY_DATE_STR during setup); no other DF-* tasks appear (only DF-DueSoon has a planned date set)

### 9. Edge Cases

#### Test 9a: due: "overdue" on task with no dueDate
1. `list_tasks` with `due: "overdue", search: "DF-NoDue"`
2. PASS if: `items` array is empty — DF-NoDue has no due date and is not treated as overdue. Tasks without the filtered date field are excluded, not matched.

#### Test 9b: Round-trip — filter result vs get_task
1. Call `list_tasks` with `due: "overdue", search: "DF-Overdue"` and note the returned task's ID and `dueDate`
2. Call `get_task` with that task ID
3. PASS if: both responses show the same `dueDate` value; the value matches the OVERDUE_DUE timestamp set during setup (dates survive the round-trip through date filtering and individual lookup)

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Due: overdue | Overdue tasks returned; no-due and future excluded; inherited overdue included | |
| 1b | Due: soon | Tasks within threshold returned; overdue included (soon ⊃ overdue); future excluded | |
| 1c | Due: today | Tasks due today returned; future and no-due excluded | |
| 2a | Lifecycle: completed all | All completed tasks appear alongside active; dropped excluded | |
| 2b | Lifecycle: dropped all | All dropped tasks appear alongside active; completed excluded | |
| 2c | Lifecycle: completed today | Only today's completions; auto-includes completed availability | |
| 2d | Lifecycle: completed {last: 1w} | DateFilter on lifecycle field; today's completion within 1w range | |
| 2e | Lifecycle: auto-inclusion | completed filter adds COMPLETED to availability without explicit setting | |
| 2f | Lifecycle: available + completed | Explicit available-only + lifecycle auto-include; blocked excluded | |
| 3a | Shorthand: this week | Calendar week; today's tasks included, 30-day future excluded | |
| 3b | Shorthand: last 3 days | Rolling past [midnight-3d, now]; overdue included, future-today excluded | |
| 3c | Shorthand: next week | Rolling future [now, midnight+8d]; near-future included, 30-day excluded | |
| 3d | Non-due: defer today | Tasks with today's defer date only; others excluded | |
| 3e | Non-due: added today | All today's tasks returned; no lifecycle auto-include for `added` | |
| 4a | Soon ⊃ overdue | Overdue task explicitly found in "soon" results | |
| 4b | Inherited: overdue | No direct dueDate; found by overdue filter via inherited effective date | |
| 4c | Inherited: absolute | Inherited effective date caught by absolute {before} filter | |
| 5a | Absolute: before tomorrow | Near-term tasks returned; 30-day future excluded; no-due excluded | |
| 5b | Absolute: after yesterday | All dated tasks returned; no-due excluded | |
| 5c | Absolute: range [now, tomorrow] | Future-today window; overdue and far-future both excluded | |
| 5d | Absolute: before now = overdue | Equivalent result to "overdue" shortcut (test 1a) | |
| 5e | Absolute: after now = future | Only future due dates; overdue and no-due excluded | |
| 6a | Combo: overdue + flagged | AND logic; only flagged overdue task appears | |
| 6b | Combo: completed + search | Lifecycle auto-inclusion + narrow search; single task returned | |
| 6c | Combo: today + flagged | AND logic; flagged due-today tasks only | |
| 6d | Combo: multi-dim defer + due | Both date dimensions AND'd; empty result proves intersection logic | |
| 7a | Defer hint: after now | W022 tip about availability: 'blocked' alternative | |
| 7b | Defer hint: before now | W023 tip about availability: 'available' alternative | |
| 8a | Other: modified last week | All remaining tasks returned; no lifecycle auto-include for modified | |
| 8b | Other: planned today | Only task with planned date today returned | |
| 9a | Edge: no due date | Task without dueDate excluded from overdue filter | |
| 9b | Edge: round-trip | dueDate consistent between list_tasks filter and get_task lookup | |
