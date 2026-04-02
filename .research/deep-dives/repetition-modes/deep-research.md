
# How OmniFocus calculates repeat dates for each mode

**For day-of-week patterns like BYDAY=TU,WE, the three repeat modes differ primarily in what date gets fed into the RRULE engine.** "Regularly" advances from the previously scheduled date (producing past dates if overdue). "Regularly + Catch Up" advances from *now*, always landing in the future. "From Completion" advances from the completion date—and for BYDAY patterns specifically, applies a "skip ahead by interval, then find next matching day" two-step that can push the next occurrence further out than catch-up mode. This distinction is subtle but real, and OmniFocus 4 (unlike versions 2–3) does allow combining BYDAY rules with "From Completion" in both the UI and the API.

The behavioral differences matter most when tasks are completed late. When completed on time, all three modes produce identical results for BYDAY patterns with `INTERVAL=1`. The divergence appears in overdue and early-completion scenarios, where the input date to the RRULE evaluation changes everything.

## The algorithm: one function, three input dates

OmniFocus uses ICS-formatted recurrence strings (RFC 5545 RRULE) internally. The `Task.RepetitionRule` object exposes a method called **`firstDateAfterDate(date)`** that returns the next date matching the RRULE after the given input date. This function operates purely on the RRULE string—it has no knowledge of schedule type. The schedule type determines *which date* gets passed to this function:

- **Regularly (no catch-up):** input = the current occurrence's assigned date (due, defer, or planned, per `anchorDateKey`)
- **Regularly + catch-up:** input = whichever is later: the assigned date or the current date/time. Effectively, it scans forward through the RRULE sequence until finding a date in the future.
- **From Completion:** input = the completion date/time (with rounding applied per the configured time unit)

For a rule like `FREQ=WEEKLY;BYDAY=TU,WE`, the RRULE generates an infinite sequence: every Tuesday and every Wednesday. Calling `firstDateAfterDate(Thursday_April_2)` returns `Tuesday_April_7`—the next matching day after the input. The schedule type just determines whether "Thursday April 2" represents the old due date, the current moment, or the completion timestamp.

## Regularly without catch-up: marching through the past

When a task repeats "Regularly," OmniFocus calculates the next occurrence from the **previously assigned date**, not from when you complete it. For `FREQ=WEEKLY;BYDAY=TU,WE` with a task due Tuesday:

- Complete on Tuesday → `firstDateAfterDate(Tuesday)` → **Wednesday** (next day, on schedule)
- Complete late on Thursday → `firstDateAfterDate(Tuesday)` → **Wednesday** (yesterday—still in the past)
- Complete that past-Wednesday occurrence → `firstDateAfterDate(Wednesday)` → **next Tuesday**

The official OmniFocus 4.7.1 manual states: *"With this setting turned off, completing an item will create the next occurrence following the schedule you have set, even when the next occurrence is in the past."* This forces **multiple completions to catch up** through missed occurrences one by one. Each completion advances exactly one step in the RRULE sequence. For `BYDAY=TU,WE`, the sequence is TU→WE→TU→WE, so falling two weeks behind on a Tuesday task requires four completions to reach the present.

The pre-4.7 workaround documented at `support.omnigroup.com/of2-catch-up/` was to manually reschedule the overdue task to today before completing it, which resets the anchor date. OmniFocus 4.7 automated this with the catch-up toggle.

## Regularly with catch-up: snapping to the schedule grid

The catch-up variant, introduced in **OmniFocus 4.7 (August 2025)**, uses the same RRULE but skips past occurrences. The manual's key passage: *"Regularly with Catch up automatically turned on creates the next occurrence based on the schedule that you have configured, skipping all occurrences that have been missed, so the date of the next occurrence is predictable."*

For `FREQ=WEEKLY;BYDAY=TU,WE`:

- Task due Tuesday, complete on Thursday → skips past Wednesday → `firstDateAfterDate(now=Thursday)` → **next Tuesday** (5 days out)
- Task due Tuesday, complete two weeks late on a Monday → skips all past TU/WE → `firstDateAfterDate(now=Monday)` → **tomorrow (Tuesday)**
- Task due Wednesday, complete on Wednesday → `firstDateAfterDate(Wednesday)` → **next Tuesday** (normal advance)

The schedule grid is preserved. **No matter how late you complete, the next occurrence snaps to the original Tuesday/Wednesday pattern.** This is the defining characteristic: the dates are "predictable" because they always fall on the RRULE's pre-determined days. One additional detail from the manual: *"Repetitions that are set to Catch up automatically do not affect the number of remaining repetitions for End After when catching up automatically"*—skipped occurrences don't count against repeat limits.

## From Completion with BYDAY: the two-step algorithm

In OmniFocus 4 (versions 4.3.3+), the UI **does** allow selecting specific weekdays for "From Completion" repeats—a change from OmniFocus 2/3 where BYDAY selectors were restricted to "Repeat Regularly" only. The OmniFocus 4 reference manual documents a specific two-step algorithm for this combination:

> *"If you use a custom weekly or monthly repeat, where you have chosen specific days or dates for an item to repeat, completing an item will calculate the next occurrence by **skipping ahead, and then finding the next chosen day or date**."*

The manual provides three explicit examples:

- *"An item which repeats every weekday after completion will schedule the next occurrence for the **next available weekday**."* (Complete Friday → next Monday)
- *"An item which repeats **four weeks from completion on weekdays** will schedule the next occurrence for the first available weekday, **at least four weeks from completion**."*
- *"An item which repeats the last Friday of every third month will schedule the next occurrence for the first available last Friday, **at least three months from completion**."*

The algorithm is: **(1) apply the RRULE's interval from the completion date to establish a minimum gap, then (2) find the next matching BYDAY day on or after that point.** For `FREQ=WEEKLY;INTERVAL=1;BYDAY=TU,WE`:

- Complete on Thursday → `firstDateAfterDate(Thursday)` → **next Tuesday** (5 days). The RRULE's `INTERVAL=1` means every week's Tuesday and Wednesday are valid, so the function simply returns the next matching day.
- Complete on Tuesday → `firstDateAfterDate(Tuesday)` → **Wednesday** (next day)
- Complete on Wednesday → `firstDateAfterDate(Wednesday)` → **next Tuesday** (6 days)

For `FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,WE` (every **other** week):

- Complete on Thursday in week 1 → next valid occurrence is Tuesday of week 3 (the next even-week Tuesday per the RRULE sequence anchored to the completion date). This is where "From Completion" diverges significantly from "Regularly"—the every-other-week grid resets based on when you completed.

OmniFocus also applies **time rounding** for From Completion repeats to prevent time drift: completing in the first half of an hour rounds earlier; the second half rounds later. The manual notes you can switch to smaller time units (days→hours, hours→minutes) for finer precision.

## The critical edge case: catch-up vs. From Completion for BYDAY

For `FREQ=WEEKLY;BYDAY=TU,WE` with `INTERVAL=1`, the practical difference between "Regularly + Catch Up" and "From Completion" is **minimal but real**. Both produce future dates. Both find the next matching Tuesday or Wednesday. The differences are:

**Time anchoring.** Regularly preserves the original task's exact times (e.g., due at 5:00 PM stays at 5:00 PM regardless of when you complete). From Completion recalculates times from the completion timestamp, subject to rounding. A task originally due at 5:00 PM Tuesday, completed at 9:00 AM Thursday, will be due at 5:00 PM next Tuesday with catch-up but may shift to 9:00 AM next Tuesday with From Completion.

**Defer-to-due date relationships.** The `anchorDateKey` (new in v4.7) determines which date drives the calculation, with other dates maintaining their relative offsets. For Regularly, the offsets are preserved exactly. For From Completion, the "Based on" date is recalculated from completion, and all other dates shift proportionally.

**INTERVAL > 1 creates real divergence.** For `FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,WE`, Regularly + Catch Up preserves the original odd/even week grid—it finds the next future Tuesday or Wednesday that falls on the correct alternating week. From Completion resets the alternation grid based on the completion date. Over time, this means the two modes could land on entirely different weeks.

**Early completion.** If you complete a Tuesday task on Monday (a day early), Regularly still advances to Wednesday (the next scheduled date after Tuesday). From Completion uses Monday as the input, so `firstDateAfterDate(Monday)` returns Tuesday—**the task reappears the next day** rather than advancing to Wednesday.

## API reference for MCP server implementation

The v4.7+ Omni Automation API exposes repetition through these types:

```javascript
// Schedule types (replaces deprecated Task.RepetitionMethod)
Task.RepetitionScheduleType.Regularly     // Fixed calendar schedule
Task.RepetitionScheduleType.FromCompletion // Completion-relative
Task.RepetitionScheduleType.None          // No repeat

// Anchor date (which date drives the calculation)
Task.AnchorDateKey.DueDate
Task.AnchorDateKey.DeferDate  
Task.AnchorDateKey.PlannedDate  // New in v4.7

// Constructor (v4.7+)
new Task.RepetitionRule(
    ruleString,            // ICS RRULE, e.g., "FREQ=WEEKLY;BYDAY=TU,WE"
    null,                  // deprecated method param—must be null
    scheduleType,          // Task.RepetitionScheduleType.Regularly
    anchorDateKey,         // Task.AnchorDateKey.DueDate  
    catchUpAutomatically   // Boolean, only meaningful for Regularly
)
```

The legacy `Task.RepetitionMethod` enum maps to the new system as follows: **`Fixed` → Regularly**, **`DueDate` → FromCompletion + AnchorDateKey.DueDate** (confusingly named—"DueDate" meant "due again after completion"), and **`DeferUntilDate` → FromCompletion + AnchorDateKey.DeferDate**. Passing both a non-null `method` and a `scheduleType` throws an error.

The `firstDateAfterDate(date)` method on `Task.RepetitionRule` evaluates the RRULE string and returns the next matching date after the input, independent of schedule type. This is the core utility for programmatically previewing what the next occurrence will be.

## Practical documentation guidance for AI agents

For an MCP server that needs to explain repeat options to an AI agent setting up tasks, the clearest framing is:

**"Regularly"** means the task is locked to a calendar grid. Use for obligations tied to specific dates: rent due the 1st, team standup every MWF, trash pickup every Tuesday. If the user falls behind, uncompleted occurrences stack up in the past. Enable **catch-up** (the default recommendation) so completing an overdue task jumps to the next future grid point rather than requiring multiple completions.

**"From Completion"** means the schedule floats based on actual behavior. Use for maintenance tasks where the interval matters more than the specific day: water plants every 10 days, clean the kitchen every 5 days, review investments quarterly. With BYDAY constraints, the task will land on the next matching day *after* the interval elapses from completion—useful for "do this weekly but only on a weekday" patterns.

The decision tree: Does the task need to happen on specific calendar days regardless of completion history? → **Regularly + Catch Up**. Does the minimum time gap between occurrences matter more than landing on a fixed day? → **From Completion**. For BYDAY patterns with `INTERVAL=1`, the practical difference is small—both land on the same days in most scenarios. The divergence grows with longer intervals or when tasks are frequently completed early or late.

## Conclusion

The three repeat modes share a single RRULE evaluation engine (`firstDateAfterDate`) but differ in what date they feed it. For day-of-week patterns, this means "Regularly" preserves the original calendar grid, "Catch Up" jumps forward on that same grid, and "From Completion" restarts the RRULE evaluation from a floating completion-based anchor point. The OmniFocus 4.3.3 release explicitly added support for BYDAY + FromCompletion combinations with a documented "skip ahead, then find next matching day" algorithm—resolving what was a UI limitation in earlier versions. For `INTERVAL=1` BYDAY patterns, the catch-up and From Completion modes converge in behavior except for time anchoring and early-completion handling. For `INTERVAL≥2`, they genuinely diverge because From Completion resets the alternation grid while Regularly preserves it.