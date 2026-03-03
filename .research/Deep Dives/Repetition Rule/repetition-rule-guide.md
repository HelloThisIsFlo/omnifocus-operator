# OmniFocus Task.RepetitionRule — Complete Guide (v4.7+ Only)

This document covers every scenario for working with repetition rules in OmniFocus via the Omni Automation JavaScript API. It targets OmniFocus 4.7+ exclusively and uses only the current (non-deprecated) API surface.

> **Key insight:** All properties on a `Task.RepetitionRule` are read-only. You cannot mutate an existing rule — you always create a new `Task.RepetitionRule` and assign it to `task.repetitionRule`. This applies to every "modify" operation.

---

## Where This Lives on the Task

A Task in OmniFocus has many properties. Here's how repetition fits into the broader picture:

```
Task
├── name                    "Weekly Team Standup"
├── dueDate                 2026-03-10T10:00:00Z
├── deferDate               2026-03-09T09:00:00Z
├── flagged                 false
├── taskStatus              Available
├── ...
│
└── repetitionRule          ← null if non-repeating, or a Task.RepetitionRule:
     ├── ruleString             "FREQ=WEEKLY;BYDAY=MO"
     ├── scheduleType           Regularly
     ├── anchorDateKey          DueDate
     └── catchUpAutomatically   true
```

When a repeating task is completed, OmniFocus uses the `repetitionRule` to generate the next occurrence. It reads the `ruleString` to calculate the next date, applies it to the date specified by `anchorDateKey` (due, defer, or planned), and uses `scheduleType` to decide whether that calculation is relative to the calendar (`Regularly`) or to the completion moment (`FromCompletion`).

The task's `dueDate`, `deferDate`, and other date properties are *not* part of the rule — they're on the task itself. The rule just describes *how* to compute the next set of dates when the current occurrence is resolved.

---

## API Reference

### Constructor

```javascript
new Task.RepetitionRule(
    ruleString,              // String — ICS RRULE (e.g. "FREQ=WEEKLY")
    null,                    // method — ALWAYS pass null (deprecated param)
    scheduleType,            // Task.RepetitionScheduleType
    anchorDateKey,           // Task.AnchorDateKey
    catchUpAutomatically     // Boolean
)
```

### Task.RepetitionScheduleType

| Value | Meaning |
|---|---|
| `Task.RepetitionScheduleType.Regularly` | Fixed calendar schedule — next occurrence is calculated from the assigned dates |
| `Task.RepetitionScheduleType.FromCompletion` | Next occurrence is relative to when the task is completed |
| `Task.RepetitionScheduleType.None` | Task does not repeat. You will never use this directly — to remove repetition, set `task.repetitionRule = null`. This value exists for the `.all` array used in plug-in form dropdowns. |

### Task.AnchorDateKey

| Value | Meaning |
|---|---|
| `Task.AnchorDateKey.DueDate` | Repetition updates the due date |
| `Task.AnchorDateKey.DeferDate` | Repetition updates the defer (start) date |
| `Task.AnchorDateKey.PlannedDate` | Repetition updates the planned date (v4.7+) |

### Read-Only Properties on a RepetitionRule Instance

| Property | Type | Description |
|---|---|---|
| `ruleString` | `String` | The ICS RRULE string |
| `scheduleType` | `Task.RepetitionScheduleType` | How the schedule is applied |
| `anchorDateKey` | `Task.AnchorDateKey` | Which date is updated on repetition |
| `catchUpAutomatically` | `Boolean` | Whether missed occurrences are auto-skipped |
| `firstDateAfterDate(date)` | Function | Returns the next occurrence after the given date |

---

## Group 1 — Create a Fixed (Regular) Repetition

Use `Regularly` when the task should repeat on a predictable calendar schedule regardless of when it's completed.

```javascript
var task = flattenedTasks.byName("Weekly Team Standup");

task.repetitionRule = new Task.RepetitionRule(
    "FREQ=WEEKLY",                              // every week
    null,                                       // deprecated param, always null
    Task.RepetitionScheduleType.Regularly,       // fixed calendar schedule
    Task.AnchorDateKey.DueDate,                  // update the due date
    true                                         // auto-skip missed occurrences
);
```

### Parameter variations (no separate code needed)

**Anchor date options** — swap `Task.AnchorDateKey.DueDate` for:
- `Task.AnchorDateKey.DeferDate` — useful when the defer/start date is what matters (e.g. "become available again every Monday")
- `Task.AnchorDateKey.PlannedDate` — for tasks tracked by planned date

**Catch-up behaviour:**
- `true` — if you complete a weekly task 3 weeks late, it skips to the next future occurrence rather than creating 3 overdue copies
- `false` — each missed occurrence must be individually resolved; useful for things like "monthly rent payment" where every instance matters

---

## Group 2 — Create a From-Completion Repetition

Use `FromCompletion` when the next occurrence should be calculated relative to when you actually complete the task, not when it was originally scheduled.

```javascript
var task = flattenedTasks.byName("Clean the coffee machine");

task.repetitionRule = new Task.RepetitionRule(
    "FREQ=DAILY;INTERVAL=3",                    // 3 days after completion
    null,
    Task.RepetitionScheduleType.FromCompletion,  // relative to completion
    Task.AnchorDateKey.DeferDate,                // update the defer date
    false                                        // catchUp is not meaningful here
);
```

### When to use which schedule type

| Scenario | Schedule Type | Why |
|---|---|---|
| "Staff meeting every Tuesday" | `Regularly` | It's on Tuesday regardless of when you check it off |
| "Water plants every 5 days" | `FromCompletion` | The 5-day interval restarts when you actually water them |
| "Rent due on the 1st" | `Regularly` + `catchUp: false` | Calendar-fixed, and every missed one matters |
| "Haircut every 6 weeks" | `FromCompletion` | Relative to when you last got one |

### Note on catchUpAutomatically with FromCompletion

`catchUpAutomatically` only applies to `Regularly`. For `FromCompletion`, the next date is always calculated from the completion moment, so there's no concept of "missed" occurrences. You can pass `false` — it's effectively ignored.

---

## Group 3 — RRULE String Reference

The rule string follows the iCalendar RRULE specification. OmniFocus doesn't change or extend this syntax — it's standard ICS. Here are the patterns you'll actually use:

### Frequency and interval

| Rule String | Plain English |
|---|---|
| `FREQ=DAILY` | Every day |
| `FREQ=DAILY;INTERVAL=3` | Every 3 days |
| `FREQ=WEEKLY` | Every week |
| `FREQ=WEEKLY;INTERVAL=2` | Every 2 weeks |
| `FREQ=MONTHLY` | Every month |
| `FREQ=MONTHLY;INTERVAL=3` | Every 3 months (quarterly) |
| `FREQ=YEARLY` | Every year |

### Specific days of the week

| Rule String | Plain English |
|---|---|
| `FREQ=WEEKLY;BYDAY=MO` | Every Monday |
| `FREQ=WEEKLY;BYDAY=MO,WE,FR` | Every Mon, Wed, Fri |
| `FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH` | Every 2 weeks on Tue and Thu |

### Monthly by day of month

| Rule String | Plain English |
|---|---|
| `FREQ=MONTHLY;BYMONTHDAY=1` | The 1st of every month |
| `FREQ=MONTHLY;BYMONTHDAY=15` | The 15th of every month |
| `FREQ=MONTHLY;BYMONTHDAY=-1` | The last day of every month |

### Monthly by position (nth weekday)

| Rule String | Plain English |
|---|---|
| `FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2` | The 2nd Tuesday of every month |
| `FREQ=MONTHLY;BYDAY=FR;BYSETPOS=1` | The 1st Friday of every month |
| `FREQ=MONTHLY;BYDAY=MO;BYSETPOS=-1` | The last Monday of every month |
| `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=2` | The 2nd weekend day of every month |

### Limiting repetitions

| Rule String | Plain English |
|---|---|
| `FREQ=WEEKLY;COUNT=10` | Every week, 10 times total then stop |
| `FREQ=MONTHLY;UNTIL=20261231T000000Z` | Every month until Dec 31, 2026 |

### Tips

- Do not include a trailing semicolon (e.g. `FREQ=WEEKLY;` will error)
- Day codes: `MO`, `TU`, `WE`, `TH`, `FR`, `SA`, `SU`
- `UNTIL` uses ISO 8601 format with a `Z` suffix for UTC
- The easiest way to derive a complex rule string is to set it up in the OmniFocus UI first, then read `task.repetitionRule.ruleString` from the console
- The RRULE Tool at [iCalendar.org](https://icalendar.org/rrule-tool.html) is useful for generating and validating rule strings

---

## Group 4 — Modifying an Existing Repetition

Since all properties on `Task.RepetitionRule` are read-only, modifying means: read the current config, construct a new rule with your changes, and reassign.

```javascript
var task = flattenedTasks.byName("Weekly Report");
var current = task.repetitionRule;

if (!current) {
    throw new Error("Task is not repeating");
}

// Example: change from weekly to biweekly, keep everything else
task.repetitionRule = new Task.RepetitionRule(
    "FREQ=WEEKLY;INTERVAL=2",                 // changed: was "FREQ=WEEKLY"
    null,
    current.scheduleType,                      // preserved
    current.anchorDateKey,                     // preserved
    current.catchUpAutomatically               // preserved
);
```

### Common modifications as one-liners

**Change frequency only** (keep schedule type, anchor, catch-up):
```javascript
task.repetitionRule = new Task.RepetitionRule(
    "FREQ=MONTHLY",     // new rule string
    null,
    current.scheduleType,
    current.anchorDateKey,
    current.catchUpAutomatically
);
```

**Change anchor date only** (keep rule string, schedule type, catch-up):
```javascript
task.repetitionRule = new Task.RepetitionRule(
    current.ruleString,
    null,
    current.scheduleType,
    Task.AnchorDateKey.DeferDate,   // changed
    current.catchUpAutomatically
);
```

**Switch from Regularly to FromCompletion** (keep rule string, anchor):
```javascript
task.repetitionRule = new Task.RepetitionRule(
    current.ruleString,
    null,
    Task.RepetitionScheduleType.FromCompletion,  // changed
    current.anchorDateKey,
    false                                         // not meaningful for FromCompletion
);
```

**Toggle catch-up** (keep everything else):
```javascript
task.repetitionRule = new Task.RepetitionRule(
    current.ruleString,
    null,
    current.scheduleType,
    current.anchorDateKey,
    !current.catchUpAutomatically   // toggled
);
```

### Multi-change example

Switch from "regularly every week on due date with catch-up" to "from completion every 2 weeks on defer date":

```javascript
task.repetitionRule = new Task.RepetitionRule(
    "FREQ=WEEKLY;INTERVAL=2",
    null,
    Task.RepetitionScheduleType.FromCompletion,
    Task.AnchorDateKey.DeferDate,
    false
);
```

---

## Group 5 — Removing Repetition

```javascript
task.repetitionRule = null;
```

That's it. The task becomes non-repeating. Any existing due/defer dates remain unchanged — only the repetition schedule is cleared.

---

## Group 6 — Reading Repetition Config

### Full extraction

```javascript
var task = flattenedTasks.byName("Weekly Review");
var r = task.repetitionRule;

if (r) {
    var info = {
        ruleString:     r.ruleString,
        scheduleType:   r.scheduleType.name,
        anchorDateKey:  r.anchorDateKey.name,
        catchUp:        r.catchUpAutomatically
    };
    console.log(JSON.stringify(info, null, 2));
} else {
    console.log("Task does not repeat");
}
```

Example output:
```json
{
    "ruleString": "FREQ=WEEKLY;BYDAY=MO,WE,FR",
    "scheduleType": "Regularly",
    "anchorDateKey": "DueDate",
    "catchUp": true
}
```

### Getting the next occurrence

```javascript
var r = task.repetitionRule;
if (r) {
    var nextDate = r.firstDateAfterDate(new Date());
    console.log("Next occurrence: " + nextDate.toISOString());
}
```

This is useful for forecasting — e.g., showing the user when a task will next appear without having to parse the RRULE yourself.

---

## Compatibility Note

This guide targets OmniFocus 4.7+ with a migrated database. On older versions or unmigrated databases, the v4.7 properties (`scheduleType`, `anchorDateKey`, `catchUpAutomatically`) do not exist on the `RepetitionRule` prototype. Accessing them will return `undefined`, and calling `.name` on `undefined` will throw a `TypeError`.

For the MCP server, the recommended approach is to detect this on the first repeating task encountered:

```javascript
var r = task.repetitionRule;
if (r && r.scheduleType === undefined) {
    throw new Error(
        "OmniFocus database must be migrated to 4.7+ format. " +
        "Open Settings > Database and complete the migration, then retry."
    );
}
```

---

## Before vs After: Legacy API Comparison

This section is for context only. The rest of this document uses exclusively the v4.7+ API.

### Before (pre-4.7)

The old API crammed schedule type and anchor date into a single `Task.RepetitionMethod` enum:

```javascript
// Old way — Task.RepetitionMethod combined two concepts into one value
task.repetitionRule = new Task.RepetitionRule(
    "FREQ=WEEKLY",
    Task.RepetitionMethod.DueDate          // this meant: Regularly + anchor to DueDate
);

// The available methods were:
//   Task.RepetitionMethod.Fixed           → Regularly (anchor unclear)
//   Task.RepetitionMethod.DueDate         → Regularly + DueDate
//   Task.RepetitionMethod.DeferDate       → Regularly + DeferDate
//   Task.RepetitionMethod.DueAfterCompletion   → FromCompletion + DueDate
//   Task.RepetitionMethod.DeferAfterCompletion → FromCompletion + DeferDate

// Reading was similarly limited:
var method = task.repetitionRule.method;    // Task.RepetitionMethod — one combined value
var rule = task.repetitionRule.ruleString;  // String — same as today
// No access to catchUpAutomatically — it didn't exist as a concept
```

### After (4.7+)

The new API separates the concerns into independent, composable parameters:

```javascript
// New way — each concept is its own parameter
task.repetitionRule = new Task.RepetitionRule(
    "FREQ=WEEKLY",                              // ruleString (unchanged)
    null,                                       // method (deprecated, always null)
    Task.RepetitionScheduleType.Regularly,       // schedule type (was baked into method)
    Task.AnchorDateKey.DueDate,                  // anchor date (was baked into method)
    true                                         // catchUpAutomatically (new capability)
);

// Reading is now granular:
var r = task.repetitionRule;
r.ruleString;              // "FREQ=WEEKLY"
r.scheduleType.name;       // "Regularly"
r.anchorDateKey.name;      // "DueDate"
r.catchUpAutomatically;    // true
r.method.name;             // still populated for compat, but ignore it
```

### What changed in summary

| Aspect | Pre-4.7 | 4.7+ |
|---|---|---|
| Schedule type + anchor | Combined in `Task.RepetitionMethod` | Separate: `scheduleType` + `anchorDateKey` |
| Catch-up behaviour | Not configurable | `catchUpAutomatically` boolean |
| PlannedDate as anchor | Not available | `Task.AnchorDateKey.PlannedDate` |
| Constructor | 2 params: `(ruleString, method)` | 5 params: `(ruleString, null, scheduleType, anchorDateKey, catchUp)` |
| Reading properties | `method` + `ruleString` | `scheduleType` + `anchorDateKey` + `catchUpAutomatically` + `ruleString` |
