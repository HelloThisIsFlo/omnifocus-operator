# Phase 18: Repetition Rule Write Support - Context

**Gathered:** 2026-03-13
**Status:** Ready for planning

<domain>
## Phase Boundary

Enable agents to set, modify, and remove repetition rules on tasks via `edit_tasks` (including partial updates), and create tasks with repetition rules via `add_tasks`. Uses structured fields instead of raw RRULE strings. The read model also changes to structured fields — symmetric read/write, `ruleString` removed entirely.

</domain>

<decisions>
## Implementation Decisions

### Write API shape
- Structured fields only — agents never see or write RRULE strings
- Symmetric read/write model: same structured fields on both sides. `ruleString` removed from read model
- Nested frequency object with `type` as discriminator:
  - Types: `minutely`, `hourly`, `daily`, `weekly`, `monthly`, `monthly_day_of_week`, `monthly_day_in_month`, `yearly`
  - `interval` nested inside frequency, defaults to 1
  - Weekly `onDays`: optional array of two-letter codes (MO–SU). Case-insensitive input, normalized to uppercase. Omitted = repeats every N weeks from basedOn date
  - `monthly_day_of_week` `on`: single key-value object. Key = ordinal (first/second/third/fourth/fifth/last). Value = day name (monday–sunday, weekday, weekend_day). Case-insensitive input, normalized to lowercase. Reads like English: `"on": {"second": "tuesday"}`
  - `monthly_day_in_month` `onDates`: array of integers (1–31, -1 for last day). Empty/omitted triggers warning suggesting plain `monthly` type
- `schedule` at root, required on creation: `regularly` / `regularly_with_catch_up` / `from_completion` (three values — no separate catchUp boolean)
- `basedOn` at root, required on creation: `due_date` / `defer_date` / `planned_date` (renamed from anchorDateKey to match OmniFocus UI language)
- `end` at root, optional: `{"date": "ISO-8601-string"}` or `{"occurrences": N}` or omitted for no end. Same "key IS the value" pattern as moveTo — exactly one key allowed

### Repetition lifecycle
- Partial updates supported on `edit_tasks`
- Root-level fields (`schedule`, `basedOn`, `end`) are independently updatable — change one without resending others
- Frequency object partial update rule:
  - Same type → merge (omitted fields preserved from existing rule)
  - Type changes → full replacement of frequency object required (no cross-type inference)
  - `type` is always required in the frequency object (discriminator)
- No existing rule + partial update → error: provide complete rule
- Creating new rule (via `add_tasks` or `edit_tasks` on non-repeating task) → all required fields must be present (frequency with type, schedule, basedOn)
- `repetitionRule: null` = remove repetition rule
- Omit `repetitionRule` entirely = no change (UNSET)
- No-op detection with educational warnings (consistent with existing edit_tasks pattern)
- `add_tasks` also supports `repetitionRule` — same model, same validation as creating new via edit_tasks

### RRULE generation and parsing
- Python service layer builds RRULE strings for writes — bridge stays dumb, receives fully validated spec (ruleString + scheduleType + anchorDateKey + catchUp)
- Standalone utility functions with Pydantic model interfaces:
  - `build_rrule(FrequencySpec) -> str` — structured fields to RRULE string (writes)
  - `parse_rrule(str) -> FrequencySpec` — RRULE string to structured fields (reads)
- Both SQLite and bridge read paths need RRULE parsing — standalone function covers both
- Read model change is a breaking change — acceptable at this stage (pre-release, single user)

### Validation and errors
- Three validation layers:
  1. **Pydantic structural**: required fields, enum values, `end` has exactly one key
  2. **Type-specific constraints**: reject fields that don't belong to given frequency type, value ranges (interval >= 1, valid day codes, valid ordinals, dayOfMonth -1 to 31 excluding 0, end.occurrences >= 1)
  3. **Service semantic**: no existing rule + partial update, type change + incomplete frequency, no-op detection
- Same error pattern as existing edit_tasks — ValueError with educational messages
- End date in the past: warning (confirm with user intention), same style as existing "completed task" warnings
- Validate everything cheaply before bridge call — OmniJS layer is flaky, catch errors in Python
- Tool documentation must be very clear on schema — especially -1 convention, day codes, nested structures, field requirements per type

### Claude's Discretion
- RRULE utility function module placement and wiring to both read paths
- Pydantic model structure (discriminated unions, model names, FrequencySpec hierarchy)
- Exact warning/error message wording (read existing codebase warnings for style — user will fine-tune during UAT)
- Test structure and organization
- Bridge.js handler implementation details
- Tool description documentation approach for the complex schema

</decisions>

<specifics>
## Specific Ideas

- The three schedule values (`regularly`, `regularly_with_catch_up`, `from_completion`) collapse what was previously a schedule type + boolean into a single ergonomic field — cleaner for agents
- `basedOn` naming comes from OmniFocus UI language ("based on due date") rather than the technical `anchorDateKey` — more intuitive for agents driving user conversations
- The `monthly_day_of_week` `on` field reads like English: `"on": {"second": "tuesday"}` — "on the second Tuesday of every month"
- Database validation is fine in general (e.g., reading current task state for merge logic), just avoid recursive/expensive operations
- OmniFocus happily accepts interval=10000 (repeating every 10,000 years) — no upper bound needed
- OmniFocus handles edge cases like dayOfMonth=31 in February internally — no need to validate calendar logic

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RepetitionRule` model (`models/common.py`): needs complete rewrite — replace ruleString + schedule_type + anchor_date_key + catch_up_automatically with structured frequency fields
- `ScheduleType` / `AnchorDateKey` enums (`models/enums.py`): may need updates for new value naming (regularly_with_catch_up, basedOn values)
- UNSET sentinel pattern (`models/write.py`): reuse for partial update support on repetition fields
- Existing edit_tasks validation pipeline (`service.py`): template for repetition validation
- Educational warnings pattern (`service.py`): reuse for repetition no-ops and edge cases

### Established Patterns
- Service validates before bridge executes — all repetition validation in Python
- Bridge.js receives fully validated spec — no logic, just relay
- `model_dump(by_alias=True)` for camelCase bridge payloads
- `items: list[dict]` input with `model_validate()` at MCP layer
- No-op detection via field comparison before bridge delegation

### Integration Points
- `bridge/bridge.js`: needs handler for setting/removing repetition rule on tasks (construct `new Task.RepetitionRule(ruleString, null, scheduleType, anchorDateKey, catchUp)` or assign `null`)
- `bridge/adapter.py` `_adapt_repetition_rule()`: integrate RRULE parsing for bridge read path
- `repository/hybrid.py` `_build_repetition_rule()`: integrate RRULE parsing for SQLite read path
- `service.py`: merge logic for partial updates, build_rrule() calls, validation
- `models/write.py`: new write model for repetition rule (with UNSET support for partial updates)
- `models/common.py`: RepetitionRule read model rewrite
- `simulator/data.py`: all test tasks currently have `repetitionRule: None` — needs test data with actual rules
- `add_tasks` in service.py and bridge.js: wire in repetition rule support

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 18-repetition-rule-write-support-structured-fields-not-rrule-strings*
*Context gathered: 2026-03-13*
