# Phase 33: Write Model, Validation & Bridge - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable agents to create and edit tasks with repetition rules through existing `add_tasks` and `edit_tasks` tools. 35 requirements (ADD-01 through ADD-14, EDIT-01 through EDIT-16, VALID-01 through VALID-05). No new tools — extends existing write pipeline with repetition rule support across all layers: contracts, service, bridge, validation, and tool descriptions.

</domain>

<decisions>
## Implementation Decisions

### Edit Partial Update Design
- **D-01:** Nested wrapper approach. `EditTaskCommand` gets `repetition_rule: PatchOrClear[RepetitionRuleEditSpec] = UNSET`. The spec has inner `Patch` fields so root-level fields (schedule, basedOn, end) are independently patchable. `null` clears the whole rule. `UNSET` means no change.
- **D-02:** Frequency merge is a service-layer concern. In this phase, `type` is required on every frequency update (Pydantic's discriminated union requires it). Service compares submitted type vs existing type: same → merge (preserve omitted frequency fields), different → require full frequency object. No existing rule + partial update → error. **Design for evolution:** Keep frequency validation logic in the service layer (not heavily reliant on Pydantic structural validation) so that Phase 33.1 can swap to a flat frequency model and make `type` optional without rewriting service logic.

### Write Model Topology
- **D-03:** Two dedicated spec models in `contracts/`:
  - `RepetitionRuleAddSpec(CommandModel)` — all fields required (frequency, schedule, basedOn), end optional. `extra="forbid"` catches agent typos.
  - `RepetitionRuleEditSpec(CommandModel)` — `Patch[Frequency]`, `Patch[Schedule]`, `Patch[BasedOn]`, `PatchOrClear[EndCondition]` for independent updates.
- **D-04:** Noun-first naming for nested specs: `RepetitionRuleAddSpec` / `RepetitionRuleEditSpec` (not `AddRepetitionRuleSpec`). Rationale: nested specs are about the THING (RepetitionRule), not the ACTION. Noun-first groups them in imports/autocomplete. Top-level commands remain verb-first (`AddTaskCommand`). Add a comment in the code explaining this convention.
- **D-05:** Both specs embed the `Frequency` union for now (Phase 33). Write-side models must inherit `CommandModel` (`extra="forbid"`), but Frequency is a read model (`OmniFocusBaseModel`). Phase 33 accepts this gap because the discriminated union provides structural validation that partially compensates. Phase 33.1 will fix this properly: flat `FrequencyAddSpec` and `FrequencyEditSpec` in `contracts/` with `CommandModel` inheritance. Both specs reuse `Schedule`, `BasedOn` enums and `EndCondition` union from `models/`. Design specs so the Frequency swap in 33.1 is easy.
- **D-06:** `AddTaskCommand` embeds `RepetitionRuleAddSpec | None = None`. `EditTaskCommand` embeds `PatchOrClear[RepetitionRuleEditSpec] = UNSET`.

### Bridge OmniJS Strategy
- **D-07:** 4-field bridge format: Python sends `{ruleString, scheduleType, anchorDateKey, catchUpAutomatically}`. Symmetric with how the bridge currently reads repetition rules. Python builds the RRULE string via `build_rrule()`, expands `Schedule` back to `(scheduleType, catchUpAutomatically)` pair, maps `BasedOn` to `anchorDateKey` string.
- **D-08:** Bridge constructs `new Task.RepetitionRule(ruleString, null, scheduleType, anchorDateKey, catchUpAutomatically)`. Second param is deprecated `method`, always `null`. `scheduleType` and `anchorDateKey` are OmniJS enum objects — bridge needs reverse lookups (string → enum constant, e.g., `"Regularly"` → `Task.RepetitionScheduleType.Regularly`).
- **D-09:** Clearing: `task.repetitionRule = null`. Confirmed in OmniJS API — dates remain unchanged.
- **D-10:** All RepetitionRule properties are read-only. Modification = construct new + assign. Bridge never mutates an existing rule.

### Warning & Error Catalog
- **D-11:** Errors (block the operation):
  - Type change with incomplete frequency (EDIT-14)
  - No existing rule + partial update (EDIT-15)
  - Invalid structures: bad enums, missing required fields, wrong field on type (VALID-01, VALID-02)
  - Cross-type fields, e.g., `onDays` on `daily` (VALID-02)
- **D-12:** Warnings (operation succeeds, agent gets educated):
  - End date in the past (VALID-05) — same style as existing "completed task" warnings
  - `monthly_day_in_month` with empty `onDates` (ADD-08) — suggests using plain `monthly`
  - No-op: same rule sent back (EDIT-16) — follows existing `EDIT_NO_CHANGES_DETECTED` pattern
  - Setting repetition on completed/dropped task — follows existing `check_completed_status` pattern
- **D-13:** `monthly_day_in_month` with empty `onDates` uses normalize + warn pattern: service converts to plain `monthly` before building the RRULE (produces `"FREQ=MONTHLY"`). Warning educates agent to use `monthly` directly next time. Read-back is clean: `parse_rrule("FREQ=MONTHLY")` returns `MonthlyFrequency`.

### Tool Descriptions
- **D-14:** Full inline documentation in tool docstrings. The inputSchema is currently opaque (`items: list[dict[str, Any]]` → schema says "array of objects, any properties"). The docstring is the ONLY guidance agents receive — there is no schema to fall back on. This makes comprehensive tool description documentation critical.
- **D-15:** Hierarchical format: each frequency type shows its complete shape on one line with `interval: N`. Type-specific fields (onDays, on, onDates) shown inline with the type.
- **D-16:** Include 2-3 examples per tool showing common patterns (daily from completion, weekly on days with end condition, monthly day of week).
- **D-17:** add_tasks and edit_tasks use different language for optional/clearing:
  - add_tasks: `end` → "omit for no end" (no patch semantics)
  - edit_tasks: `end` → "null to clear" (PatchOrClear semantics)
  - "null to clear an existing repetition rule" only on edit_tasks

### Tool Description Templates

**add_tasks repetition section:**
```
- repetitionRule: Repetition rule (all three root fields required on creation)
  - frequency (required): Object with "type" discriminator
    - {type: "minutely", interval: N}
    - {type: "hourly", interval: N}
    - {type: "daily", interval: N}
    - {type: "weekly", interval: N}  — every N weeks, no specific day constraint
    - {type: "weekly_on_days", interval: N, onDays: ["MO","WE","FR"]}  — specific days (MO-SU)
    - {type: "monthly", interval: N}
    - {type: "monthly_day_of_week", interval: N, on: {"second": "tuesday"}}
        ordinals: first/second/third/fourth/fifth/last
        days: monday-sunday, weekday, weekend_day
    - {type: "monthly_day_in_month", interval: N, onDates: [1, 15]}
        valid dates: 1 to 31, use -1 for last day of month
    - {type: "yearly", interval: N}
    - interval defaults to 1, omit or set explicitly
  - schedule (required): "regularly" / "regularly_with_catch_up" / "from_completion"
  - basedOn (required): "due_date" / "defer_date" / "planned_date"
  - end: {"date": "ISO-8601"} or {"occurrences": N} — omit for no end

  Examples:
    Every 3 days from completion:
      {frequency: {type: "daily", interval: 3},
       schedule: "from_completion", basedOn: "defer_date"}

    Every 2 weeks on Mon and Fri, stop after 10:
      {frequency: {type: "weekly_on_days", interval: 2, onDays: ["MO", "FR"]},
       schedule: "regularly", basedOn: "due_date",
       end: {occurrences: 10}}

    Last Friday of every month:
      {frequency: {type: "monthly_day_of_week", on: {"last": "friday"}},
       schedule: "regularly", basedOn: "due_date"}
```

**edit_tasks repetition section:**
```
- repetitionRule: Set, update, or clear a repetition rule
  - Full rule: same shape as add_tasks (frequency, schedule, basedOn required)
  - Partial update: send only changed fields, omitted root fields preserved
    - frequency.type is always required when updating frequency
    - Same type: omitted frequency fields preserved from existing rule
    - Different type: full replacement, defaults apply like creation
  - end: null to clear, omit to preserve
  - null to clear the repetition rule

  Examples:
    Change just the schedule:
      {schedule: "from_completion"}

    Change interval (type required, other frequency fields preserved):
      {frequency: {type: "daily", interval: 5}}

    Switch to monthly on specific days (schedule/basedOn/end preserved):
      {frequency: {type: "monthly_day_in_month", onDates: [1, 15]}}

    Clear:
      null
```

### Claude's Discretion
- RRULE builder inverse functions (Schedule → scheduleType/catchUp, BasedOn → anchorDateKey)
- Service pipeline step ordering and internal merge algorithm
- Bridge JS reverse enum lookup implementation
- Test structure and organization
- Exact warning/error message wording (existing `agent_messages/` patterns as style guide)
- Whether to keep `interval: N` in the description or refine further during implementation

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Spec
- `.research/updated-spec/MILESTONE-v1.2.3.md` — Complete structured model spec. Lines 37-48 define partial update lifecycle. Line 52 defines bridge payload format. Lines 59-69 define validation layers.

### Requirements
- `.planning/REQUIREMENTS.md` — ADD-01 through ADD-14, EDIT-01 through EDIT-16, VALID-01 through VALID-05. 35 requirements, all mapped to Phase 33.

### Architecture & Naming
- `docs/architecture.md` — Model naming taxonomy (lines 264-317): decision tree for naming, `___Spec` suffix for write-side value objects, noun-first nested specs convention. Write pipeline diagram (lines 128-158). Repetition rule structure (lines 480-607). Validation layers (lines 651-657).

### OmniJS API
- `.research/deep-dives/repetition-rule/repetition-rule-guide.md` — Complete OmniJS RepetitionRule API. Constructor signature (lines 38-47), enum values (lines 49-64), read-only properties (lines 65-73), clearing (line 281), modification pattern (Group 4).

### Existing Code (extension targets)
- `src/omnifocus_operator/contracts/use_cases/add_task.py` — AddTaskCommand, AddTaskRepoPayload (add `repetition_rule` field)
- `src/omnifocus_operator/contracts/use_cases/edit_task.py` — EditTaskCommand, EditTaskRepoPayload (add `repetition_rule` field with PatchOrClear)
- `src/omnifocus_operator/contracts/base.py` — CommandModel, UNSET, Patch[T], PatchOrClear[T]
- `src/omnifocus_operator/service/service.py` — _AddTaskPipeline, _EditTaskPipeline (add repetition rule steps)
- `src/omnifocus_operator/service/domain.py` — DomainLogic (add repetition rule validation/warnings)
- `src/omnifocus_operator/service/validate.py` — Pure validators (add repetition rule validation)
- `src/omnifocus_operator/service/payload.py` — PayloadBuilder (add repetition rule serialization)
- `src/omnifocus_operator/bridge/bridge.js` — handleAddTask, handleEditTask (add repetition rule construction/clearing)
- `src/omnifocus_operator/agent_messages/errors.py` — Add repetition rule error constants
- `src/omnifocus_operator/agent_messages/warnings.py` — Add repetition rule warning constants
- `src/omnifocus_operator/server.py` — Tool docstrings (lines 168-187, 231-260)

### RRULE Utilities (already implemented)
- `src/omnifocus_operator/rrule/builder.py` — `build_rrule(frequency, end)` → RRULE string
- `src/omnifocus_operator/rrule/parser.py` — `parse_rrule(rule_string)` → Frequency
- `src/omnifocus_operator/rrule/schedule.py` — `derive_schedule()` (forward mapping; Phase 33 needs the inverse)

### Read-Side Models (reused by write specs)
- `src/omnifocus_operator/models/repetition_rule.py` — Frequency union (9 types), EndCondition union, RepetitionRule
- `src/omnifocus_operator/models/enums.py` — Schedule, BasedOn enums

### Test Infrastructure
- `tests/test_output_schema.py` — Schema-vs-data validation tests. Phase 33 must keep these passing after adding repetition rule fields to write commands.
- `tests/doubles/` — InMemoryBridge, StubBridge (need repetition rule write support)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `build_rrule(frequency, end)` — already converts Frequency model → RRULE string. Write path calls this directly.
- `derive_schedule(schedule_type, catch_up)` — forward mapping (read path). Write path needs the inverse (~3 lines).
- Frequency discriminated union (9 types) — reused in both AddSpec and EditSpec. Phase 33.1 will flatten this; keep coupling light.
- `_AddTaskPipeline` / `_EditTaskPipeline` — Method Object pattern. New steps slot in naturally.
- `DomainLogic` — existing warning generation for lifecycle, tags, no-op. Repetition warnings follow same pattern.
- `PayloadBuilder` — existing `model_dump(by_alias=True, exclude_unset=True)` pattern handles serialization automatically.

### Established Patterns
- UNSET sentinel + `is_set()` TypeGuard — gates all edit logic. Repetition rule follows same pattern.
- `extra="forbid"` on CommandModel — catches agent typos. Both specs inherit this.
- `PatchOrClear[T]` — three-way semantics already battle-tested on dates, note, estimatedMinutes.
- Bridge `hasOwnProperty()` checks — falsy-safe field detection. Repetition rule uses same approach.
- `normalize_clear_intents()` — existing null-means-clear mapping in edit pipeline.
- Bridge enum resolvers (`rst()`, `adk()`) — forward lookups exist for reads. Write path needs reverse lookups.

### Integration Points
- `AddTaskCommand` / `EditTaskCommand` — add `repetition_rule` field
- `AddTaskRepoPayload` / `EditTaskRepoPayload` — add serialized repetition rule for bridge
- `_AddTaskPipeline` — new `_validate_repetition_rule()` step
- `_EditTaskPipeline` — new `_apply_repetition_rule()` step (fetch existing, merge, validate)
- `bridge.js` `handleAddTask()` / `handleEditTask()` — construct/clear `Task.RepetitionRule`
- `agent_messages/` — new error and warning constants
- `server.py` docstrings — comprehensive repetition rule documentation

</code_context>

<specifics>
## Specific Ideas

- Tool description format was iterated extensively during discussion. Each frequency type shows complete shape with `interval: N`. Examples included for both add and edit. Templates are in the decisions section above — use them as the starting point.
- The `monthly_day_in_month` with empty `onDates` normalizes to `monthly` at the service layer, not just warns. Round-trip is clean: write as monthly, read back as monthly.
- Bridge reverse enum lookups can use `Task.RepetitionScheduleType.all.find(v => v.name === str)` or a simple lookup object — same pattern as existing resolvers, just inverted.
- The `derive_schedule()` inverse is trivial: `regularly` → `("Regularly", false)`, `regularly_with_catch_up` → `("Regularly", true)`, `from_completion` → `("FromCompletion", false)`.
- User confirmed MINUTELY and HOURLY are real OmniFocus options they occasionally use (carried from Phase 32 D-04).

</specifics>

<deferred>
## Deferred Ideas

- **Phase 33.1: Flat Frequency Model** — Flatten the 9-subtype discriminated Frequency union into 3 flat classes: `Frequency` (read, `OmniFocusBaseModel`), `FrequencyAddSpec` (write, `CommandModel`, type required), `FrequencyEditSpec` (write, `CommandModel`, type optional). Cross-cutting refactor affecting read, add, and edit models. Three wins: (1) makes `type` optional on same-type edit updates (agent sends `{frequency: {interval: 5}}` without restating type), (2) solves the interval serialization issue from Phase 32.1 (`exclude_defaults` on interval=1 without losing `type`), (3) simplifies the model hierarchy (9 subtypes + base + union → 3 focused classes). Service-layer validation replaces Pydantic structural validation for cross-type field rejection. Non-applicable fields excluded via `exclude_none` at serialization time. Breaking change on read output — acceptable (pre-release, single user). Also fixes the `extra="forbid"` gap from Phase 33 D-05.
- **Typed inputSchema for write tools** — Currently `items: list[dict[str, Any]]` produces opaque inputSchema. Agents get zero schema information; tool docstrings do all the work. Investigating typed parameters with custom error formatting (via FastMCP middleware or other approaches) would give agents schema + educational errors. Full context document was provided during discussion. Not Phase 33 scope.
- Old test names still reference `FrequencySpec` (carried from Phase 32.1 deferred).

</deferred>

---

*Phase: 33-write-model-validation-bridge*
*Context gathered: 2026-03-28*
