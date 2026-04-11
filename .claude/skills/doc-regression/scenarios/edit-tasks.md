# Edit Tasks — Doc Regression Scenarios

Scenarios testing whether LLMs can construct correct `edit_tasks` payloads from tool documentation alone.

---

### Scenario 1: Surgical null vs omit vs value

**Prompt:**
> For task oRx3bL, I added some notes yesterday that are totally wrong — delete them. Also unmark it as flagged, and I'm planning to work on it April 15th. Leave the time estimate as is.

**Trap:** Four fields, four different patch semantics: note=null (clear), flagged=false (set value), plannedDate=value (set), estimatedMinutes must be OMITTED (not null, not a value — "leave as is" means don't touch). Models often set estimatedMinutes to null (which would erase it).

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "oRx3bL",
    "note": null,
    "flagged": false,
    "plannedDate": "2026-04-15T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].note` MUST be null
- `items[0].flagged` MUST be false
- `items[0].plannedDate` MUST be a date in April 2026
- `items[0].estimatedMinutes` MUST NOT be present
- `items[0].dueDate` MUST NOT be present
- `items[0].deferDate` MUST NOT be present

---

### Scenario 2: Mass clear

**Prompt:**
> Task jK9mNp — strip it completely. Remove its due date, defer date, planned date, notes, time estimate, flag, and all tags. I want it totally clean.

**Trap:** Every clearable field must be null. Flagged is set to false (not null — it's a boolean). Tags require actions.tags.replace with null or []. Models sometimes forget one of the fields or use the wrong clear mechanism for tags.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "jK9mNp",
    "dueDate": null,
    "deferDate": null,
    "plannedDate": null,
    "note": null,
    "estimatedMinutes": null,
    "flagged": false,
    "actions": {
      "tags": { "replace": null }
    }
  }]
}
```

**Grading:**
- `items[0].dueDate` MUST be null
- `items[0].deferDate` MUST be null
- `items[0].plannedDate` MUST be null
- `items[0].note` MUST be null
- `items[0].estimatedMinutes` MUST be null
- `items[0].flagged` MUST be false
- `items[0].actions.tags.replace` MUST be null or empty array
- `items[0].actions.tags.add` MUST NOT be present

---

### Scenario 3: Minimal edit — nothing extra

**Prompt:**
> Flag task qW2eR4.

**Trap:** Just one field. Models sometimes add unnecessary fields (name, note, etc.) or wrap in extra structure. The payload should be as minimal as possible.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "qW2eR4",
    "flagged": true
  }]
}
```

**Grading:**
- `items[0].flagged` MUST be true
- `items[0].id` MUST be "qW2eR4"
- `items[0].dueDate` MUST NOT be present
- `items[0].note` MUST NOT be present
- `items[0].name` MUST NOT be present

---

### Scenario 4: "Remove it" ambiguity — clear field, don't delete task

**Prompt:**
> Task tY5uI8 — turns out there's no real deadline for this after all. Remove it.

**Trap:** "Remove it" refers to the deadline (mentioned in previous sentence), not the task itself. The model must set dueDate: null, NOT use actions.lifecycle: "drop" or "complete".

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "tY5uI8",
    "dueDate": null
  }]
}
```

**Grading:**
- `items[0].dueDate` MUST be null
- `items[0].actions` MUST NOT be present (no lifecycle, no move)

---

### Scenario 5: Hide from lists = deferDate

**Prompt:**
> I keep seeing task pL3kJ7 and it's stressing me out. Get it out of my face — I don't want to see it or think about it until May 1st.

**Trap:** "Don't want to see it" = hidden from views = deferDate. NOT plannedDate (that's for intention, doesn't hide anything). The tool description explicitly says deferDate means "Hidden from most views until then."

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "pL3kJ7",
    "deferDate": "2026-05-01T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].deferDate` MUST be a date in May 2026
- `items[0].plannedDate` MUST NOT be present
- `items[0].dueDate` MUST NOT be present

---

### Scenario 6: Intention without urgency = plannedDate

**Prompt:**
> I'm thinking I'll work on task mN4bV6 next Tuesday. No rush at all, just want to remember when I was planning to get to it.

**Trap:** "planning to get to it" + "no rush" = plannedDate. The tool description says plannedDate is "When you intend to work on this task. No urgency signal." Models often default to dueDate.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "mN4bV6",
    "plannedDate": "2026-04-07T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].plannedDate` MUST be a date in April 2026
- `items[0].dueDate` MUST NOT be present
- `items[0].deferDate` MUST NOT be present

---

### Scenario 7: Three dates from context clues

**Prompt:**
> Task xC8vB2 — here's the deal: the contractor said they can't deliver the materials until June 1st, so I literally can't start before then. I want to plan on tackling it around June 10th, and the whole thing absolutely has to be wrapped up by June 15th or we lose the deposit.

**Trap:** Three different dates, three different semantic meanings: "can't start before" = deferDate, "plan on tackling" = plannedDate, "absolutely has to be done" = dueDate. Model must map each phrase to the correct field.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "xC8vB2",
    "deferDate": "2026-06-01T00:00:00Z",
    "plannedDate": "2026-06-10T00:00:00Z",
    "dueDate": "2026-06-15T00:00:00Z"
  }]
}
```

**Grading:**
- `items[0].deferDate` MUST be a date around June 1 2026
- `items[0].plannedDate` MUST be a date around June 10 2026
- `items[0].dueDate` MUST be a date around June 15 2026

---

### Scenario 8: Change interval only — type inferred

**Prompt:**
> Task rT6yU1 repeats on some schedule — I don't remember the details. Just change the interval to every 5 instead of whatever it is now. Don't touch anything else about the repetition.

**Trap:** Only frequency.interval should be sent. Type is inferred from the existing rule (docs: "frequency.type can be omitted (inferred from existing rule)"). Model should NOT send type, schedule, or basedOn.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "rT6yU1",
    "repetitionRule": {
      "frequency": { "interval": 5 }
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.interval` MUST be 5
- `items[0].repetitionRule.frequency.type` MUST NOT be present
- `items[0].repetitionRule.schedule` MUST NOT be present
- `items[0].repetitionRule.basedOn` MUST NOT be present

---

### Scenario 9: Add days to weekly — full array replacement

**Prompt:**
> Task wQ9eR3 currently repeats every week on Monday, Tuesday, and Wednesday. I want to add Thursday and Friday to that as well.

**Trap:** onDays is FULL REPLACEMENT, not additive. The model must send all 5 days ["MO","TU","WE","TH","FR"], not just the new ones ["TH","FR"]. This is the most common mistake — models treat it like a tag add operation.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "wQ9eR3",
    "repetitionRule": {
      "frequency": { "onDays": ["MO", "TU", "WE", "TH", "FR"] }
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.onDays` MUST contain all 5 days: MO, TU, WE, TH, FR
- `items[0].repetitionRule.frequency.onDays` MUST NOT contain only TH and FR (partial = fail)

---

### Scenario 10: Type change — interval must be re-sent

**Prompt:**
> Task aS2dF5 repeats every 2 days right now. Change it to every 2 weeks on Mondays instead.

**Trap:** Changing frequency type triggers FULL REPLACEMENT with creation defaults (docs: "Different type: full replacement with creation defaults"). The creation default for interval is 1. So interval=2 must be explicitly re-sent or it will reset to 1. This is the subtlest trap in the suite.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "aS2dF5",
    "repetitionRule": {
      "frequency": {
        "type": "weekly",
        "interval": 2,
        "onDays": ["MO"]
      }
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.type` MUST be "weekly"
- `items[0].repetitionRule.frequency.interval` MUST be 2 (not omitted, not 1)
- `items[0].repetitionRule.frequency.onDays` MUST contain "MO"

---

### Scenario 11: Monthly onDates to on pattern

**Prompt:**
> Task gH4jK6 repeats on the 1st and 15th of each month. Actually, change that to the last Friday of every month instead.

**Trap:** Setting `on` auto-clears `onDates` (they're mutually exclusive). The model just needs to send the new `on` value — it doesn't need to explicitly null out `onDates`.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "gH4jK6",
    "repetitionRule": {
      "frequency": {
        "on": { "last": "friday" }
      }
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.on` MUST equal `{"last": "friday"}`
- `items[0].repetitionRule.frequency.type` SHOULD NOT be present (same type, omit to preserve)

---

### Scenario 12: Clear repetition rule entirely

**Prompt:**
> Task zX7cV9 repeats but I don't want it to anymore. Make it a one-time thing.

**Trap:** repetitionRule must be set to null at the root level. Not an empty object, not omitted.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "zX7cV9",
    "repetitionRule": null
  }]
}
```

**Grading:**
- `items[0].repetitionRule` MUST be null (not omitted, not empty object)

---

### Scenario 13: Add rule to task with no existing rule

**Prompt:**
> Make task bN5mL8 repeat daily. Regular schedule, anchor to the due date.

**Trap:** When there's no existing rule, ALL THREE root fields are required (frequency, schedule, basedOn). The docs say "Task has no existing rule: all three root fields required." Models sometimes omit schedule or basedOn.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "bN5mL8",
    "repetitionRule": {
      "frequency": { "type": "daily" },
      "schedule": "regularly",
      "basedOn": "due_date"
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency` MUST be present with type "daily"
- `items[0].repetitionRule.schedule` MUST be "regularly"
- `items[0].repetitionRule.basedOn` MUST be "due_date"

---

### Scenario 14: Change only schedule — rest preserved

**Prompt:**
> Task yU1iO3 has some complex repetition setup. I just want to change one thing: make it repeat from when I complete it, instead of on a fixed schedule. Don't touch anything else about the rule.

**Trap:** Only schedule field needed when task has existing rule (docs: "Task has existing rule: omitted root fields are preserved"). Model should NOT send frequency or basedOn.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "yU1iO3",
    "repetitionRule": {
      "schedule": "from_completion"
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.schedule` MUST be "from_completion"
- `items[0].repetitionRule.frequency` MUST NOT be present
- `items[0].repetitionRule.basedOn` MUST NOT be present

---

### Scenario 15: Change only basedOn

**Prompt:**
> Task eW3rT5 repeats anchored to the due date. Switch the anchor to the planned date instead. Nothing else about the repetition changes.

**Trap:** Only basedOn needed. Same logic as scenario 14 — existing rule means omitted fields are preserved.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "eW3rT5",
    "repetitionRule": {
      "basedOn": "planned_date"
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.basedOn` MUST be "planned_date"
- `items[0].repetitionRule.frequency` MUST NOT be present
- `items[0].repetitionRule.schedule` MUST NOT be present

---

### Scenario 16: Tag wipe and replace

**Prompt:**
> Task hJ6kL8 has a bunch of tags from before. Wipe them all and just tag it Urgent and Work.

**Trap:** This is the `replace` mode under actions.tags. Model must NOT use add/remove (that would keep existing tags).

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "hJ6kL8",
    "actions": {
      "tags": { "replace": ["Urgent", "Work"] }
    }
  }]
}
```

**Grading:**
- `items[0].actions.tags.replace` MUST contain "Urgent" and "Work"
- `items[0].actions.tags.add` MUST NOT be present
- `items[0].actions.tags.remove` MUST NOT be present

---

### Scenario 17: Add + remove tags, keep rest

**Prompt:**
> On task fD4sA7, add the Urgent tag and take off Low Priority. Keep everything else it's tagged with.

**Trap:** "Keep everything else" = add/remove mode, NOT replace. Replace would wipe other existing tags. The modes are incompatible — docs say "replace is standalone. add/remove are combinable with each other but not with replace."

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "fD4sA7",
    "actions": {
      "tags": {
        "add": ["Urgent"],
        "remove": ["Low Priority"]
      }
    }
  }]
}
```

**Grading:**
- `items[0].actions.tags.add` MUST contain "Urgent"
- `items[0].actions.tags.remove` MUST contain "Low Priority"
- `items[0].actions.tags.replace` MUST NOT be present

---

### Scenario 18: Remove all tags

**Prompt:**
> Clear all tags from task pO9iU2. Every single one.

**Trap:** Use replace with null or [] to clear all tags.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "pO9iU2",
    "actions": {
      "tags": { "replace": null }
    }
  }]
}
```

**Grading:**
- `items[0].actions.tags.replace` MUST be null or empty array
- `items[0].actions.tags.remove` MUST NOT be present

---

### Scenario 19: Move before a sibling

**Prompt:**
> I need task lK2jH5 right before task mN8bV4 in the list.

**Trap:** actions.move.before with sibling ID. Not beginning/ending (those target containers).

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "lK2jH5",
    "actions": {
      "move": { "before": "mN8bV4" }
    }
  }]
}
```

**Grading:**
- `items[0].actions.move.before` MUST be "mN8bV4"
- `items[0].actions.move.beginning` MUST NOT be present
- `items[0].actions.move.ending` MUST NOT be present

---

### Scenario 20: Move to inbox — $inbox sentinel

**Prompt:**
> Pull task qW5eR7 out of its project and put it back in the inbox.

**Trap:** Inbox uses the sentinel string "$inbox", not a bare "inbox" or null. Docs: "Container to move into (project name/ID, task name/ID, or '$inbox')." Models sometimes write `"ending": "inbox"` (missing the $) or `"ending": null`.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "qW5eR7",
    "actions": {
      "move": { "ending": "$inbox" }
    }
  }]
}
```

**Grading:**
- `items[0].actions.move` MUST have `ending: "$inbox"` or `beginning: "$inbox"`
- `items[0].actions.move.ending` MUST be the string "$inbox" (not "inbox", not null)

---

### Scenario 21: Move to top of project

**Prompt:**
> Move task tY8uI1 to the very top of project pR4oJ9.

**Trap:** "Very top" = beginning, not ending. With the project ID as value.

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "tY8uI1",
    "actions": {
      "move": { "beginning": "pR4oJ9" }
    }
  }]
}
```

**Grading:**
- `items[0].actions.move.beginning` MUST be "pR4oJ9"
- `items[0].actions.move.ending` MUST NOT be present

---

### Scenario 22: Drop, not complete — "skip without credit"

**Prompt:**
> I'm not going to do task vB3nM6. Skip it, I don't want credit for completing it.

**Trap:** "Skip without credit" = drop, not complete. The description says drop "skips/cancels the task without completing it."

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "vB3nM6",
    "actions": {
      "lifecycle": "drop"
    }
  }]
}
```

**Grading:**
- `items[0].actions.lifecycle` MUST be "drop"
- `items[0].actions.lifecycle` MUST NOT be "complete"

---

### Scenario 23: Mega combo — 6 concerns in one edit

**Prompt:**
> OK here's a bunch of changes for task dF6gH2. It should now repeat every 2 weeks on Mondays and Fridays, regular schedule, anchored to the due date. Add the Review tag and get rid of the Draft tag. The real deadline is July 31st. Put a note on it saying "Needs sign-off from legal before publishing." I think it'll take about 90 minutes. And move it to the top of project pX5cZ8.

**Trap:** Six different concerns: (1) repetition rule with all 3 root fields (new rule), (2) tag add/remove, (3) dueDate, (4) note, (5) estimatedMinutes, (6) move to beginning. All in one call. Model must use correct modes for each (add/remove for tags, not replace; beginning for move, not ending).

**Expected:** `edit_tasks`
```json
{
  "items": [{
    "id": "dF6gH2",
    "dueDate": "2026-07-31T00:00:00Z",
    "note": "Needs sign-off from legal before publishing.",
    "estimatedMinutes": 90,
    "repetitionRule": {
      "frequency": { "type": "weekly", "interval": 2, "onDays": ["MO", "FR"] },
      "schedule": "regularly",
      "basedOn": "due_date"
    },
    "actions": {
      "tags": { "add": ["Review"], "remove": ["Draft"] },
      "move": { "beginning": "pX5cZ8" }
    }
  }]
}
```

**Grading:**
- `items[0].repetitionRule.frequency.type` MUST be "weekly"
- `items[0].repetitionRule.frequency.interval` MUST be 2
- `items[0].repetitionRule.frequency.onDays` MUST contain "MO" and "FR"
- `items[0].repetitionRule.schedule` MUST be "regularly"
- `items[0].repetitionRule.basedOn` MUST be "due_date"
- `items[0].dueDate` MUST be a date in July 2026
- `items[0].note` MUST contain "sign-off" or "legal"
- `items[0].estimatedMinutes` MUST be 90
- `items[0].actions.tags.add` MUST contain "Review"
- `items[0].actions.tags.remove` MUST contain "Draft"
- `items[0].actions.tags.replace` MUST NOT be present
- `items[0].actions.move.beginning` MUST be "pX5cZ8"
