# Phase 32: Read Model Rewrite - Context

**Gathered:** 2026-03-28
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace the current `RepetitionRule` model (raw `ruleString`, `scheduleType`, `anchorDateKey`, `catchUpAutomatically`) with structured frequency fields on both read paths (SQLite and bridge). Agents receive parsed, structured data — never RRULE strings. This is Phase 1 of the v1.2.3 milestone; the write model (Phase 33) depends on the types defined here.

</domain>

<decisions>
## Implementation Decisions

### Frequency Object Shape
- **D-01:** Typed discriminated union — each frequency type is its own Pydantic model with only its relevant fields. 8 subtypes using `Field(discriminator="type")`. Agent sees exactly what applies, no null-field noise.
- **D-02:** Field naming uses agent-friendly terms: `onDays` (weekly), `onDates` (monthly_day_in_month), `on` (monthly_day_of_week). Not RRULE-native terms.
- **D-08:** Interval omitted when 1 (the default). Only appears in output when > 1.

### End Condition
- **D-03:** Single-key dict following `moveTo` pattern: `{"date": "ISO-8601"}` or `{"occurrences": N}`. Key IS the type. Omit field entirely for no end. Per milestone spec line 34.

### Schedule Model
- **D-06:** 3-value enum derived from 2 SQLite columns: `regularly` (scheduleType=regularly + catchUp=false), `regularly_with_catch_up` (scheduleType=regularly + catchUp=true), `from_completion` (scheduleType=from_completion + catchUp=false). Combination `from_completion + catchUp=true` is an impossible state — fail-fast with error, not silent handling.

### RRULE Parser
- **D-05:** BYDAY positional prefix form only (`BYDAY=2TU`, `BYDAY=-1FR`). BYSETPOS as separate parameter is not supported — clear error message if encountered. OmniFocus always produces the prefix form.
- **D-04:** MINUTELY and HOURLY parsed like any other frequency type — simple `{type, interval}` objects. They are real OmniFocus options.
- **D-07:** Malformed RRULE strings fail-fast with ValueError and educational error message. Consistent with project's fail-fast philosophy.

### monthly_day_of_week Vocabulary
- **D-10:** Ordinals: first/second/third/fourth/fifth/last. Days: monday through sunday, plus weekday (MO-FR) and weekend_day (SA-SU). All lowercase, normalized from RRULE. Reads like English: `{"on": {"second": "tuesday"}}`.

### Breaking Change
- **D-09:** Clean break — `ruleString` removed entirely, no transition period. Pre-release server, single user, installed from source. Milestone spec line 56 confirms this is acceptable.

### Module Structure
- **D-11:** Repetition rule gets its own module (not inline in `common.py`). The discriminated union + parser/builder utilities are too complex for a shared commons file. Exact package structure is Claude's discretion.

### Golden Master
- **D-12:** 30 golden master scenarios captured in `08-repetition/` covering all 8 frequency types, schedule variations, anchor dates, end conditions, and completion lifecycle. InMemoryBridge updated to match. Golden master operates at raw bridge layer — unaffected by the structured model transformation. The parser is a separate layer tested independently.

### Claude's Discretion
- RRULE utility function internal structure and wiring to both read paths
- Pydantic model names and ~~FrequencySpec~~ → Frequency hierarchy details
- Exact warning/error message wording (existing `agent_messages` patterns as style guide)
- Test structure and organization
- Exact module/package layout within the decided "own module" boundary

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Milestone Spec
- `.research/updated-spec/MILESTONE-v1.2.3.md` -- Complete structured model spec (frequency table, root-level fields, lifecycle, validation layers, design notes, Claude's discretion items)

### Requirements
- `.planning/REQUIREMENTS.md` -- READ-01 through READ-04 acceptance criteria for this phase

### Research Artifacts
- `.research/deep-dives/rrule-validator/rrule_validator.py` -- Spike parser + builder (~200 lines), 79 tests. Code is directly portable to production. Handles DAILY/WEEKLY/MONTHLY/YEARLY; needs extension for MINUTELY/HOURLY and BYDAY positional prefix.
- `.research/deep-dives/rrule-validator/test_rrule_validator.py` -- Spike test suite
- `.research/deep-dives/repetition-rule/repetition-rule-guide.md` -- Full OmniJS API reference for Task.RepetitionRule

### Existing Code (transformation targets)
- `src/omnifocus_operator/models/common.py` -- Current `RepetitionRule` model (4 fields, to be replaced)
- `src/omnifocus_operator/models/enums.py` -- Current `ScheduleType` (2 values) and `AnchorDateKey` (3 values) enums
- `src/omnifocus_operator/repository/hybrid.py` lines 198-227 -- SQLite read path `_build_repetition_rule()` (transformation target)
- `src/omnifocus_operator/bridge/adapter.py` lines 92-117 -- Bridge adapter `_adapt_repetition_rule()` (transformation target)

### Golden Master
- `tests/golden_master/snapshots/08-repetition/` -- 30 scenarios with raw bridge-format repetition rule data (ground truth for parser testing)
- `tests/golden_master/normalize.py` -- Normalization rules; `repetitionRule` is in `UNCOMPUTED_PROJECT_FIELDS` only

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Spike parser (`rrule_validator.py`): `validate_rrule()` and `build_rrule()` with 79 tests — directly portable, needs MINUTELY/HOURLY and BYDAY prefix extension
- `ScheduleType` and `AnchorDateKey` enums in `models/enums.py` — will be modified (ScheduleType gains third value)
- `OmniFocusBaseModel` base class with camelCase alias generation — all new models inherit from this

### Established Patterns
- Discriminated unions: `moveTo` uses "key IS the type" pattern — established precedent for `end` condition
- Adapter layer: `_adapt_repetition_rule()` transforms bridge JSON → model dict; this is where bridge-path parsing will hook in
- SQLite mapping: `_build_repetition_rule()` maps DB columns → model dict; this is where SQLite-path parsing will hook in
- Both paths produce dicts that Pydantic validates into models — the parser can return dicts or model instances

### Integration Points
- SQLite read path: `_build_repetition_rule()` in `hybrid.py` — currently passes through raw `ruleString`, will call parser
- Bridge adapter: `_adapt_repetition_rule()` in `adapter.py` — currently maps enum values, will call parser
- Model layer: `RepetitionRule` in `common.py` — replaced with structured model in new module
- `models/__init__.py` — exports and `model_rebuild()` calls need updating

</code_context>

<specifics>
## Specific Ideas

- Live OmniFocus data was queried during discussion to confirm: BYDAY=2TU (prefix form), 3-value schedule derivation, BYMONTHDAY=-1 for last day
- User explicitly wants YAGNI approach: only parse what OmniFocus actually produces, not defensive handling of theoretical RRULE variants
- User confirmed MINUTELY/HOURLY are real options they occasionally use
- `from_completion + catchUp=true` should crash — it's not a valid UI combination, so encountering it means data corruption

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 32-read-model-rewrite*
*Context gathered: 2026-03-28*
