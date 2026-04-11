# List Tasks — Doc Regression Scenarios

Scenarios testing whether LLMs can construct correct `list_tasks` payloads from tool documentation alone.

---

### Scenario 1: Calendar week vs rolling week

**Prompt:**
> What deadlines do I have this week? I need to see what's due Monday through Sunday so I can plan.

**Trap:** "This week" with "Monday through Sunday" = calendar-aligned `{this: "w"}`, not rolling `{last: "1w"}`. Models may default to the rolling form.

**Expected:** `list_tasks`
```json
{
  "query": {
    "due": {"this": "w"}
  }
}
```

**Grading:**
- `query.due` MUST be `{"this": "w"}`
- `query.due` MUST NOT be `{"last": "1w"}` or `{"last": "w"}`

---

### Scenario 2: Completed "all" with project filter

**Prompt:**
> Show me all the completed tasks in the Kitchen Remodel project. I want to see how much we've actually gotten done.

**Trap:** `completed: "all"` not `completed: true` (boolean errors). Also tests combining completed with a project filter.

**Expected:** `list_tasks`
```json
{
  "query": {
    "completed": "all",
    "project": "Kitchen Remodel",
    "availability": []
  }
}
```

**Grading:**
- `query.completed` MUST equal `"all"`
- `query.completed` MUST NOT be `true` or `"any"`
- `query.project` MUST be present and contain "Kitchen Remodel" (case-insensitive)
- `query.availability` SHOULD equal `[]` (exclude remaining tasks — "all completed" implies lifecycle-only)

---

### Scenario 3: Completed today — shortcut

**Prompt:**
> What did I get done today? I want to see everything I checked off.

**Trap:** `completed: "today"` is a dedicated shortcut. Agent might try `completed: {"this": "d"}` (valid but verbose), `completed: true`, or even a `modified: "today"` filter.

**Expected:** `list_tasks`
```json
{
  "query": {
    "completed": "today"
  }
}
```

**Grading:**
- `query.completed` MUST equal `"today"` OR `{"this": "d"}`
- `query.completed` MUST NOT be `true`
- `query.modified` MUST NOT be present

---

### Scenario 4: Completed in the last week — rolling + lifecycle-only

**Prompt:**
> Show me what I've completed in the last week. Only completed tasks, nothing else.

**Trap:** Two traps in one. (1) "Only completed, nothing else" = `availability: []` to suppress remaining tasks. Default availability `["remaining"]` would also show available+blocked tasks. Docs say: "Empty list [] = no remaining tasks (combine with completed/dropped filters for lifecycle-only results)." (2) "In the last week" = rolling `{last: "1w"}`, not calendar week.

**Expected:** `list_tasks`
```json
{
  "query": {
    "availability": [],
    "completed": {"last": "1w"}
  }
}
```

**Grading:**
- `query.completed` MUST be `{"last": "1w"}` or `{"last": "w"}`
- `query.availability` MUST equal `[]` (empty array)
- `query.availability` MUST NOT be omitted (default would include remaining tasks)

---

### Scenario 5: Dropped + available mix

**Prompt:**
> I need two things: show me my available tasks, and also pull up anything I dropped this past month — I want to see if I should revive any of them.

**Trap:** Two filter concerns in one call. `availability: ["available"]` restricts remaining tasks to available only. `dropped: {last: "1m"}` auto-includes dropped tasks from the last month. Agent might try adding "dropped" to availability (not in the enum) or think this requires two separate calls.

**Expected:** `list_tasks`
```json
{
  "query": {
    "availability": ["available"],
    "dropped": {"last": "1m"}
  }
}
```

**Grading:**
- `query.availability` MUST equal `["available"]`
- `query.dropped` MUST be `{"last": "1m"}` or `{"last": "m"}`
- `query.availability` MUST NOT contain `"dropped"`
- Response MUST be a single `list_tasks` call, not two separate calls

---

### Scenario 6: Everything that happened — completed + dropped

**Prompt:**
> Give me a recap of everything that happened in the last 3 days — tasks I finished and tasks I dropped.

**Trap:** Two lifecycle filters in one call. `completed: {last: "3d"}` auto-includes completed tasks. `dropped: {last: "3d"}` auto-includes dropped tasks. Default availability `["remaining"]` is fine — no need to explicitly change it. Agent might try to add "completed" or "dropped" to the availability array (not in the enum).

**Expected:** `list_tasks`
```json
{
  "query": {
    "completed": {"last": "3d"},
    "dropped": {"last": "3d"}
  }
}
```

**Grading:**
- `query.completed` MUST be `{"last": "3d"}`
- `query.dropped` MUST be `{"last": "3d"}`
- `query.availability` MUST NOT contain `"completed"` or `"dropped"`
- `query.availability` SHOULD NOT be present (default is fine)

---

### Scenario 7: Overdue — vague language

**Prompt:**
> I know I've dropped the ball on some things. Show me all the tasks where I'm late — stuff that should have been done already.

**Trap:** Vague "I'm late" / "should have been done already" = `due: "overdue"`. Agent might try a boolean `overdue: true`, a `completed` filter, or even `availability: ["blocked"]`.

**Expected:** `list_tasks`
```json
{
  "query": {
    "due": "overdue"
  }
}
```

**Grading:**
- `query.due` MUST equal `"overdue"` OR `{"before": "now"}`
- `query.completed` MUST NOT be present
- `query.dropped` MUST NOT be present

---

### Scenario 8: "This month" = calendar month

**Prompt:**
> It's January 29th and I'm doing my monthly review. Show me everything that's due this month.

**Trap:** "This month" in a monthly review = calendar month (Jan 1-31) = `{this: "m"}`. On the 29th, a rolling `{last: "1m"}` would reach back to Dec 29, which is wrong for a monthly review. Models may conflate "this month" with "last 30 days".

**Expected:** `list_tasks`
```json
{
  "query": {
    "due": {"this": "m"}
  }
}
```

**Grading:**
- `query.due` MUST be `{"this": "m"}` OR absolute bounds covering the calendar month (e.g., `{after: "2026-01-01", before: "2026-01-31"}`)
- `query.due` MUST NOT be `{"last": "1m"}` or `{"last": "m"}`
- `query.due` SHOULD be `{"this": "m"}` (shortcut preferred over absolute bounds)

---

### Scenario 9: Equivalent forms — shortcut vs absolute

**Prompt:**
> Find all tasks where the due date has already passed.

**Trap:** Both `due: "overdue"` (shortcut) and `due: {before: "now"}` (absolute) are correct. The shortcut is cleaner.

**Expected:** `list_tasks`

**Option A:**
```json
{
  "query": {
    "due": "overdue"
  }
}
```

**Option B:**
```json
{
  "query": {
    "due": {"before": "now"}
  }
}
```

**Grading:**
- `query.due` MUST equal `"overdue"` OR `{"before": "now"}`
- `query.due` SHOULD equal `"overdue"` (cleaner form preferred)

---

### Scenario 10: Absolute date range — both bounds inclusive

**Prompt:**
> Show me everything due in March — from March 1st through March 31st.

**Trap:** `{after: "2026-03-01", before: "2026-03-31"}` — both bounds inclusive, date-only is fine (resolves to start/end of day). Agent may add unnecessary time components like `T00:00:00` or `T23:59:59`, or may think one bound is exclusive.

**Expected:** `list_tasks`
```json
{
  "query": {
    "due": {"after": "2026-03-01", "before": "2026-03-31"}
  }
}
```

**Grading:**
- `query.due.after` MUST be `"2026-03-01"` (date-only acceptable) or an equivalent datetime on March 1
- `query.due.before` MUST be `"2026-03-31"` (date-only acceptable) or an equivalent datetime on March 31
- Both bounds MUST be present

---

### Scenario 11: Previous calendar week — standup context

**Prompt:**
> It's Tuesday morning and I'm prepping for standup. What did I get done last week? Just the completed stuff.

**Trap:** "Last week" on a Tuesday = the previous Monday-Sunday block, NOT rolling 7 days (which would include Monday+Tuesday of this week). No shorthand exists for "previous calendar week" — agent needs absolute bounds. `{last: "1w"}` is wrong (rolling). `{this: "w"}` is wrong (current week). "Just the completed stuff" = `availability: []`.

**Expected:** `list_tasks`
```json
{
  "query": {
    "availability": [],
    "completed": {"after": "2026-04-06", "before": "2026-04-12"}
  }
}
```

**Grading:**
- `query.completed` MUST use absolute bounds (`after`/`before`) covering the previous Monday through Sunday
- `query.completed` MUST NOT be `{"last": "1w"}` (rolling — would bleed into current week)
- `query.completed` MUST NOT be `{"this": "w"}` (current week, not previous)
- `query.availability` MUST equal `[]`

---

### Scenario 12: Blocked tasks — state not timing

**Prompt:**
> I want to see the tasks I can't move forward on right now — stuff that's stalled, waiting on something, or just not available yet.

**Trap:** "Can't move forward on" = availability: ["blocked"], NOT a defer filter. Availability covers all four blocking reasons (deferred, held project, sequential prerequisite, future dates); defer is timing-only (one of four).

**Expected:** `list_tasks`
```json
{
  "query": {
    "availability": ["blocked"]
  }
}
```

**Grading:**
- `query.availability` MUST equal `["blocked"]`
- `query.defer` MUST NOT be present
- `query.availability` MUST NOT contain `"available"` or `"remaining"`

---

### Scenario 13: Tags — OR logic in arrays

**Prompt:**
> I need to tackle some house stuff. Pull up anything I've tagged as Errands, Cleaning, and Groceries.

**Trap:** Tags use OR logic per docs. "Tagged as X, Y, and Z" uses "and" as a list conjunction (union) but models may parse as intersection. Array must contain all three names in a single call.

**Expected:** `list_tasks`
```json
{
  "query": {
    "tags": ["Errands", "Cleaning", "Groceries"]
  }
}
```

**Grading:**
- `query.tags` MUST be an array containing `"Errands"`, `"Cleaning"`, and `"Groceries"`
- Response MUST be a single `list_tasks` call, not multiple calls

---

### Scenario 14: Becoming available — defer timing not state

**Prompt:**
> I'm planning ahead for next week. What tasks are going to become workable in the next seven days? I want to see what's about to open up.

**Trap:** Timing question → defer: {next: "1w"}, NOT availability: ["blocked"]. Docs: "defer filter answers 'what becomes available when?' (timing only)." Blocked gives all blocked tasks regardless of when they unblock.

**Expected:** `list_tasks`
```json
{
  "query": {
    "defer": {"next": "1w"}
  }
}
```

**Grading:**
- `query.defer` MUST be `{"next": "1w"}`, `{"next": "w"}`, or `{"next": "7d"}`
- `query.availability` MUST NOT equal `["blocked"]`
- `query.availability` SHOULD NOT be present (default is fine)

---

### Scenario 15: Counting tasks — limit 0 for count only

**Prompt:**
> How many things am I behind on? I don't need the details, just a number.

**Trap:** "Behind on" = due: "overdue". "Just a number" = limit: 0 — returns {items: [], total: N} so the total gives the count without transferring task data. Models may fetch all items and count client-side, or use default limit 50 (wrong if >50).

**Expected:** `list_tasks`
```json
{
  "query": {
    "due": "overdue",
    "limit": 0
  }
}
```

**Grading:**
- `query.due` MUST equal `"overdue"` OR `{"before": "now"}`
- `query.limit` MUST equal `0`
- `query.limit` MUST NOT be `null` or omitted

---

### Scenario 16: Actionable tasks this week — available only

**Prompt:**
> What are the things I can actually pick up and work on that are due this week? Skip anything I'm waiting on or can't start yet.

**Trap:** "Can actually pick up" + "skip anything waiting on" = availability: ["available"], NOT default ["remaining"] which includes blocked. "Due this week" = due: {this: "w"} (calendar week). Model may omit availability, leaving blocked tasks in.

**Expected:** `list_tasks`
```json
{
  "query": {
    "availability": ["available"],
    "due": {"this": "w"}
  }
}
```

**Grading:**
- `query.availability` MUST equal `["available"]`
- `query.availability` MUST NOT contain `"blocked"` or `"remaining"`
- `query.due` MUST be `{"this": "w"}`

---

### Scenario 17: Inbox tasks — dedicated filter

**Prompt:**
> Show me what's sitting in my inbox — the stuff I haven't sorted into projects yet.

**Trap:** Two valid forms: inInbox: true (recommended, purpose-built) or project: "$inbox" (works but repurposes a name-resolution filter). Model should pick one, not both.

**Expected:** `list_tasks`

**Option A (recommended):**
```json
{
  "query": {
    "inInbox": true
  }
}
```

**Option B:**
```json
{
  "query": {
    "project": "$inbox"
  }
}
```

**Grading:**
- `query.inInbox` MUST equal `true` OR `query.project` MUST equal `"$inbox"`
- `query` MUST NOT contain both `inInbox` and `project` simultaneously
- `query.inInbox` SHOULD equal `true` (preferred form)

---

### Scenario 18: Full system audit — lifecycle inclusion

**Prompt:**
> I'm doing a full system audit. Show me every single task — active, completed, dropped, everything. The complete picture.

**Trap:** Need completed: "all" + dropped: "all" to include lifecycle states excluded by default. Default availability ["remaining"] already handles active tasks (available + blocked). Model may try availability: "all" (errors — not a valid enum value).

**Expected:** `list_tasks`
```json
{
  "query": {
    "completed": "all",
    "dropped": "all"
  }
}
```

**Grading:**
- `query.completed` MUST equal `"all"`
- `query.dropped` MUST equal `"all"`
- `query.availability` MUST NOT equal `"all"`, `["all"]`, or `[]` (empty list excludes active tasks)
- `query.availability` SHOULD NOT be present (default handles active tasks)
