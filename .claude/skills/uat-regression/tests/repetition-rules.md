# Repetition Rules Test Suite

Tests repetition rule creation, read model, editing (set/clear/partial update/type change), no-op detection, status warnings, lifecycle interactions, normalization, validation errors, and combo scenarios for `add_tasks` and `edit_tasks`.

## Conventions

- **Inbox only.** Never create tasks in projects. Every task goes to inbox (no `parent` for top-level, or under the test parent task).
- **Timezone required.** Date fields need timezone info in ISO 8601 (e.g., `+01:00` or `Z`). Without it, Pydantic rejects the value.
- **1-item limit.** `edit_tasks` currently accepts exactly 1 item per call.
- **Due date for lifecycle tests.** Tasks used in lifecycle tests (7a, 7b) need a `dueDate` set before the lifecycle action — a repeating task without its anchor date won't produce the next occurrence.

## Setup

### Task Hierarchy

Create this structure in the inbox using `add_tasks`:

```
UAT-RepetitionRule (parent)
+-- T1-SetRule
+-- T2-ClearRule
+-- T3-Partial
+-- T4-TypeChange
+-- T5-NoOp
+-- T6-StatusComplete
+-- T7-StatusDrop
+-- T8-Lifecycle
+-- T9-LifecycleDrop
+-- T10-Errors
+-- T11-Normalize
+-- T12-EndPast
+-- T13-Combos
```

Create the parent first, then all children (can be parallel). Store all IDs.

### Automated Setup Actions

After creating all tasks, run these lifecycle actions:
1. `edit_tasks` on T6-StatusComplete: `actions: { lifecycle: "complete" }`
2. `edit_tasks` on T7-StatusDrop: `actions: { lifecycle: "drop" }`

Verify T6 shows `availability: "completed"` and T7 shows `availability: "dropped"` via `get_task`.

Then tell the user: "Setup complete. Running all tests now. I'll report results when done."

## Tests

### 1. Creation via add_tasks

These tests create NEW tasks (under UAT-RepetitionRule parent) with repetition rules and verify the round-trip via `get_task`.

#### Test 1a: Daily with interval — basic round-trip
1. `add_tasks` with name "R1a-Daily", parent=UAT-RepetitionRule, `dueDate: "2026-06-01T12:00:00Z"`, `repetitionRule: { frequency: { type: "daily", interval: 3 }, schedule: "regularly", basedOn: "due_date" }`
2. `get_task` on the created task
3. PASS if: `repetitionRule.frequency.type` is `"daily"`, `frequency.interval` is `3`, `schedule` is `"regularly"`, `basedOn` is `"due_date"`, `end` is `null`, and response does NOT contain a `ruleString` field

#### Test 1b: Weekly on days — case normalization + catch-up + end by occurrences
1. `add_tasks` with name "R1b-WeeklyDays", parent=UAT-RepetitionRule, `dueDate: "2026-06-01T12:00:00Z"`, `repetitionRule: { frequency: { type: "weekly_on_days", onDays: ["mo", "we", "fr"] }, schedule: "regularly_with_catch_up", basedOn: "due_date", end: { occurrences: 5 } }`
2. `get_task` on the created task
3. PASS if: `frequency.type` is `"weekly_on_days"`, `frequency.onDays` is `["MO", "WE", "FR"]` (uppercase), `schedule` is `"regularly_with_catch_up"`, `end.occurrences` is `5`

#### Test 1c: Monthly day of week — from_completion + end by date
1. `add_tasks` with name "R1c-MonthlyDoW", parent=UAT-RepetitionRule, `dueDate: "2026-06-01T12:00:00Z"`, `repetitionRule: { frequency: { type: "monthly_day_of_week", on: { "second": "tuesday" } }, schedule: "from_completion", basedOn: "due_date", end: { date: "2026-12-31T00:00:00Z" } }`
2. `get_task` on the created task
3. PASS if: `frequency.type` is `"monthly_day_of_week"`, `frequency.on` is `{ "second": "tuesday" }`, `schedule` is `"from_completion"`, `end.date` is present

#### Test 1d: Monthly day in month — defer_date basedOn
1. `add_tasks` with name "R1d-MonthlyDiM", parent=UAT-RepetitionRule, `deferDate: "2026-06-01T12:00:00Z"`, `repetitionRule: { frequency: { type: "monthly_day_in_month", onDates: [1, 15, -1] }, schedule: "regularly", basedOn: "defer_date" }`
2. `get_task` on the created task
3. PASS if: `frequency.type` is `"monthly_day_in_month"`, `frequency.onDates` contains `1`, `15`, `-1`, `basedOn` is `"defer_date"`

#### Test 1e: Yearly — planned_date basedOn
1. `add_tasks` with name "R1e-Yearly", parent=UAT-RepetitionRule, `dueDate: "2026-06-01T12:00:00Z"`, `repetitionRule: { frequency: { type: "yearly" }, schedule: "regularly", basedOn: "planned_date" }`
2. `get_task` on the created task
3. PASS if: `frequency.type` is `"yearly"`, `frequency.interval` is `1` (default), `basedOn` is `"planned_date"`

### 2. Edit — Set & Clear

#### Test 2a: Set rule on non-repeating task
1. Edit T1-SetRule: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`, `dueDate: "2026-06-15T12:00:00Z"`
2. `get_task` T1 to verify `repetitionRule` is present with correct fields
3. PASS if: success, `repetitionRule.frequency.type` is `"daily"`, `schedule` and `basedOn` present

#### Test 2b: Clear rule
1. Edit T2-ClearRule: `repetitionRule: { frequency: { type: "weekly" }, schedule: "regularly", basedOn: "due_date" }`, `dueDate: "2026-06-15T12:00:00Z"`
2. Verify rule is set via `get_task`
3. Edit T2: `repetitionRule: null`
4. `get_task` T2
5. PASS if: `repetitionRule` is `null` in the response

### 3. Partial Updates

First, set up T3-Partial with a rule: `repetitionRule: { frequency: { type: "weekly_on_days", onDays: ["MO", "WE"], interval: 2 }, schedule: "regularly", basedOn: "due_date", end: { occurrences: 10 } }`, `dueDate: "2026-06-15T12:00:00Z"`

Then run each test sequentially (each builds on the previous state):

#### Test 3a: Schedule only change
1. Edit T3: `repetitionRule: { schedule: "from_completion" }`
2. `get_task` T3
3. PASS if: `schedule` is `"from_completion"`, `frequency` still `weekly_on_days` with `onDays: ["MO", "WE"]` and `interval: 2`, `basedOn` still `"due_date"`, `end.occurrences` still `10`

#### Test 3b: BasedOn only change
1. Edit T3: `repetitionRule: { basedOn: "defer_date" }`
2. `get_task` T3
3. PASS if: `basedOn` is `"defer_date"`, all other fields preserved from 3a

#### Test 3c: Interval + onDays update (same type)
Note: `weekly_on_days` requires `onDays` at the Pydantic level, so you can't omit it even for a partial update. This test verifies you can change interval while re-specifying the existing onDays.
1. Edit T3: `repetitionRule: { frequency: { type: "weekly_on_days", onDays: ["MO", "WE"], interval: 4 } }`
2. `get_task` T3
3. PASS if: `frequency.interval` is `4`, `frequency.onDays` still `["MO", "WE"]`

#### Test 3d: onDays change (same-type merge — interval preserved)
1. Edit T3: `repetitionRule: { frequency: { type: "weekly_on_days", onDays: ["TU", "TH"] } }`
2. `get_task` T3
3. PASS if: `frequency.onDays` is `["TU", "TH"]`, `frequency.interval` still `4` (preserved from 3c)

#### Test 3e: Add end condition
1. First clear end: Edit T3 `repetitionRule: { end: null }`
2. Verify end is gone via `get_task`
3. Edit T3: `repetitionRule: { end: { date: "2027-01-01T00:00:00Z" } }`
4. `get_task` T3
5. PASS if: `end.date` is present, frequency/schedule/basedOn preserved

#### Test 3f: Change end type (date to occurrences)
1. Edit T3: `repetitionRule: { end: { occurrences: 3 } }`
2. `get_task` T3
3. PASS if: `end.occurrences` is `3`, no `end.date` field

#### Test 3g: Clear end
1. Edit T3: `repetitionRule: { end: null }`
2. `get_task` T3
3. PASS if: `end` is `null`, frequency/schedule/basedOn preserved

### 4. Type Change

#### Test 4a: Daily to weekly_on_days (full replacement)
1. Edit T4-TypeChange: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`, `dueDate: "2026-06-15T12:00:00Z"`
2. Edit T4: `repetitionRule: { frequency: { type: "weekly_on_days", onDays: ["MO", "FR"], interval: 2 } }`
3. `get_task` T4
4. PASS if: `frequency.type` is `"weekly_on_days"`, `onDays` is `["MO", "FR"]`, `interval` is `2`

### 5. No-Op Detection

First, set up T5-NoOp with a rule: `repetitionRule: { frequency: { type: "daily", interval: 2 }, schedule: "regularly", basedOn: "due_date" }`, `dueDate: "2026-06-15T12:00:00Z"`

#### Test 5a: Identical rule — no-op
1. Edit T5 with the exact same rule: `repetitionRule: { frequency: { type: "daily", interval: 2 }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: success with warning containing "identical to the existing one"

#### Test 5b: Omitted repetitionRule + field edit
1. Edit T5 with only `flagged: true` (no `repetitionRule` field at all)
2. PASS if: success, no repetition-related warning, flagged change applied

### 6. Status Warnings

#### Test 6a: Set rule on completed task
1. Edit T6-StatusComplete: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: success with warning mentioning "completed"

#### Test 6b: Set rule on dropped task
1. Edit T7-StatusDrop: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: success with warning mentioning "dropped"

### 7. Lifecycle x Repetition

#### Test 7a: Complete a repeating task
1. Edit T8-Lifecycle: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`, `dueDate: "2026-06-15T12:00:00Z"`
2. Edit T8: `actions: { lifecycle: "complete" }`
3. PASS if: warning containing "next occurrence created"

#### Test 7b: Drop a repeating task
1. Edit T9-LifecycleDrop: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`, `dueDate: "2026-06-15T12:00:00Z"`
2. Edit T9: `actions: { lifecycle: "drop" }`
3. PASS if: warning containing "occurrence was skipped"

### 8. Normalization & Warnings

#### Test 8a: Empty onDates normalized to monthly
1. `add_tasks` with name "R8a-EmptyOnDates", parent=UAT-RepetitionRule, `dueDate: "2026-06-01T12:00:00Z"`, `repetitionRule: { frequency: { type: "monthly_day_in_month", onDates: [] }, schedule: "regularly", basedOn: "due_date" }`
2. Check response for warning containing "equivalent to plain 'monthly'"
3. `get_task` on created task
4. PASS if: warning present AND `frequency.type` is `"monthly"` (normalized)

#### Test 8b: End date in the past
1. Edit T12-EndPast: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date", end: { date: "2020-01-01T00:00:00Z" } }`, `dueDate: "2026-06-15T12:00:00Z"`
2. PASS if: success with warning containing "end date" and "in the past"

#### Test 8c: Rule without anchor date (common agent mistake)
1. `add_tasks` with name "R8c-NoAnchor", parent=UAT-RepetitionRule, `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }` — NO `dueDate` set
2. PASS if: either a warning about missing anchor date OR silent success (document whichever behavior occurs — this tests what agents will actually encounter)

### 9. Validation Errors

Run each INDIVIDUALLY (they will error):

#### Test 9a: Invalid interval
1. `edit_tasks` on T10-Errors: `repetitionRule: { frequency: { type: "daily", interval: 0 }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: error containing "Interval must be >= 1"

#### Test 9b: Invalid day code
1. `edit_tasks` on T10: `repetitionRule: { frequency: { type: "weekly_on_days", onDays: ["XX"] }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: error containing "Invalid day code"

#### Test 9c: Invalid ordinal
1. `edit_tasks` on T10: `repetitionRule: { frequency: { type: "monthly_day_of_week", on: { "sixth": "tuesday" } }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: error containing "Invalid ordinal"

#### Test 9d: Invalid day name
1. `edit_tasks` on T10: `repetitionRule: { frequency: { type: "monthly_day_of_week", on: { "second": "funday" } }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: error containing "Invalid day name"

#### Test 9e: Invalid onDate
1. `edit_tasks` on T10: `repetitionRule: { frequency: { type: "monthly_day_in_month", onDates: [0] }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: error containing "Invalid date value"

#### Test 9f: Invalid end occurrences
1. `edit_tasks` on T10: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date", end: { occurrences: 0 } }`
2. PASS if: error containing "End occurrences must be >= 1"

#### Test 9g: Partial update on non-repeating task
1. `edit_tasks` on T10 (has no rule): `repetitionRule: { schedule: "from_completion" }`
2. PASS if: error containing "no existing rule"

### 10. Clean Error Format

Run INDIVIDUALLY:

#### Test 10a: Structurally invalid frequency
1. `edit_tasks` on T10: `repetitionRule: { frequency: { interval: 2 }, schedule: "regularly", basedOn: "due_date" }`
2. PASS if: error does NOT contain "type=", "pydantic", or "input_value"

#### Test 10b: Empty end object
1. `edit_tasks` on T10: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date", end: {} }`
2. PASS if: clean error (no pydantic internals leaked)

### 11. Combos

#### Test 11a: Set rule + field edit in same call
1. Edit T13-Combos: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`, `flagged: true`, `dueDate: "2026-06-15T12:00:00Z"`
2. `get_task` T13 to verify both rule and flagged
3. PASS if: `repetitionRule` present AND `effectiveFlagged: true`

#### Test 11b: No-op repetition + name change
1. Edit T13 with same rule: `repetitionRule: { frequency: { type: "daily" }, schedule: "regularly", basedOn: "due_date" }`, `name: "T13-CombosRenamed"`
2. `get_task` T13
3. PASS if: warning containing "identical to the existing one" AND name is `"T13-CombosRenamed"`

## Report Table Rows

| # | Test | Description | Result |
|---|------|-------------|--------|
| 1a | Create: daily + interval | Daily freq, interval=3, regularly, due_date; verify structured round-trip, no ruleString | |
| 1b | Create: weekly_on_days | onDays case-normalized to uppercase; regularly_with_catch_up; end by occurrences | |
| 1c | Create: monthly_day_of_week | on={"second":"tuesday"}; from_completion; end by date | |
| 1d | Create: monthly_day_in_month | onDates=[1,15,-1]; defer_date basedOn | |
| 1e | Create: yearly | Yearly freq; planned_date basedOn | |
| 2a | Edit: set rule | Set complete rule on non-repeating task | |
| 2b | Edit: clear rule | Set then clear with null; get_task confirms gone | |
| 3a | Partial: schedule only | Change schedule; frequency/basedOn/end preserved | |
| 3b | Partial: basedOn only | Change basedOn; others preserved | |
| 3c | Partial: interval + onDays | Change interval with existing onDays re-specified (Pydantic requires onDays) | |
| 3d | Partial: onDays (same type) | Change onDays; interval preserved via same-type merge (model_fields_set) | |
| 3e | Partial: add end | Add end condition; others preserved | |
| 3f | Partial: change end type | Date to occurrences | |
| 3g | Partial: clear end | end: null; others preserved | |
| 4a | Type change: daily to weekly | Full frequency replacement; no merging | |
| 5a | No-op: identical rule | Same rule back returns "identical" warning | |
| 5b | No-op: omitted + field edit | No repetition warning; field change applied | |
| 6a | Status: completed task | Set rule on completed task; "completed" warning | |
| 6b | Status: dropped task | Set rule on dropped task; "dropped" warning | |
| 7a | Lifecycle: complete repeating | Complete repeating task; "next occurrence created" | |
| 7b | Lifecycle: drop repeating | Drop repeating task; "occurrence was skipped" | |
| 8a | Normalize: empty onDates | Empty onDates normalized to monthly; warning present | |
| 8b | Warning: end date past | End date in past; "no future occurrences" warning | |
| 8c | Edge: rule without anchor date | Create with basedOn: due_date but no dueDate; document behavior | |
| 9a | Error: invalid interval | interval=0 returns clean error | |
| 9b | Error: invalid day code | onDays=["XX"] returns clean error | |
| 9c | Error: invalid ordinal | on={"sixth":...} returns clean error | |
| 9d | Error: invalid day name | on={...:"funday"} returns clean error | |
| 9e | Error: invalid onDate | onDates=[0] returns clean error | |
| 9f | Error: invalid end occurrences | occurrences=0 returns clean error | |
| 9g | Error: no existing rule | Partial update on non-repeating task errors | |
| 10a | Clean error format | Missing type field; no pydantic internals leaked | |
| 10b | Clean error: empty end | end: {} returns clean error | |
| 11a | Combo: rule + field edit | Set rule and flagged in same call; both applied | |
| 11b | Combo: no-op rule + name | No-op warning present; name change still applied | |
