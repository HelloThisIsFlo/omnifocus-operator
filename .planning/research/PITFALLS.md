# Domain Pitfalls

**Domain:** Repetition rule write support for OmniFocus MCP server
**Researched:** 2026-03-27
**Confidence:** HIGH -- pitfalls derived from codebase inspection, spike artifacts, OmniJS ground truth (352 real tasks), and RFC 5545 edge cases

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or broken read model.

### Pitfall 1: BYDAY Positional Prefix Form (BYDAY=-1SA)

**What goes wrong:** The spike parser (`rrule_validator.py`) validates BYDAY values against bare two-letter codes (`MO`, `TU`, etc.) only. Real OmniFocus data contains `BYDAY=-1SA` (last Saturday) -- RFC 5545 allows an integer prefix on BYDAY values (e.g., `2TU` = second Tuesday, `-1SA` = last Saturday). The parser will reject valid existing rules on read, crashing the read path for any task with this RRULE form.

**Why it happens:** The spike was built against the simple BYDAY+BYSETPOS pattern (`BYDAY=TU;BYSETPOS=2`). OmniFocus can emit either form interchangeably -- the prefixed BYDAY form and the BYDAY+BYSETPOS form are semantically equivalent.

**Consequences:**
- `parse_rrule` blows up on read for existing tasks with prefixed BYDAY
- The structured frequency model (`monthly_day_of_week` with `on` field) must handle both input forms, normalizing to one canonical output
- Golden master tests will fail on real data if the parser can't round-trip both forms

**Prevention:**
- Parser must accept `BYDAY=-1SA`, `BYDAY=2TU`, `BYDAY=-1MO,2FR` (RFC 5545 Section 3.3.10)
- Normalize both forms to the same structured output (`monthly_day_of_week` with `on: {"last": "saturday"}`)
- Builder should emit the BYSETPOS form (more explicit, matches the structured model)
- Add test cases from real data: `FREQ=MONTHLY;BYDAY=-1SA`, `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1`

**Detection:** Parse every distinct `ruleString` from the golden master or real database through the parser. Any `ValueError` = missed form.

**Phase:** Read model rewrite (Phase 1). Must be caught before write model builds on top.

---

### Pitfall 2: Read Model Breaking Change -- Downstream Ripple

**What goes wrong:** Replacing `ruleString` (a flat string) with structured fields (`frequency`, `schedule`, `basedOn`, `end`) changes the `RepetitionRule` model shape. Every consumer of the read model must be updated simultaneously: the SQLite mapper (`_build_repetition_rule`), the bridge adapter (`_adapt_repetition_rule`), the `RepetitionRule` Pydantic model, all test fixtures, the golden master normalizer, InMemoryBridge task data, and the MCP tool output serialization.

**Why it happens:** The `RepetitionRule` model is used in `ActionableEntity` (shared by Task and Project). Changes propagate to both entity types across both read paths (SQLite + bridge).

**Consequences:**
- Miss one consumer and you get Pydantic validation errors in production (the model expects structured fields, gets flat ruleString)
- Test fixtures across 56+ files reference `repetitionRule` with `ruleString` field
- Golden master snapshots contain the old shape -- need re-normalization strategy
- The bridge `rr()` function returns `{ruleString, scheduleType, anchorDateKey, catchUpAutomatically}` -- adapter must now parse ruleString into structured frequency

**Prevention:**
- Audit every file that references `repetitionRule`, `ruleString`, `rule_string`, `RepetitionRule` before starting (Grep shows 8 src files, 56 test files)
- Change the model first, then let Pydantic validation errors guide remaining fixes
- Both read paths (SQLite `_build_repetition_rule` and bridge adapter `_adapt_repetition_rule`) must call `parse_rrule` to decompose the ruleString
- Golden master: add `repetitionRule` structured fields to the normalization, strip `ruleString` if it no longer exists

**Detection:** Run `uv run pytest` after model change -- mass failures across test suite are expected and guide the fix.

**Phase:** Read model rewrite (Phase 1). The entire phase exists to handle this.

---

### Pitfall 3: Schedule Field Collapse Asymmetry (3 values vs 2+bool)

**What goes wrong:** The spec collapses `scheduleType` (2 values: `regularly`, `from_completion`) + `catchUpAutomatically` (boolean) into `schedule` (3 values: `regularly`, `regularly_with_catch_up`, `from_completion`). The mapping is:

| schedule | scheduleType | catchUp |
|----------|-------------|---------|
| `regularly` | `Regularly` | `false` |
| `regularly_with_catch_up` | `Regularly` | `true` |
| `from_completion` | `FromCompletion` | `false`* |

*`catchUp` is meaningless for `FromCompletion` but must still be passed to the constructor.

**The trap:** On reads, you must derive `schedule` from two fields. On writes, you must decompose back. The OmniJS constructor requires both `scheduleType` AND `catchUpAutomatically` as separate params. If you forget to set `catchUp=true` when `schedule=regularly_with_catch_up`, the bridge creates the wrong rule silently (no error, just wrong behavior).

**Additional traps:**
- `from_completion` with `catchUp=true` is technically valid in OmniJS but meaningless -- should we warn? Silently normalize to `false`?
- SQLite `_SCHEDULE_TYPE_MAP` currently maps `"fixed"` and `"from-assigned"` to `"regularly"` but has no concept of catch-up distinction -- need to check what SQLite stores for catchUpAutomatically
- The existing `ScheduleType` enum has only 2 values (`regularly`, `from_completion`). Adding the 3-value `schedule` field means the enum changes or a new one replaces it

**Consequences:** Silent data corruption -- task appears to repeat with catch-up but doesn't, or vice versa. User's missed occurrences pile up without auto-skip.

**Prevention:**
- Explicit mapping table with exhaustive tests for all 3 directions: `(schedule) -> (scheduleType, catchUp)`, `(scheduleType, catchUp) -> schedule`, and `(SQLite raw) -> schedule`
- Bridge handler must receive `scheduleType` + `catchUpAutomatically` as separate params (matching the OmniJS constructor)
- Service layer does the collapse/expansion; bridge stays dumb
- Test: create rule with each schedule value, read it back, verify round-trip

**Phase:** Both phases. Read path (Phase 1) needs parse direction. Write path (Phase 2) needs build direction.

---

### Pitfall 4: OmniJS RepetitionRule Immutability Footgun

**What goes wrong:** All properties on `Task.RepetitionRule` are read-only. You cannot do `task.repetitionRule.ruleString = "FREQ=DAILY"`. You must create an entirely new `Task.RepetitionRule` and assign it. If the bridge handler tries to partially mutate an existing rule, OmniJS silently ignores the write (no error thrown).

**Why it happens:** Natural instinct is to read current rule, modify one field, write it back. OmniJS objects look mutable (no freeze, no error on assignment) but property writes are silently dropped.

**Consequences:** Bridge thinks it edited the rule, returns success, but rule is unchanged. No error in the bridge response. Service layer has no way to detect the failure. Write-through guarantee sees the old rule in SQLite.

**Prevention:**
- Bridge handler must ALWAYS construct a new `Task.RepetitionRule(ruleString, null, scheduleType, anchorDateKey, catchUp)` and assign it to `task.repetitionRule`
- Never read-modify-write on the OmniJS object -- Python service does the merge, bridge receives a complete rule spec
- Document this in bridge.js with a comment: "RepetitionRule is immutable -- always create new"
- Test via golden master: set rule, verify ruleString actually changed in read-back

**Phase:** Write model (Phase 2). Bridge handler implementation.

---

### Pitfall 5: .name Accessor is Broken on RepetitionRule Enums

**What goes wrong:** The repetition-rule-guide.md shows `r.scheduleType.name` and `r.anchorDateKey.name` for reading enum values. Ground truth testing (FINDINGS.md Section 9.1) proved these return `undefined`. The bridge must use `===` comparison against the enum constants, not `.name` accessors.

**Why it happens:** OmniFocus opaque enums don't expose `.name` on their RepetitionRule-related enums, even though `.name` works on some other OmniFocus enums. This is inconsistent but empirically verified.

**Consequences:** Bridge returns `undefined` for scheduleType and anchorDateKey. Adapter maps `undefined` to unexpected values. Pydantic validation fails or produces garbage.

**Prevention:**
- The existing bridge `rr()` function already uses `rst()` and `adk()` resolvers with `===` comparison -- verified in current bridge.js
- The write path must similarly use `Task.RepetitionScheduleType.Regularly` (not string names) when constructing rules
- When writing the bridge handler, pass the enum constants directly to the constructor, not string representations
- The bridge receives string values from Python (`"Regularly"`, `"DueDate"`) and must map them to the OmniJS enum constants

**Detection:** Any `undefined` in bridge response JSON for scheduleType or anchorDateKey.

**Phase:** Write model (Phase 2). Bridge handler must map Python strings to OmniJS enum constants.

---

## Moderate Pitfalls

### Pitfall 6: Partial Update Merge -- Three-Way UNSET/null/value on Nested Object

**What goes wrong:** The `repetitionRule` field has three states at the command level:
- UNSET: no change to repetition rule
- `null`: remove repetition rule
- Object: set/modify repetition rule

Within the object, each sub-field (`schedule`, `basedOn`, `end`, `frequency`) also has UNSET/null/value semantics. This creates a nested UNSET problem not seen in existing flat field patches.

**Specific merge edge cases:**
- `frequency` sent with `type` matching current type but other fields omitted -> merge (preserve current `onDays`, `interval`, etc.)
- `frequency` sent with different `type` -> replace entirely (no cross-type inference)
- `frequency` omitted but `schedule` sent -> update schedule, keep current frequency
- Task has no existing rule + partial `frequency` sent -> error (need complete rule)
- `end: null` -> clear end condition (keep frequency and schedule)
- `end` omitted -> no change to end condition

**Why it happens:** Existing edit fields are flat (name, note, dates). This is the first nested discriminated union with partial update semantics. The `Patch[T]`/`PatchOrClear[T]` type aliases work for flat fields but need careful composition for nested objects.

**Consequences:** Wrong merge = user sends `{"frequency": {"type": "weekly"}}` to change a biweekly-MO-WE rule to weekly, expecting `onDays` preserved. If merge logic resets onDays, rule silently changes meaning.

**Prevention:**
- Define merge semantics in a lookup table, not scattered conditionals
- Same-type merge: for each field in current frequency, use new value if provided, else preserve current
- Type-change: require all type-specific fields (Pydantic can enforce via discriminated union validation)
- Test every combination: same-type-merge, type-change-complete, type-change-partial (error), no-existing-rule-partial (error), clear-rule
- The service layer must read current task state (existing rule) before merge -- this is already the pattern for no-op detection

**Phase:** Write model (Phase 2). Core complexity of the milestone.

---

### Pitfall 7: Frequency Type Discriminator Mismatch Between Read and Write

**What goes wrong:** The spec defines 8 frequency types (`minutely`, `hourly`, `daily`, `weekly`, `monthly`, `monthly_day_of_week`, `monthly_day_in_month`, `yearly`). But RRULE has only 6 FREQ values (`MINUTELY`, `HOURLY`, `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`). The `monthly` vs `monthly_day_of_week` vs `monthly_day_in_month` distinction is determined by which RRULE modifiers are present:

| Type | RRULE Pattern |
|------|--------------|
| `monthly` | `FREQ=MONTHLY` (no BYDAY, no BYMONTHDAY, no BYSETPOS) |
| `monthly_day_of_week` | `FREQ=MONTHLY` + `BYDAY` (with or without BYSETPOS) |
| `monthly_day_in_month` | `FREQ=MONTHLY` + `BYMONTHDAY` |

**The trap:** On read (parse), you must inspect modifiers to determine the structured type. On write (build), you must map the structured type back to `FREQ=MONTHLY` + appropriate modifiers. If the parser mis-classifies a monthly rule, the structured model is wrong. If the builder forgets BYSETPOS for `monthly_day_of_week`, the RRULE is semantically wrong.

**Additional edge:** What about `FREQ=MONTHLY;BYDAY=MO;BYMONTHDAY=15`? Both BYDAY and BYMONTHDAY present. This is valid RFC 5545 but unclear which structured type it maps to. OmniFocus likely doesn't generate this, but an agent could theoretically create it via raw input. Need a decision: reject? Pick one?

**Prevention:**
- Parser: check for BYDAY/BYSETPOS first (monthly_day_of_week), then BYMONTHDAY (monthly_day_in_month), then plain monthly. Order matters.
- Builder: exhaustive match on type discriminator to RRULE components
- Test round-trip for every monthly variant
- Reject BYDAY+BYMONTHDAY combination (conflicting types) with a clear error message

**Phase:** Both phases. Parser in Phase 1, builder in Phase 2.

---

### Pitfall 8: HOURLY/MINUTELY Supported in Spec but Not in Spike

**What goes wrong:** The milestone spec includes `minutely` and `hourly` as frequency types. The spike validator (`VALID_FREQS`) only accepts `DAILY`, `WEEKLY`, `MONTHLY`, `YEARLY`. Real data confirms 1 HOURLY task exists. If the production parser rejects HOURLY, it breaks the read path for that task.

**Why it happens:** The spike was conservative. MINUTELY/HOURLY are valid RRULE FREQ values but rare in OmniFocus usage.

**Consequences:** Read path crashes on any HOURLY/MINUTELY task. Parser must be updated before production.

**Prevention:**
- Add `MINUTELY` and `HOURLY` to `VALID_FREQS`
- These map to `minutely` and `hourly` structured types with no extra fields (same as `daily`)
- Verify OmniFocus accepts them via golden master (at least HOURLY is confirmed in real data)

**Phase:** Read model rewrite (Phase 1).

---

### Pitfall 9: No-Op Detection Needs Repetition Rule Comparison

**What goes wrong:** The `_all_fields_match` method in `DomainLogic` compares payload fields against current task state for no-op detection. It currently checks: name, note, flagged, estimated_minutes, dates, tags, lifecycle, move. It does NOT check repetition rule fields. After adding repetition write support, an agent could send a repetition rule edit that matches the current rule exactly -- this should be detected as a no-op with a warning.

**Consequences:** Without the check, the bridge gets called unnecessarily. Worse, if the bridge call for repetition rule assignment triggers OmniFocus to re-process the rule (creating a new occurrence), what should be a no-op could have side effects.

**Prevention:**
- Add repetition rule comparison to `_all_fields_match`
- Must compare structured fields, not raw RRULE string (the same rule can have different string representations: `FREQ=WEEKLY;INTERVAL=1` == `FREQ=WEEKLY`)
- Normalize before comparison: treat `interval=1` as equivalent to `interval=None` (both mean "every 1")
- Compare each structured field: frequency type, interval, type-specific fields, schedule, basedOn, end

**Phase:** Write model (Phase 2).

---

### Pitfall 10: End Condition Round-Trip Through RRULE

**What goes wrong:** End conditions (`COUNT` and `UNTIL`) live in the RRULE string. But the spec puts them at the root level (`end` field) rather than inside `frequency`. This creates a split: `build_rrule` needs the end condition to build the full RRULE string, but the structured model stores it outside the frequency object. The parse/build functions must bridge this gap.

**Additionally:** The `end.date` uses ISO 8601 format but RRULE `UNTIL` uses `YYYYMMDDTHHMMSSZ` format. The parser/builder must convert between these formats -- silently getting the format wrong produces a valid-looking but semantically wrong RRULE.

**Consequences:**
- Missing COUNT in built RRULE = infinite repetition instead of limited
- UNTIL format mismatch = OmniJS rejects the rule or interprets the date wrong
- Partial update on end condition: changing `end.occurrences` to `end.date` must remove COUNT from RRULE and add UNTIL

**Prevention:**
- `build_rrule` takes frequency fields + end condition as separate params
- `parse_rrule` returns frequency fields + end condition separately
- Explicit ISO 8601 <-> RRULE UNTIL format converter with tests
- Test: create rule with COUNT, read back, verify end.occurrences matches. Same for UNTIL/end.date.

**Phase:** Both phases. Parse in Phase 1, build in Phase 2.

---

### Pitfall 11: Bridge Must Receive Fully Expanded Payload (Not Structured Model)

**What goes wrong:** The bridge is dumb -- it receives a flat payload and passes values to the OmniJS constructor. It does NOT understand the structured frequency model. The Python service must expand the structured model back to: `ruleString` (full RRULE string), `scheduleType` (OmniJS enum name), `anchorDateKey` (OmniJS enum name), `catchUpAutomatically` (boolean). If the service sends structured fields to the bridge, the bridge won't know what to do.

**Pattern alignment:**
- Existing pattern: `edit_tasks` service builds `EditTaskRepoPayload` (flat, bridge-ready) from `EditTaskCommand` (structured, agent-facing)
- Same here: `RepetitionRuleCommand` (structured, agent-facing) must become `{ruleString, scheduleType, anchorDateKey, catchUpAutomatically}` in the repo payload

**Consequences:** Bridge receives unknown fields, throws error, write fails.

**Prevention:**
- PayloadBuilder builds the RRULE string + decomposes schedule back to scheduleType + catchUp
- Bridge handler receives exactly: `{ruleString, scheduleType, anchorDateKey, catchUpAutomatically}` or `null`
- Match the existing bridge pattern: `params.hasOwnProperty("repetitionRule")` check

**Phase:** Write model (Phase 2). PayloadBuilder + bridge handler.

---

### Pitfall 12: SQLite Schedule Type Raw Values Differ From Bridge

**What goes wrong:** SQLite stores `repetitionScheduleTypeString` with raw values like `"fixed"`, `"from-assigned"`, `"due-after-completion"`, `"start-after-completion"`, `"from-completion"`. The bridge sends `"Regularly"` and `"FromCompletion"`. These are different string formats for the same concepts.

Currently `_SCHEDULE_TYPE_MAP` in `hybrid.py` maps both `"fixed"` and `"from-assigned"` to `"regularly"`. With the new schedule field, we also need to check `catchUpAutomatically` (a separate SQLite column) to determine if it's `regularly` vs `regularly_with_catch_up`.

**The trap:** The current mapping works because the old model doesn't distinguish catch-up. The new model must combine `repetitionScheduleTypeString` + `catchUpAutomatically` from SQLite to produce the correct 3-value `schedule` field.

**Consequences:** SQLite reads return wrong `schedule` value, agent sees `regularly` when it should be `regularly_with_catch_up`.

**Prevention:**
- Update `_build_repetition_rule` to derive `schedule` from both `scheduleType` and `catchUpAutomatically`
- Map: `(fixed|from-assigned, true)` -> `regularly_with_catch_up`, `(fixed|from-assigned, false)` -> `regularly`, `(*-completion, *)` -> `from_completion`
- Test with golden master data that includes both catch-up=true and catch-up=false tasks

**Phase:** Read model rewrite (Phase 1).

---

## Minor Pitfalls

### Pitfall 13: INTERVAL=1 Equivalence

**What goes wrong:** `FREQ=WEEKLY` and `FREQ=WEEKLY;INTERVAL=1` are semantically identical. The parser should treat missing INTERVAL as defaulting to 1. But on read, OmniFocus may store either form. If the read path returns `interval: null` for one and `interval: 1` for the other, comparisons break.

**Prevention:** Parser normalizes: if INTERVAL is 1 or absent, the structured output uses `interval: 1` (always explicit). Builder: if interval is 1, omit it from RRULE string (canonical form, shorter). Document this normalization.

---

### Pitfall 14: Tool Description Complexity

**What goes wrong:** The structured frequency model has 8 types, each with different required fields. LLMs parsing the tool schema can get confused by the discriminated union, send wrong field combinations, and get opaque Pydantic validation errors.

**Prevention:**
- Tool description must include concrete examples for the most common patterns (daily, weekly with days, monthly day-of-week)
- Pydantic validation errors must be educational -- "monthly_day_of_week requires 'on' field with format {ordinal: day}" not just "field required"
- The existing `extra="forbid"` on CommandModel will catch extraneous fields

---

### Pitfall 15: Golden Master Must Add Repetition Rule Scenarios

**What goes wrong:** Current golden master has 43 scenarios across 7 categories. None test repetition rule creation or editing. After v1.2.3, the golden master needs new scenarios proving repetition rule round-trip through the real bridge. Without them, InMemoryBridge can drift.

**Prevention:**
- GOLD-01 constraint: "any phase that adds or modifies bridge operations must re-capture golden master"
- Plan new golden master categories: set repetition rule, modify rule, clear rule
- Capture at minimum: daily, weekly-with-days, monthly-by-date, monthly-day-of-week, from-completion

---

### Pitfall 16: OmniJS Constructor Parameter Position

**What goes wrong:** The `Task.RepetitionRule` constructor takes 5 positional params: `(ruleString, null, scheduleType, anchorDateKey, catchUpAutomatically)`. The second param is deprecated and MUST be `null`. If the bridge passes `scheduleType` as the second param (off-by-one), OmniJS may silently create a rule using the deprecated API path with wrong semantics.

**Prevention:**
- Bridge handler must explicitly pass `null` as the second param
- Comment in bridge.js explaining the 5-param constructor and the deprecated slot
- Test: create rule via bridge, read it back, verify all 4 properties match

---

### Pitfall 17: Adapter Must Handle Both Old and New Shapes

**What goes wrong:** The bridge adapter (`_adapt_repetition_rule`) currently maps `scheduleType` and `anchorDateKey` from PascalCase to snake_case, and passes through `ruleString` as-is. After the read model change, the adapter must ALSO call `parse_rrule` to decompose `ruleString` into structured frequency fields. But the adapter should remain idempotent (safe to call on already-adapted data). If structured fields are already present, the adapter should not re-parse.

**Prevention:**
- Add idempotency check: if `frequency` key exists, skip parsing (already adapted)
- Test adapter with both old-shape (bridge JSON) and new-shape (already adapted) data

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|-------------|---------------|------------|
| Read model rewrite (Phase 1) | BYDAY positional form crashes parser (#1) | Test against all 49 distinct ruleStrings from real DB |
| Read model rewrite (Phase 1) | Breaking change ripple (#2) | Grep for all `ruleString`/`repetitionRule` references, update atomically |
| Read model rewrite (Phase 1) | HOURLY not in parser (#8) | Add MINUTELY/HOURLY to VALID_FREQS before production |
| Read model rewrite (Phase 1) | SQLite schedule collapse (#12) | Derive 3-value schedule from scheduleType + catchUp |
| Write model + bridge (Phase 2) | Partial update merge logic (#6) | Enumerate all merge cases in a decision table |
| Write model + bridge (Phase 2) | Immutable RepetitionRule (#4) | Always construct new rule, never mutate |
| Write model + bridge (Phase 2) | .name accessor broken (#5) | Use === comparison to enum constants in bridge |
| Write model + bridge (Phase 2) | Schedule decomposition wrong (#3) | Mapping table with exhaustive tests |
| Write model + bridge (Phase 2) | Bridge expects flat payload (#11) | PayloadBuilder does the expansion |
| Write model + bridge (Phase 2) | No-op detection missing (#9) | Add repetition rule comparison to _all_fields_match |
| Both phases | End condition format mismatch (#10) | ISO 8601 <-> RRULE UNTIL converter with tests |
| Both phases | Monthly type classification (#7) | Parser modifier-based classification with clear precedence |

---

## RRULE Edge Cases to Test

Derived from real OmniFocus data (352 repeating tasks, 49 distinct ruleStrings):

| RRULE | What's Tricky | Frequency Type |
|-------|--------------|----------------|
| `FREQ=DAILY` | Simplest case | `daily` |
| `FREQ=DAILY;INTERVAL=88` | Max observed interval | `daily` |
| `FREQ=WEEKLY;BYDAY=MO,TU,WE,TH,FR` | 5-day BYDAY list (weekdays) | `weekly` |
| `FREQ=WEEKLY;INTERVAL=2;BYDAY=TU,TH` | Interval + BYDAY combined | `weekly` |
| `FREQ=MONTHLY` | Plain monthly (no modifiers) | `monthly` |
| `FREQ=MONTHLY;BYMONTHDAY=14` | Specific day of month | `monthly_day_in_month` |
| `FREQ=MONTHLY;BYMONTHDAY=-1` | Last day of month | `monthly_day_in_month` |
| `FREQ=MONTHLY;BYDAY=TU;BYSETPOS=2` | Nth weekday (BYSETPOS form) | `monthly_day_of_week` |
| `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1` | Weekend day (multi-BYDAY + BYSETPOS) | `monthly_day_of_week` |
| `FREQ=MONTHLY;BYDAY=-1SA` | Positional BYDAY form (no BYSETPOS) | `monthly_day_of_week` |
| `FREQ=HOURLY` | Rare but exists in real data | `hourly` |
| `FREQ=YEARLY` | Annual | `yearly` |
| `FREQ=WEEKLY;COUNT=10` | End by count | `weekly` + end |
| `FREQ=MONTHLY;UNTIL=20261231T000000Z` | End by date | `monthly` + end |
| `FREQ=WEEKLY;INTERVAL=1` | Explicit interval=1 (equiv to omitted) | `weekly` |

## Sources

- Codebase inspection: `src/omnifocus_operator/` (models, bridge, adapter, service, repository)
- Spike artifacts: `.research/deep-dives/rrule-validator/` (parser + builder, 79 tests)
- OmniJS ground truth: `.research/deep-dives/omnifocus-api-ground-truth/FINDINGS.md` (352 tasks, 49 ruleStrings)
- OmniJS API reference: `.research/deep-dives/repetition-rule/repetition-rule-guide.md`
- Milestone spec: `.research/updated-spec/MILESTONE-v1.2.3.md`
- RFC 5545 (iCalendar RRULE): training data, verified against real OmniFocus behavior
