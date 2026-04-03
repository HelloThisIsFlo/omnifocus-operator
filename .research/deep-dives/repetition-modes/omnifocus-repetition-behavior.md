# OmniFocus Repetition Behavior: Empirical Reference

## Context

This document records empirically verified behavior for OmniFocus repetition scheduling, established through controlled experiments using the OmniFocus Operator MCP server. All findings were validated on OmniFocus 4.7+ (April 2026) in BST (UTC+1) timezone.

This reference is intended for agents working on the OmniFocus Operator MCP server. Treat it as ground truth — every claim here was tested and confirmed against real OmniFocus behavior, not inferred from documentation.

---

## Part 1: The Three Schedule Types

OmniFocus offers three repetition schedule types. Their behavior differs based on what date is fed into the RRULE engine when a task is completed.

### Regularly (no catch-up)

The next occurrence is calculated from the **previously scheduled date**, not from when you complete it. If the next occurrence falls in the past, it stays in the past — you must complete it again to advance, one step at a time.

**Verified**: A task due Sat Mar 30 at 10 PM, completed on Thu Apr 2, required 3 completions to reach the present. Each completion advanced exactly one day on the grid.

### Regularly with Catch Up

Same fixed calendar grid as "regularly," but skips past any occurrences that have already passed. One completion jumps to the next future occurrence on the original schedule. The check is **time-level** — it considers both the date AND the time when determining whether a grid point is "in the future" (see Part 3).

**Verified**: Same task as above, one completion jumped straight to Thu Apr 2 at 10 PM (the next future daily slot). Original time preserved.

### From Completion

The next occurrence is calculated from the **completion date**. The schedule floats based on when you actually complete it. The check is **day-level** — the completion day itself never counts as a valid next occurrence, regardless of time-of-day (see Part 3).

**Verified**: Same task, one completion created the next occurrence on Fri Apr 3 at 10 PM. The interval (1 day) was applied from the completion date.

---

## Part 2: Time Preservation (Not Drift)

A deep research report claimed that "from completion" causes the due *time* to drift to the completion timestamp, while "regularly + catch up" preserves the original time. **This is incorrect at every granularity we tested.**

### What we tested

- **Weekly BYDAY**: Tasks repeating on WE+FR, originally due at 10 PM BST. Completed 21+ hours off from the original time. All three modes preserved 10 PM.
- **Daily**: Tasks repeating daily at 10 PM BST. Completed at various times. All three modes preserved 10 PM.
- **Hourly**: Task repeating every 2 hours from 10 AM BST, completed at 12:36 PM. Next occurrence landed at 2 PM — on the original 10/12/2/4 grid, not at 2:36 PM (completion + 2h).

### Conclusion

**All three modes preserve the original RRULE time grid at every granularity tested (hourly, daily, weekly).** OmniFocus's rounding mechanism prevents time drift. The RRULE generates a fixed grid of valid times, and both catch-up and from-completion simply find the next point on that grid — they never shift the grid itself.

The deep research report's claim about time drift as a key differentiator between catch-up and from-completion is wrong.

---

## Part 3: The Fundamental Asymmetry — Day-Level vs Time-Level

The real difference between catch-up and from-completion is not about time drift. It's about **what granularity each mode uses when deciding whether an occurrence is "in the past."**

### The rule

| Mode | Granularity | Behavior |
|------|-------------|----------|
| **Catch-up** | **Time-level** | A same-day grid point counts as "future" if its exact time hasn't passed yet |
| **From-completion** | **Day-level** | The completion day itself NEVER counts, regardless of time-of-day |

### Proof: Q1 — From-completion skips today even when the time is still future

- Task due **today** (Friday) at 10 PM BST, repeating WE+FR, from_completion
- Completed at 12:36 PM BST — over 9 hours before the due time
- Next occurrence: **Wed Apr 8** at 10 PM (not today)

Even though Friday is a BYDAY match and 10 PM was still 9+ hours away, from-completion skipped to next Wednesday. **Today never counts for from-completion, period.**

### Proof: Q2 — Catch-up skips today when the time HAS passed

- Task overdue from Wednesday at 10 AM BST, repeating WE+FR, catch_up
- Today's grid point: Friday at 10 AM — already passed (it's afternoon)
- Completed at 12:36 PM BST
- Next occurrence: **Wed Apr 8** at 10 AM (not today)

Catch-up skipped today because the 10 AM grid point had already passed.

### Contrast: Catch-up lands on today when the time is still future

- Task overdue from Wednesday at 10 PM BST, repeating WE+FR with INTERVAL=2, catch_up
- Today's grid point: Friday at 10 PM — still in the future (it's ~noon)
- Next occurrence: **today** (Friday) at 10 PM

Catch-up landed on today because the 10 PM grid point was still ahead.

### Combined truth table

| Scenario | From-completion | Catch-up |
|----------|----------------|----------|
| Today is a match day, time still future | **Skips today** | **Lands on today** ✅ |
| Today is a match day, time already past | **Skips today** | **Skips today** |
| Today is NOT a match day | Finds next match | Finds next match |

This asymmetry is the single most important behavioral difference between the two modes for BYDAY patterns.

---

## Part 4: Late and Early Completion with BYDAY

### Late completion (overdue task)

Tasks repeating weekly on WE+FR, due Wed Apr 1 at 10 PM (overdue). Completed Fri Apr 3 at ~1 AM.

| Schedule | New due | Explanation |
|----------|---------|-------------|
| Regularly (no catch-up) | **Fri Apr 3** at 10 PM | Next in WE→FR sequence after Wed. Still overdue until 10 PM. |
| Regularly + Catch Up | **Fri Apr 3** at 10 PM | Same grid, skipped past Wed, found Fri (still future at 1 AM). |
| From Completion | **Wed Apr 8** at 10 PM | `firstDateAfterDate(Friday)` → next Wed. **Skipped today entirely.** |

From-completion created a **5-day gap** compared to catch-up. This is because from-completion's day-level rounding eliminates Friday, while catch-up's time-level check saw that Friday at 10 PM was still in the future.

### Early completion (before due date)

Tasks repeating weekly on WE+FR, due Wed Apr 8 at 10 PM (in the future). Completed Fri Apr 3 (5 days early).

| Schedule | New due | Explanation |
|----------|---------|-------------|
| Regularly (no catch-up) | **Fri Apr 10** at 10 PM | Next in WE→FR sequence after the scheduled Wed Apr 8. |
| Regularly + Catch Up | **Fri Apr 10** at 10 PM | Same as above — nothing to catch up when completing early. |
| From Completion | **Wed Apr 8** at 10 PM | `firstDateAfterDate(Fri Apr 3)` → Wed Apr 8. **Comes back sooner.** |

When completing early, from-completion brings the task back **sooner** than regularly. The regularly modes advance from the scheduled date (Wed → Fri), while from-completion finds the next matching BYDAY after the completion date (Fri → Wed).

**Implication for agents**: If a user wants to "get ahead" on a BYDAY task by completing it early, from-completion will bring it back sooner than they might expect.

---

## Part 5: INTERVAL ≥ 2 Grid Reset — Confirmed

The deep research report claimed that from-completion resets the alternating week grid while catch-up preserves it. **This is confirmed and the divergence is dramatic.**

### What we tested

Tasks repeating every 2 weeks on WE+FR, due Wed Apr 1 at 10 PM (overdue). Completed Fri Apr 3 at ~noon.

| Schedule | New due | Gap from completion |
|----------|---------|-------------------|
| Regularly + Catch Up | **Fri Apr 3** at 10 PM | **0 days** (tonight!) |
| From Completion | **Fri Apr 17** at 10 PM | **14 days** |

### Explanation

**Catch-up** preserved the original biweekly grid. The grid had Apr 1 (Wed) and Apr 3 (Fri) in the same cycle. Since Fri Apr 3 at 10 PM was still in the future at the time of completion (~noon), it landed there.

**From-completion** reset the grid from the completion date. With INTERVAL=2, it applied a 2-week minimum gap from the completion date (Fri Apr 3), then found the next matching WE or FR: Fri Apr 17.

**This is a 14-day difference between the two modes.** For tasks with INTERVAL ≥ 2, the choice between catch-up and from-completion has massive practical consequences. Agents should flag this to users when setting up biweekly or less frequent BYDAY patterns.

---

## Part 6: Repeat Limits and Catch-Up

### Do skipped occurrences count against repeat limits?

**No. Empirically verified.**

- Task created with `end: {occurrences: 6}`, due 5 days ago, daily, catch_up
- Completed once — catch-up skipped 4 past occurrences
- New `end` value: `{occurrences: 5}`

The count decremented by **1** (from 6 to 5), not by 5. Only the actual completion counted. The 4 skipped occurrences were free.

This confirms the OmniFocus 4.7 manual's statement and upgrades it from "documented" to "empirically verified."

---

## Part 7: Missing Anchor Date Behavior

When the `basedOn` (anchor) field points to a date property that is **not set** on the task, OmniFocus handles it gracefully but potentially surprisingly.

### Summary

OmniFocus does NOT refuse to repeat, does NOT silently skip the repetition, and does NOT fall back to the task's creation date. Instead:

1. **Creates the missing anchor date from scratch** on the next occurrence.
2. Uses the **completion date** for the date portion (not the creation date).
3. Uses the **user's configured default time** for that date type (from OmniFocus Settings → Dates & Times) for the time portion.
4. Shifts any other existing dates forward proportionally.
5. Dates that were never set remain unset.

### How we proved this

**Experiment 1 (same-day)**: Created and completed tasks within minutes. Ruled out that OmniFocus refuses or skips. Showed that the missing anchor date is created from scratch. Could not distinguish creation vs completion date (both on same day).

**Experiment 2 (cross-day)**: Created tasks on April 2, completed on April 3. All new anchor dates landed on **April 4** (completion + 1 day), not April 3 (creation + 1 day). This definitively proved **completion date fallback**, disproving the creation date hypothesis.

**Experiment 3 (time verification)**: Compared new anchor times against OmniFocus default time settings:

| Anchor type | New time (BST) | Setting |
|-------------|----------------|---------|
| due_date | 19:00 | Default time for due dates: **19:00** ✅ |
| defer_date | 08:00 | Default time for defer dates: **08:00** ✅ |
| planned_date | 09:00 | Default time for planned dates: **09:00** ✅ |

### The complete algorithm

```
1. Take the COMPLETION DATE (date portion only)
2. Apply the repeat interval (e.g., +1 day for FREQ=DAILY)
3. Set the TIME to the user's configured default for that date type:
   - due_date    → Settings > "Default time for due dates"
   - defer_date  → Settings > "Default time for defer dates"  
   - planned_date → Settings > "Default time for planned dates"
4. This becomes the new anchor date on the next occurrence
5. Any other dates that WERE set shift forward by the same delta
6. Any dates that were NOT set remain unset
```

Behavior is consistent across all three schedule types.

### MCP Server Warning

The current warning text is incorrect:

> ❌ "OmniFocus will fall back to the task's creation date as the anchor."

Recommended replacement:

> ✅ "OmniFocus will create the missing {anchor_field} on the next occurrence using the completion date and the user's default time for {date_type} (configured in Settings → Dates & Times). This produces a valid but potentially surprising schedule. Set the {anchor_field} explicitly for predictable repetition behavior."

---

## Part 8: Decision Guide for Agents

When an agent needs to choose a schedule type for a user's repeating task:

### Use `regularly_with_catch_up` when:
- The task is tied to specific calendar days (standup every MWF, rent on the 1st)
- The user wants to skip over missed occurrences without tapping through them
- The user might complete early and wants today's occurrence to still count (if the time hasn't passed)
- **This is the recommended default for most recurring tasks**

### Use `regularly` (no catch-up) when:
- The user explicitly needs to process every missed occurrence (e.g., logging daily entries)
- Missing an occurrence has real consequences that can't be skipped

### Use `from_completion` when:
- The minimum time gap between occurrences matters more than the specific day
- Examples: "water plants every 10 days," "replace filter every 3 months"
- **Caution with BYDAY patterns**: from-completion can produce surprising results:
  - The completion day never counts — even if the due time is hours away
  - Late completion skips the current day entirely (landed on next Wednesday instead of today's Friday)
  - Early completion brings the task back sooner than expected
  - INTERVAL ≥ 2 resets the week grid, potentially shifting by 14+ days vs catch-up

### Always set the anchor date explicitly
- If `basedOn` points to a date field that isn't set, OmniFocus will create it using completion date + default time
- This works but is rarely intentional and produces user-specific results (depends on their Settings)
- Warn the user; don't silently allow it

---

## Part 9: Untested Areas

The following have NOT been empirically verified and should not be treated as ground truth:

- **Monthly patterns**: `onDates: [1, 15]` and `on: {last: "friday"}` with from-completion. Expected to follow the same "skip ahead, then find next match" algorithm, but monthly has edge cases (month boundaries, varying month lengths) that could surprise.
- **Minutely frequency**: Untested. Hourly showed no time drift, but minutely rounding may behave differently.
- **Time drift at very fine granularity with large offsets**: All our hourly tests completed within a few hours of the due time. Completing a 2-hourly task 18 hours late might reveal drift behavior not visible in our tests.

---

## Methodology

- All experiments used `omnifocus-operator-2:add_tasks` to create tasks and `omnifocus-operator-2:get_task` to query results after completion.
- Task IDs persist across repetition completions — the same ID returns the new occurrence.
- Times verified against user's OmniFocus Settings → Dates & Times (screenshot confirmed: due=19:00, defer=08:00, planned=09:00 BST).
- Experiments conducted April 2–3, 2026, OmniFocus 4.7+, BST (UTC+1).

### Verification scorecard

| Claim | Status | Source | Notes |
|-------|--------|--------|-------|
| Time drift for from_completion | ❌ **DISPROVEN** | Deep research report | Time preserved at hourly, daily, and weekly granularity |
| From-completion: today never counts | ✅ **CONFIRMED** | Experiment Q1 | Day-level rounding — skips today even with 9+ hours remaining |
| Catch-up: checks exact time, not just day | ✅ **CONFIRMED** | Experiments Q2 + IV1 | Lands on today if time is future; skips if time has passed |
| Early completion date difference | ✅ **CONFIRMED** | Experiment EC1-3 | From-completion finds next BYDAY after completion; can return sooner |
| Late completion date difference | ✅ **CONFIRMED** | Part 3 BYDAY test | From-completion skips current day; catch-up lands on nearest future grid point |
| INTERVAL ≥ 2 grid reset | ✅ **CONFIRMED** | Experiment IV1-2 | 14-day divergence observed; from-completion resets the alternation grid |
| Skipped occs don't count against limits | ✅ **CONFIRMED** | Experiment Q4 | `end.occurrences` decremented by 1, not by number of skipped days |
| Catch-up preserves original time | ✅ **CONFIRMED** | Multiple experiments | But so does from-completion — not a differentiator |
| No time drift at hourly granularity | ✅ **CONFIRMED** | Experiment Q5 | Landed on original 2-hour grid, not completion_time + interval |
| Missing anchor uses creation date | ❌ **DISPROVEN** | Experiment 2 (cross-day) | Uses completion date + user's default time settings |
| Missing anchor creates the date | ✅ **CONFIRMED** | Experiment 1 | OmniFocus creates the anchor date from scratch; doesn't refuse or skip |
| Monthly from-completion behavior | ⬜ **UNTESTED** | — | Expected same algorithm but unverified |
