# Add Tasks — Doc Regression Scenarios

Scenarios testing whether LLMs can construct correct `add_tasks` payloads from tool documentation alone.

---

### Scenario 1: All three dates — explicit mapping

**Prompt:**
> Create a task called "Kitchen renovation kickoff". I can't start until the permits come through on June 1st. I'm planning to work on it June 10th. And it absolutely must be done by June 15th — the contractor leaves town after that.

**Trap:** Three dates, three fields: "can't start until" = deferDate, "planning to work on" = plannedDate, "must be done by" = dueDate. Models often confuse deferDate and plannedDate.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Kitchen renovation kickoff",
    "deferDate": "2026-06-01T00:00:00Z",
    "plannedDate": "2026-06-10T00:00:00Z",
    "dueDate": "2026-06-15T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].name` MUST contain "Kitchen renovation" or "renovation kickoff"
- `items[0].deferDate` MUST be a date around June 1 2026
- `items[0].plannedDate` MUST be a date around June 10 2026
- `items[0].dueDate` MUST be a date around June 15 2026

---

### Scenario 2: "No point looking at this before then" = deferDate

**Prompt:**
> Add a task: "Order new furniture". The apartment won't be ready until September, so there's literally no point even looking at this before then.

**Trap:** "No point looking at this before then" = deferDate (hidden from views). NOT dueDate, NOT plannedDate.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Order new furniture",
    "deferDate": "2026-09-01T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].deferDate` MUST be a date in September 2026
- `items[0].dueDate` MUST NOT be present
- `items[0].plannedDate` MUST NOT be present

---

### Scenario 3: Intention without urgency = plannedDate

**Prompt:**
> Create a task "Organize photos from vacation". I'm thinking I'll get to it on June 1st, but honestly if I don't it's totally fine. No deadline.

**Trap:** "Thinking I'll get to it" + "no deadline" = plannedDate. Docs say plannedDate is "When you intend to work on this task. No urgency signal, no penalty for missing it."

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Organize photos from vacation",
    "plannedDate": "2026-06-01T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].plannedDate` MUST be a date in June 2026
- `items[0].dueDate` MUST NOT be present
- `items[0].deferDate` MUST NOT be present

---

### Scenario 4: Hard deadline = dueDate

**Prompt:**
> Add a task "File tax return" — it has to be done by April 15th, no exceptions, there are penalties if I miss it.

**Trap:** "Has to be done by" + "penalties" = hard deadline = dueDate. Straightforward, but tests that the model doesn't use plannedDate for an actual deadline.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "File tax return",
    "dueDate": "2026-04-15T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].dueDate` MUST be a date around April 15 2026
- `items[0].plannedDate` MUST NOT be present

---

### Scenario 5: Computed deferDate from context

**Prompt:**
> Create a task: "Renew apartment lease". My lease expires end of August and the landlord said I need to start the renewal process at least 2 months before it expires. So I should get on this when the time comes.

**Trap:** Agent must COMPUTE the deferDate: 2 months before end of August ≈ late June. The dueDate is end of August (lease expiry). Neither date is stated explicitly — both require inference.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Renew apartment lease",
    "deferDate": "2026-06-30T00:00:00Z",
    "dueDate": "2026-08-31T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].deferDate` MUST be a date in June 2026 (approximately 2 months before end of August)
- `items[0].dueDate` MUST be a date in late August 2026
- `items[0].plannedDate` MUST NOT be present (or if present, it's in addition to deferDate — not a substitute)

---

### Scenario 6: "Like to get to it by Friday" — NOT a deadline

**Prompt:**
> New task: "Clean out garage". I'd like to get to it by this Friday but it's really not urgent at all, just whenever I have the energy.

**Trap:** "Like to get to it" + "not urgent" + "whenever" = plannedDate. Despite "by this Friday" sounding like a deadline, the context makes clear it's an intention. Docs: plannedDate = "No urgency signal, no penalty for missing it."

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Clean out garage",
    "plannedDate": "2026-04-03T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].plannedDate` MUST be a date in April 2026 (this Friday)
- `items[0].dueDate` MUST NOT be present

---

### Scenario 7: Buried deadline in rambling message

**Prompt:**
> Hey so I was talking to my neighbor and they mentioned this community event thing happening next month, sounds like fun honestly. Oh wait — I need to submit the sign-up form for the neighborhood barbecue, that's due May 20th.

**Trap:** The actual task (submit sign-up form) and deadline (May 20th) are buried after rambling. Model must extract the task name and dueDate from context.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Submit sign-up form for neighborhood barbecue",
    "dueDate": "2026-05-20T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].name` MUST relate to sign-up form or barbecue
- `items[0].dueDate` MUST be a date around May 20 2026

---

### Scenario 8: Every 3 days from completion, defer anchor

**Prompt:**
> Add a repeating task "Water the plants". Every 3 days, but the next one should only show up after I finish the current one. Anchor it to the defer date. Give it a due date of June 1st to start.

**Trap:** All 3 root fields required for creation. schedule: from_completion (next appears after completion). basedOn: defer_date. frequency: daily with interval 3 (not "every 3rd day of week").

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Water the plants",
    "dueDate": "2026-06-01T00:00:00Z",
    "repetitionRule": {
      "frequency": { "type": "daily", "interval": 3 },
      "schedule": "from_completion",
      "basedOn": "defer_date"
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.type` MUST be "daily"
- `items[0].repetitionRule.frequency.interval` MUST be 3
- `items[0].repetitionRule.schedule` MUST be "from_completion"
- `items[0].repetitionRule.basedOn` MUST be "defer_date"

---

### Scenario 9: Biweekly on specific days, stop after 10

**Prompt:**
> Create "Team standup notes" — happens every 2 weeks on Monday and Wednesday. Regular schedule anchored to the due date. Stop repeating after 10 occurrences. Due date June 1st.

**Trap:** Weekly type with interval 2 (biweekly). End condition by occurrences. All 3 root fields.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Team standup notes",
    "dueDate": "2026-06-01T00:00:00Z",
    "repetitionRule": {
      "frequency": { "type": "weekly", "interval": 2, "onDays": ["MO", "WE"] },
      "schedule": "regularly",
      "basedOn": "due_date",
      "end": { "occurrences": 10 }
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.type` MUST be "weekly"
- `items[0].repetitionRule.frequency.interval` MUST be 2
- `items[0].repetitionRule.frequency.onDays` MUST contain "MO" and "WE"
- `items[0].repetitionRule.schedule` MUST be "regularly"
- `items[0].repetitionRule.basedOn` MUST be "due_date"
- `items[0].repetitionRule.end.occurrences` MUST be 10

---

### Scenario 10: Last Friday of month

**Prompt:**
> Add "Monthly expense report" — due the last Friday of every month. Regular schedule, anchor to due date. Start with a due date of June 1st.

**Trap:** Monthly with `on: {"last": "friday"}`, NOT `onDates`. The `on` field uses ordinal+day format.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Monthly expense report",
    "dueDate": "2026-06-01T00:00:00Z",
    "repetitionRule": {
      "frequency": { "type": "monthly", "on": { "last": "friday" } },
      "schedule": "regularly",
      "basedOn": "due_date"
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.type` MUST be "monthly"
- `items[0].repetitionRule.frequency.on` MUST equal `{"last": "friday"}`
- `items[0].repetitionRule.frequency.onDates` MUST NOT be present

---

### Scenario 11: Monthly on specific dates (onDates, not on)

**Prompt:**
> Create "Invoice clients" — it needs to go out on the 1st and 15th of each month, plus the last day of the month. Regular schedule, due date anchor. Due date June 1st.

**Trap:** `onDates: [1, 15, -1]` — the "-1" means last day of month. NOT the `on` field (that's for weekday patterns). Models sometimes confuse `on` and `onDates`.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Invoice clients",
    "dueDate": "2026-06-01T00:00:00Z",
    "repetitionRule": {
      "frequency": { "type": "monthly", "onDates": [1, 15, -1] },
      "schedule": "regularly",
      "basedOn": "due_date"
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.onDates` MUST contain 1, 15, and -1
- `items[0].repetitionRule.frequency.on` MUST NOT be present

---

### Scenario 12: Yearly with planned_date anchor

**Prompt:**
> Add "Review insurance policy". Once a year. Repeat based on when I plan to do it, regular schedule. Planned date June 1st.

**Trap:** type: yearly, basedOn: planned_date (unusual anchor choice). Models might default to due_date.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Review insurance policy",
    "plannedDate": "2026-06-01T00:00:00Z",
    "repetitionRule": {
      "frequency": { "type": "yearly" },
      "schedule": "regularly",
      "basedOn": "planned_date"
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.type` MUST be "yearly"
- `items[0].repetitionRule.basedOn` MUST be "planned_date"
- `items[0].repetitionRule.schedule` MUST be "regularly"
- `items[0].plannedDate` MUST be present (anchor date must exist)

---

### Scenario 13: Daily with end-by-date

**Prompt:**
> Create "Take antibiotics" — every day until June 30th. Regular schedule, anchored to due date. Due tomorrow.

**Trap:** End condition with date (not occurrences). All 3 root fields required.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Take antibiotics",
    "dueDate": "2026-04-02T00:00:00Z",
    "repetitionRule": {
      "frequency": { "type": "daily" },
      "schedule": "regularly",
      "basedOn": "due_date",
      "end": { "date": "2026-06-30T00:00:00Z" }
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.type` MUST be "daily"
- `items[0].repetitionRule.end.date` MUST be a date in June 2026
- `items[0].repetitionRule.end.occurrences` MUST NOT be present
- `items[0].dueDate` MUST be a date in April 2026 (tomorrow)

---

### Scenario 14: Buried estimatedMinutes in prose

**Prompt:**
> Add a task: "Sign new lease agreement". I need to get this done by end of May. The property manager said the whole signing process usually takes about 45 minutes with all the reading and paperwork.

**Trap:** "Takes about 45 minutes" buried in conversational context = estimatedMinutes: 45. Models often ignore duration mentions that aren't explicitly labeled.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Sign new lease agreement",
    "dueDate": "2026-05-31T00:00:00Z",
    "estimatedMinutes": 45
  }]
}
```

**Grading:**
- `items[0].estimatedMinutes` MUST be 45
- `items[0].dueDate` MUST be a date in May 2026

---

### Scenario 15: "Cannot forget" = flagged

**Prompt:**
> Create a task "Buy anniversary gift". Our anniversary is April 20th. This is really important — I absolutely cannot forget this one, mark it so it stands out.

**Trap:** "Cannot forget" + "mark it so it stands out" = flagged: true. The flag is the mechanism for making tasks stand out in OmniFocus.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Buy anniversary gift",
    "dueDate": "2026-04-20T00:00:00Z",
    "flagged": true
  }]
}
```

**Grading:**
- `items[0].flagged` MUST be true
- `items[0].dueDate` MUST be a date around April 20 2026

---

### Scenario 16: Conversational context → note field

**Prompt:**
> New task: "Call dentist". Here's the thing — I need to specifically ask about the crown they fitted last time because it's been feeling loose, and also check if they take our new insurance provider. Their number is 555-0123.

**Trap:** The conversational context (crown concern, insurance question, phone number) should go in the `note` field. This isn't the task name — it's supporting information.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Call dentist",
    "note": "Ask about the crown (feeling loose). Check if they take new insurance. Number: 555-0123."
  }]
}
```

**Grading:**
- `items[0].name` MUST be about calling the dentist (short, actionable)
- `items[0].note` MUST be present
- `items[0].note` MUST contain reference to the crown or insurance or phone number

---

### Scenario 17: Buried tags + duration at end of rambling

**Prompt:**
> I need to prepare the Q3 board presentation. The board meeting is July 15th so it needs to be ready by then. I figure it'll take me a couple hours to put together with all the charts and data. Oh and tag it Work and Presentations.

**Trap:** Three buried requirements: (1) dueDate from "ready by July 15th", (2) estimatedMinutes from "couple hours" = 120, (3) tags buried at the end of the message. Models often miss the duration conversion (hours→minutes).

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Prepare Q3 board presentation",
    "dueDate": "2026-07-15T00:00:00Z",
    "estimatedMinutes": 120,
    "tags": ["Work", "Presentations"]
  }]
}
```

**Grading:**
- `items[0].tags` MUST contain "Work" and "Presentations"
- `items[0].dueDate` MUST be a date around July 15 2026
- `items[0].estimatedMinutes` MUST be 120

---

### Scenario 18: Create + move to top = multi-tool

**Prompt:**
> Create a task "Urgent security patch" in project pR4oJ9 and put it at the very top of the project — it needs to be the first thing I see.

**Trap:** add_tasks can set `parent` but has NO positioning control. To put it at the top (beginning), a second edit_tasks call is needed with actions.move.beginning. Models often try to do it in one call.

**Expected:** `add_tasks` then `edit_tasks`

Call 1:
```json
{
  "items": [{
    "name": "Urgent security patch",
    "parent": "pR4oJ9"
  }]
}
```

Call 2 (using the ID returned from call 1):
```json
{
  "items": [{
    "id": "{id from call 1}",
    "actions": {
      "move": { "beginning": "pR4oJ9" }
    }
  }]
}
```

**Grading:**
- Call 1: `items[0].parent` MUST be "pR4oJ9"
- Call 1: `items[0].name` MUST contain "security patch"
- Call 2: `items[0].actions.move.beginning` MUST be "pR4oJ9"
- Model MUST indicate two separate tool calls are needed

---

### Scenario 19: Create directly in a project

**Prompt:**
> Add "Design mockups" as a task in project pR4oJ9.

**Trap:** Simple parent field usage. Test that the model knows `parent` accepts project IDs.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Design mockups",
    "parent": "pR4oJ9"
  }]
}
```

**Grading:**
- `items[0].parent` MUST be "pR4oJ9"
- `items[0].name` MUST be "Design mockups" or equivalent

---

### Scenario 20: Create as subtask of another task

**Prompt:**
> I have a task tK3mN7 for the kitchen renovation. Add a subtask under it called "Choose countertop material".

**Trap:** Parent accepts TASK IDs too (not just project IDs). The description says "Project or task ID to place this task under."

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Choose countertop material",
    "parent": "tK3mN7"
  }]
}
```

**Grading:**
- `items[0].parent` MUST be "tK3mN7"
- `items[0].name` MUST contain "countertop"

---

### Scenario 21: Create + position before sibling = multi-tool

**Prompt:**
> Add a task "Daily standup prep" to project pR4oJ9, and position it right before task tX5cZ8 in the list.

**Trap:** add_tasks has no positioning. Need two calls: add_tasks with parent, then edit_tasks with actions.move.before.

**Expected:** `add_tasks` then `edit_tasks`

Call 1:
```json
{
  "items": [{
    "name": "Daily standup prep",
    "parent": "pR4oJ9"
  }]
}
```

Call 2 (using the ID returned from call 1):
```json
{
  "items": [{
    "id": "{id from call 1}",
    "actions": {
      "move": { "before": "tX5cZ8" }
    }
  }]
}
```

**Grading:**
- Call 1: `items[0].parent` MUST be "pR4oJ9"
- Call 2: `items[0].actions.move.before` MUST be "tX5cZ8"
- Model MUST indicate two separate tool calls are needed

---

### Scenario 22: Tags on creation — flat array, not actions.tags

**Prompt:**
> Create "Research flights" with tags Travel and Personal. Due May 30th.

**Trap:** add_tasks uses a flat `tags` array in the item, NOT `actions.tags` (that's edit_tasks only). Models that have seen edit_tasks might use the wrong structure.

**Expected:** `add_tasks`
```json
{
  "items": [{
    "name": "Research flights",
    "dueDate": "2026-05-30T00:00:00Z",
    "tags": ["Travel", "Personal"]
  }]
}
```

**Grading:**
- `items[0].tags` MUST be an array containing "Travel" and "Personal"
- `items[0].actions` MUST NOT be present
