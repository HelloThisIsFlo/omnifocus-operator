---
date: "2026-03-17 16:45"
promoted: false
---

**Question**: When you complete a task that's already dropped AND has a repetition rule, does OmniFocus actually create the next occurrence?

**Why it matters**: The test `test_lifecycle_cross_state_repeating_stacked_warnings` (in `tests/test_service.py`) asserts both warnings stack:
- "Task was already dropped -- lifecycle action applied, task is now complete."
- "Repeating task -- this occurrence completed, next occurrence created."

But the second warning might be wrong. If the task was dropped, it's arguably no longer repeating — so OmniFocus might NOT create a new occurrence, yet we tell the user it did.

**Action**: UAT-test this against real OmniFocus. Drop a repeating task, then complete it, and check whether a new occurrence appears. If it doesn't, fix the warning (or suppress it in this scenario).

**Priority**: Low — discovered while investigating something else.
