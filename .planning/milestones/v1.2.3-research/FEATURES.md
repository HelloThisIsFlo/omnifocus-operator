# Feature Landscape: Repetition Rule Write Support (v1.2.3)

**Domain:** Structured recurrence rule model + write support for OmniFocus MCP server
**Researched:** 2026-03-27
**Overall confidence:** HIGH -- OmniJS API fully documented in spike, RRULE parser/builder validated with 79 tests, existing codebase patterns well-established

## Table Stakes

Features agents expect when a task management API supports repetition rules. Missing = the feature feels half-baked or forces agents to work around limitations.

| Feature | Why Expected | Complexity | Dependencies |
|---------|-------------|------------|--------------|
| Structured frequency model (not raw RRULE strings) | Every modern API abstracts RRULE away. Todoist uses natural language, Microsoft Graph uses typed `recurrencePattern` with `type` discriminator. Agents shouldn't need to construct `FREQ=WEEKLY;BYDAY=MO,WE,FR` | Med | RRULE parser/builder utilities |
| Create task with repetition rule | Can't call repetition "supported" if you can only set it on existing tasks | Med | Frequency model, validation, bridge handler |
| Edit existing repetition rule | Modify frequency, interval, schedule type, etc. without respecifying the entire rule | Med-High | Current-state read, merge logic, validation |
| Remove repetition rule | `repetitionRule: null` clears it. Standard pattern across all APIs | Low | Bridge handler for `task.repetitionRule = null` |
| All 3 schedule modes | `regularly`, `regularly_with_catch_up`, `from_completion` -- OmniFocus supports all three, agents need all three | Low | Enum + bridge mapping |
| All 3 anchor dates | `due_date`, `defer_date`, `planned_date` -- already in the read model as enums | Low | Existing enums |
| Symmetric read/write model | Same shape for reads and writes. Microsoft Graph does this with `patternedRecurrence`. Todoist does NOT (read-only `is_recurring` + natural language write), and it's a pain point | Med | Read model rewrite from ruleString to structured fields |
| Type-specific validation | Reject `onDays` on a `daily` frequency, require `on` for `monthly_day_of_week`. Microsoft Graph returns 400 for wrong-type fields | Med | Pydantic discriminated union or model validators |
| Educational error messages | Consistent with existing patterns. "You sent `onDays` but this frequency type is `daily`. onDays is only valid for `weekly_on_days`." | Low | Existing agent_messages pattern |

## Differentiators

Features that go beyond what most task management APIs offer. Not expected, but significantly improve the agent experience.

| Feature | Value Proposition | Complexity | Dependencies |
|---------|-------------------|------------|--------------|
| Partial update within frequency type | Change `interval` from 1 to 2 on a weekly rule without re-sending `onDays`. Microsoft Graph REQUIRES all fields for the type. OmniFocus Operator can do better because the service layer reads current state and merges | Med-High | Current task state read, merge logic per type |
| No-op detection for repetition changes | "The task already repeats weekly on Monday. No changes applied." Consistent with existing edit_tasks no-op pattern | Med | Current-state comparison, warning messages |
| Three-way lifecycle (`null` / omit / value) | UNSET = no change, `null` = remove rule, value = set/modify. Already the codebase pattern for dates. Agents familiar with edit_tasks already know this | Low | Existing PatchOrClear pattern |
| End condition support | By date, by occurrence count, or no end. Two of three task APIs surveyed don't expose end conditions through their API | Low-Med | RRULE UNTIL/COUNT, Pydantic "exactly one key" pattern |
| `monthly_day_of_week` English-like syntax | `"on": {"second": "tuesday"}` reads like English. Compare to Microsoft Graph's `{"index": "second", "daysOfWeek": ["tuesday"]}` or raw RRULE's `BYDAY=TU;BYSETPOS=2` | Low | Pydantic model with exactly-one-key validator |
| Type-change detection with clear error | Changing from `weekly` to `monthly` requires sending the complete new frequency object. Instead of silently producing garbage, error says exactly what to do | Low | Type comparison + educational error |

## Anti-Features

Features to explicitly NOT build. Either wrong scope, wrong abstraction, or actively harmful.

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| Natural language recurrence input ("every Monday") | Not this server's job. Server exposes primitives; the agent/LLM interprets user intent into structured fields. Adding NLP creates a second parsing layer with inevitable edge cases | Accept structured JSON only. Agent translates "every Monday" to `{"type": "weekly_on_days", "onDays": ["MO"]}` |
| RRULE string passthrough on writes | Defeats the purpose of structured fields. If agents could pass raw RRULE, they'd skip validation, and the structured model becomes dead code | Only accept structured frequency object. RRULE is an internal transport detail between service and bridge |
| RRULE string in read model (keeping ruleString) | Agents don't need it. Two representations = confusion about which is authoritative. Breaking change is acceptable pre-v2 | Remove `ruleString` from read model entirely. Structured fields ARE the read model |
| Cross-type field inference | If agent sends `type: "monthly"` with `onDays: ["MO"]`, don't silently convert to `monthly_day_of_week`. Ambiguous intent | Reject with clear error: "Did you mean `monthly_day_of_week` with `on: {first: monday}`?" |
| Per-occurrence editing | Editing a single instance of a repeating task. OmniFocus doesn't support this via OmniJS | Document as out of scope. OmniFocus treats each occurrence as a fresh task after completion |
| `minutely` / `hourly` frequency writes | OmniFocus technically accepts these RRULE frequencies but no real-world use case exists for sub-daily repetition in a task manager. Read model may encounter them in wild data | Accept in RRULE parser (read path). Reject in write validation with "OmniFocus supports these frequencies but they have no practical use for task repetition" |
| catchUpAutomatically as separate field | The spec collapses this into the schedule enum: `regularly` (catch-up=true), `regularly_with_catch_up` is wrong -- actually `regularly` means WITHOUT catch-up, `regularly_with_catch_up` means WITH it. Three values collapse schedule + boolean | Use the three-value `schedule` enum. Service layer maps to the two underlying fields |
| Repetition rule on projects via this milestone | Projects also have `repetitionRule` but project writes are deferred to v1.4.3 | Read model change applies to both tasks and projects. Write support is tasks-only for now |

## Feature Dependencies

```
RRULE parser/builder utilities
    |
    v
Read model rewrite (ruleString -> structured fields)
    |                         \
    v                          v
Structured frequency model    SQLite read path update
(Pydantic discriminated        (parse RRULE in _build_repetition_rule)
 union + validators)
    |
    +--- AddTaskCommand gets `repetition_rule` field
    |
    +--- EditTaskCommand gets `repetition_rule` field (PatchOrClear)
    |         |
    |         v
    |    Partial update merge logic (service/domain.py)
    |         |
    |         v
    |    No-op detection for repetition
    |
    v
Bridge handler update (edit_task adds repetition fields)
    |
    v
Bridge handler update (add_task adds repetition fields)
    |
    v
Repo payload models (RepetitionRuleRepoPayload)
```

**Critical path:** RRULE utilities -> Read model rewrite -> Write model + validation -> Bridge handler

**Parallelizable:** SQLite read path update can happen alongside write model work (both depend on RRULE parser)

## Ecosystem Comparison

How other APIs handle repetition rules, informing our design choices.

| Aspect | Microsoft Graph | Todoist | TickTick | OmniFocus Operator (planned) |
|--------|----------------|---------|---------|------------------------------|
| Input format | Structured JSON (`recurrencePattern` + `recurrenceRange`) | Natural language string ("every Monday") | RRULE string (with mandatory start_date) | Structured JSON (frequency + schedule + basedOn + end) |
| Type discriminator | `type` field with 6 values | Implicit (parsed from NL) | N/A (raw RRULE) | `type` field with 8 values |
| Partial update | NO -- must send all required fields per type, or get 400 | Replace entire `due` object | Replace entire rule | YES -- same type merges, type change requires full replacement |
| End conditions | `recurrenceRange` with `type`, `endDate`, `numberOfOccurrences` | Natural language ("for 10 times", "until Dec 2026") | RRULE COUNT/UNTIL | `end` object with exactly-one-key pattern (`date` or `occurrences`) |
| Remove rule | Delete recurrence fields | Remove `due.is_recurring` context | Not documented | `repetitionRule: null` |
| Read/write symmetry | YES -- same shape | NO -- read gives structured, write takes NL | Partial -- RRULE both ways | YES -- same shape |
| Schedule type | Separate concept (calendar event pattern) | Implicit in NL parsing | By Due/By Completion/By Specific | `schedule` enum (3 values) |

## MVP Recommendation

The milestone spec already defines the right scope. Prioritization within implementation:

**Phase 1 (Read model rewrite):**
1. RRULE parser/builder as standalone utility module
2. Read model change: `ruleString` -> structured frequency fields on `RepetitionRule`
3. Both read paths (SQLite `_build_repetition_rule` + bridge adapter) parse RRULE into structured model
4. Golden master re-capture (GOLD-01 constraint)

**Phase 2 (Write model + pipeline):**
1. Frequency model Pydantic types (discriminated union with type-specific validators)
2. `AddTaskCommand` gets optional `repetition_rule` field
3. `EditTaskCommand` gets `PatchOrClear[RepetitionRuleSpec]` field
4. Service layer: validation, merge logic for partial updates, RRULE building
5. Bridge payload + handler for both add_task and edit_task
6. No-op detection, educational warnings

**Defer:**
- `minutely`/`hourly` frequency writes (accept on reads only)
- Project repetition writes (v1.4.3)
- Per-occurrence editing (OmniFocus limitation)

## Sources

- OmniJS API reference: `.research/deep-dives/repetition-rule/repetition-rule-guide.md` (HIGH confidence -- primary source, hand-verified)
- RRULE parser/builder spike: `.research/deep-dives/rrule-validator/` (HIGH confidence -- 79 tests, code portable to production)
- Microsoft Graph `recurrencePattern`: [learn.microsoft.com](https://learn.microsoft.com/en-us/graph/api/resources/recurrencepattern?view=graph-rest-1.0) (HIGH confidence -- official docs)
- Microsoft Graph partial update behavior: [Q&A](https://learn.microsoft.com/en-us/answers/questions/806339/unable-to-patch-a-todo-task-with-a-recurrence-patt) (MEDIUM confidence -- community reports)
- Todoist REST API v2: [developer.todoist.com](https://developer.todoist.com/rest/v2/) (HIGH confidence -- official docs)
- TickTick recurrence: [developer.ticktick.com](https://developer.ticktick.com/) + [community SDK](https://github.com/gritse/TickTickSharp) (LOW confidence -- limited official API docs)
- Asana API: Does not support recurrence via API at all as of March 2026 (MEDIUM confidence -- [forum request](https://forum.asana.com/t/add-recurring-task-support-to-the-asana-api/1130930))
