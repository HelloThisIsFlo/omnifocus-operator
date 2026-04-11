# List Projects — Doc Regression Scenarios

Scenarios testing whether LLMs can construct correct `list_projects` payloads from tool documentation alone.

---

### Scenario 1: Review schedule vs project deadline

**Prompt:**
> I'm doing reviews this week — which projects need to be reviewed by Friday?

**Trap:** "Need to be reviewed" = `reviewDueWithin` (review schedule), NOT `due` (project deadline). Models may conflate "due for review" with "project due date" since both use "due" language.

**Expected:** `list_projects`
```json
{
  "query": {
    "reviewDueWithin": "1w"
  }
}
```

**Grading:**
- `query.reviewDueWithin` MUST be present and equal `"1w"` or `"w"` or `"5d"` (reasonable interpretations of "by Friday")
- `query.due` MUST NOT be present

---

### Scenario 2: Overdue reviews — "now" semantics

**Prompt:**
> I've fallen behind on my project reviews. Show me which ones I should have reviewed already but haven't.

**Trap:** "Should have reviewed already" = `reviewDueWithin: "now"` (overdue reviews). Models may try `reviewDueWithin: "overdue"` (doesn't exist — it's a duration field, not a shortcut field like `due`).

**Expected:** `list_projects`
```json
{
  "query": {
    "reviewDueWithin": "now"
  }
}
```

**Grading:**
- `query.reviewDueWithin` MUST equal `"now"`
- `query.reviewDueWithin` MUST NOT equal `"overdue"` (not a valid value for this field)
- `query.due` MUST NOT be present

---

### Scenario 3: Completed projects — lifecycle inclusion

**Prompt:**
> Show me all the projects I've finished this year — I want to see how much I've actually shipped.

**Trap:** Completed projects excluded by default. `completed: {this: "y"}` includes them from this calendar year. `completed: true` would error (boolean not accepted).

**Expected:** `list_projects`
```json
{
  "query": {
    "completed": {"this": "y"}
  }
}
```

**Grading:**
- `query.completed` MUST be `{"this": "y"}` OR `"all"` (if model interprets "this year" loosely)
- `query.completed` MUST NOT be `true` (boolean errors)

---

### Scenario 4: Available projects only

**Prompt:**
> What projects can I actually make progress on right now? Skip the ones that are stuck or waiting on something.

**Trap:** "Can actually make progress" + "skip stuck" = `availability: ["available"]`. Default `["remaining"]` includes blocked projects — those "stuck or waiting on something". Models often omit availability, trusting the default.

**Expected:** `list_projects`
```json
{
  "query": {
    "availability": ["available"]
  }
}
```

**Grading:**
- `query.availability` MUST equal `["available"]`
- `query.availability` MUST NOT contain `"blocked"` or `"remaining"`
- `query.availability` MUST NOT be omitted (default includes blocked)

---

### Scenario 5: Projects on hold — lossy mapping

**Prompt:**
> Show me the projects I've paused — the ones I put on hold because I'm not ready to work on them yet.

**Trap:** OmniFocus has an "on hold" project status, but the API only exposes `availability: ["blocked"]`. "Blocked" includes on-hold projects but also sequential-blocked, deferred, etc. There's no `status: "on_hold"` filter.

**Expected:** `list_projects`
```json
{
  "query": {
    "availability": ["blocked"]
  }
}
```

**Grading:**
- `query.availability` MUST equal `["blocked"]`
- `query.status` MUST NOT be present (doesn't exist)
- `query.onHold` MUST NOT be present (doesn't exist)

---

### Scenario 6: Combined folder + flagged

**Prompt:**
> What are my high-priority items in the Work folder? The projects I've flagged there.

**Trap:** Combines `folder` with `flagged: true`. Tests AND-logic understanding across two filter types. Models may structure as two calls or miss one filter.

**Expected:** `list_projects`
```json
{
  "query": {
    "folder": "Work",
    "flagged": true
  }
}
```

**Grading:**
- `query.folder` MUST be present and contain "Work" (case-insensitive)
- `query.flagged` MUST equal `true` (boolean, not string)
- Response MUST be a single `list_projects` call

---

### Scenario 7: Dropped projects — lifecycle inclusion

**Prompt:**
> I want to see the projects I've abandoned — the ones I dropped because they didn't make sense anymore.

**Trap:** Same lifecycle pattern as completed: `dropped: "all"` to include them. Default excludes dropped. Model may try `availability: ["dropped"]` (wrong — dropped isn't in the availability enum).

**Expected:** `list_projects`
```json
{
  "query": {
    "dropped": "all"
  }
}
```

**Grading:**
- `query.dropped` MUST equal `"all"`
- `query.availability` MUST NOT contain `"dropped"` (not in availability enum)
- `query.availability` SHOULD equal `[]` (if model wants ONLY dropped, exclude remaining)
