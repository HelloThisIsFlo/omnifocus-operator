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
