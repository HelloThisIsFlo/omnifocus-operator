# OmniFocus Concepts

Concepts that matter for understanding the OmniFocus Operator API. This is not an OmniFocus manual — it covers only the concepts that affect how agents should interact with the server.

## Dates

OmniFocus has three date fields. They serve fundamentally different purposes and should never be conflated.

### Due Date

A real-world deadline with negative consequences if missed.

The consequence doesn't have to be catastrophic — it ranges from severe (contract expires, legal deadline) to soft (a relationship suffers because you didn't reply within a reasonable window). What makes it a due date is that **missing it has a real, tangible downside**.

**Not a due date:** "I want to clean the living room on Tuesday." If Wednesday works just as well, there's no deadline — there's no negative consequence for missing Tuesday. Setting this as a due date pollutes the urgency signal.

**A due date:** "Reply to Sarah about dinner plans by Friday." If you don't, the relationship takes a small hit. That's a real consequence, even if minor.

**Why this matters:** The moment you start using due dates for intentions ("I'd like to do this by..."), every task becomes "due," nothing stands out, and you lose the urgency signal entirely. Due dates should trigger a sense of "this must happen by then" — reserve them for exactly that.

### Defer Date

The task is **impossible to act on** until this date. Not "I don't want to work on it yet" — literally cannot.

**Example:** Your flat contract renewal window opens 2 months before the lease ends. You physically cannot renew before that window opens. The task is deferred to that date because acting on it earlier is impossible.

**Behavior:** Deferred tasks disappear from most OmniFocus views until the defer date arrives. This is by design — if you can't act on it, you shouldn't see it. When the date arrives, the task reappears and becomes available.

**Not a defer date:** "I don't feel like working on this until next week." If you *could* work on it now but choose not to, that's not a deferral — you'd be hiding a task you might actually want to see. Use planned date instead.

### Planned Date

"I wish I worked on this on that date."

Fills the gap between due (too urgent — implies negative consequences) and defer (too hidden — removes from view):

- **No urgency signal** — won't turn red or yellow as it approaches
- **Task stays visible** — unlike defer, the task remains in your views before the planned date
- **Pure intention** — signals when you'd like to work on it, with no penalty for missing it

**Example:** "I'd like to review the Q3 roadmap on Thursday." No consequence if you do it Friday. You still want to see it before Thursday in case you get to it early. Not urgent, not blocked — just planned.

**Power use:** Combined with custom OmniFocus perspectives, planned dates enable sophisticated workflows — filtering by "planned for this week," sorting by planned date within a project, etc.

### Summary

| Field | Meaning | Consequence of missing | Visibility before date |
|-------|---------|----------------------|----------------------|
| Due date | Must happen by then | Real negative consequence | Visible, urgency signals |
| Defer date | Cannot act until then | N/A (impossible before) | Hidden from most views |
| Planned date | Want to work on it then | None | Visible, no urgency |

**The rule:** Due dates are for deadlines. Defer dates are for constraints. Planned dates are for intentions. If you're unsure which to use, it's probably a planned date.

## Repetition Rules

OmniFocus tasks and projects can repeat. A repetition rule has three components: **frequency** (how often), **schedule** (what triggers the next occurrence), and **basedOn** (which date field anchors the schedule).

### Based On (Anchor Date)

The anchor date determines which date field the repetition schedule attaches to. When the next occurrence is generated, the anchor date moves to the scheduled date. **All other date fields shift relatively, preserving their current offset from the anchor.**

**Example:** A task repeats on the 15th of every month. The anchor is `planned_date`. Currently:
- Planned date: March 15
- Due date: March 18 (+3 days from anchor)
- Defer date: March 10 (−5 days from anchor)

When the next occurrence is generated:
- Planned date → April 15 (the scheduled date)
- Due date → April 18 (anchor + 3 days, offset preserved)
- Defer date → April 10 (anchor − 5 days, offset preserved)

| Value | Meaning |
|-------|---------|
| `due_date` | Schedule anchored to the due date |
| `defer_date` | Schedule anchored to the defer date |
| `planned_date` | Schedule anchored to the planned date |

**The rule:** Choose the date that the recurrence is "about." If a task is due every Friday, anchor on `due_date`. If it becomes available every Monday, anchor on `defer_date`. If you just want to plan it for the same day each week, anchor on `planned_date`.

> **⚠️ WIP — What happens when the anchor date field is not set on the task?** Likely falls back to the task's creation date, but this needs verification.

### Schedule (Recurrence Mode)

> **⚠️ WIP — Edge cases under review.** The descriptions below are accurate for simple intervals (e.g., "every 3 days"). The behavior when combined with specific day-of-week patterns (e.g., "every Wednesday and Friday") is not fully documented — in particular, how `from_completion` differs from `regularly_with_catch_up` in that scenario is unclear.

The schedule controls what happens when a task is completed — specifically, how the next occurrence's date is calculated.

#### `regularly`

Fixed calendar schedule. The next occurrence lands on the next scheduled date regardless of when you complete the current one.

**Key behavior:** If you fall behind, every missed occurrence stays and must be individually resolved. Nothing is skipped.

**Example:** Rent is due on the 1st of every month. You forget March and April. Both missed occurrences remain — you owe two months of rent, and OmniFocus reflects that.

**When to use:** When every occurrence matters and skipping one would be a real problem.

#### `regularly_with_catch_up`

Fixed calendar schedule, but OmniFocus **catches up for you** — if you complete a task late, it skips past any overdue occurrences and jumps to the next future date.

**Example:** A weekly review repeats every Monday. You complete it 3 weeks late. Instead of creating 3 overdue occurrences, OmniFocus skips ahead to next Monday.

**When to use:** The most common mode for recurring tasks. Use when the rhythm matters but individual missed occurrences don't need to be tracked.

#### `from_completion`

The next occurrence is calculated from **when you actually complete** the current one, not from the original scheduled date.

**Example:** "Water the plants every 5 days." You complete it 2 days late. The next occurrence isn't in 3 days (to stay on the original 5-day grid) — it's in 5 days from now, because the interval restarts from the completion moment.

**When to use:** When the interval between occurrences is what matters, not hitting specific calendar dates. Common for habits, maintenance tasks, and anything where "every N days" means "N days after you last did it."

### Summary

| Schedule | Next date based on | Missed occurrences |
|----------|-------------------|-------------------|
| `regularly` | Fixed calendar | Stay — must be individually resolved |
| `regularly_with_catch_up` | Fixed calendar | Skipped — jumps to next future date |
| `from_completion` | Completion moment | N/A — no concept of "missed" |
