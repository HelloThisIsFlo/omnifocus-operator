# Milestone v1.2.2 -- Repetition Rule Write Support

## Goal

Enable agents to set, modify, and remove repetition rules on tasks via `edit_tasks` (including partial updates) and create tasks with repetition rules via `add_tasks`. Uses structured fields instead of raw RRULE strings. The read model also changes to structured fields -- symmetric read/write, `ruleString` removed entirely. No new tools -- extends `add_tasks` and `edit_tasks`.

## What to Build

### Structured Frequency Model

Agents see structured fields, never RRULE strings. Read and write use the same shape.

**Nested frequency object with `type` as discriminator:**

| Type | Extra Fields | Notes |
|------|-------------|-------|
| `minutely` | -- | |
| `hourly` | -- | |
| `daily` | -- | |
| `weekly` | `onDays`: list of two-letter codes (MO-SU) | Case-insensitive input, normalized to uppercase. Omitted = repeats every N weeks from basedOn date |
| `monthly` | -- | Plain monthly by calendar date |
| `monthly_day_of_week` | `on`: `{"ordinal": "day"}` | Key = first/second/third/fourth/fifth/last. Value = monday-sunday/weekday/weekend_day. Case-insensitive, normalized lowercase. Reads like English: `"on": {"second": "tuesday"}` |
| `monthly_day_in_month` | `onDates`: list of ints (1-31, -1 for last day) | Empty/omitted triggers warning suggesting plain `monthly` type |
| `yearly` | -- | |

- `interval` nested inside frequency, defaults to 1

### Root-Level Repetition Fields

| Field | Type | Required | Notes |
|-------|------|----------|-------|
| `schedule` | enum | On creation | `regularly` / `regularly_with_catch_up` / `from_completion` (three values -- no separate catchUp boolean) |
| `basedOn` | enum | On creation | `due_date` / `defer_date` / `planned_date` (renamed from anchorDateKey to match OmniFocus UI language) |
| `end` | object or omit | No | `{"date": "ISO-8601"}` or `{"occurrences": N}` or omitted for no end. Same "key IS the value" pattern as moveTo -- exactly one key allowed |

### Repetition Lifecycle (Partial Updates)

- Root-level fields (`schedule`, `basedOn`, `end`) are independently updatable -- change one without resending others
- Frequency object partial update rule:
  - Same type -> merge (omitted fields preserved from existing rule)
  - Type changes -> full replacement of frequency object required (no cross-type inference)
  - `type` is always required in the frequency object (discriminator)
- No existing rule + partial update -> error: provide complete rule
- Creating new rule (via `add_tasks` or `edit_tasks` on non-repeating task) -> all required fields must be present (frequency with type, schedule, basedOn)
- `repetitionRule: null` = remove repetition rule
- Omit `repetitionRule` entirely = no change (UNSET)
- No-op detection with educational warnings (consistent with existing edit_tasks pattern)

### RRULE Generation and Parsing

- Python service layer builds RRULE strings for writes -- bridge stays dumb, receives fully validated spec (ruleString + scheduleType + anchorDateKey + catchUp)
- Standalone utility functions with Pydantic model interfaces:
  - `build_rrule(FrequencySpec) -> str` -- structured fields to RRULE string (writes)
  - `parse_rrule(str) -> FrequencySpec` -- RRULE string to structured fields (reads)
- Both SQLite and bridge read paths need RRULE parsing -- standalone function covers both
- Read model change is a breaking change -- acceptable at this stage (pre-release, single user)

### Validation Layers

Three layers:
1. **Pydantic structural**: required fields, enum values, `end` has exactly one key
2. **Type-specific constraints**: reject fields that don't belong to given frequency type, value ranges (interval >= 1, valid day codes, valid ordinals, dayOfMonth -1 to 31 excluding 0, end.occurrences >= 1)
3. **Service semantic**: no existing rule + partial update, type change + incomplete frequency, no-op detection

- Same error pattern as existing edit_tasks -- ValueError with educational messages
- End date in the past: warning (confirm with user intention), same style as existing "completed task" warnings
- Validate everything cheaply before bridge call -- OmniJS layer is flaky, catch errors in Python
- Tool documentation must be very clear on schema -- especially -1 convention, day codes, nested structures, field requirements per type

### Design Notes

- The three schedule values collapse what was previously a schedule type + boolean into a single ergonomic field
- `basedOn` naming comes from OmniFocus UI language ("based on due date") rather than the technical `anchorDateKey`
- The `monthly_day_of_week` `on` field reads like English: `"on": {"second": "tuesday"}` -- "on the second Tuesday of every month"
- OmniFocus happily accepts interval=10000 -- no upper bound needed
- OmniFocus handles edge cases like dayOfMonth=31 in February internally -- no need to validate calendar logic
- Database reads during validation are fine (e.g., reading current task state for merge logic) -- avoid recursive/expensive operations

### Claude's Discretion

- RRULE utility function module placement and wiring to both read paths
- Pydantic model structure (discriminated unions, model names, FrequencySpec hierarchy)
- Exact warning/error message wording (read existing codebase warnings for style -- user will fine-tune during UAT)
- Test structure and organization
- Bridge.js handler implementation details
- Tool description documentation approach for the complex schema

## Phasing Hint

~2 plans:
1. **Read model rewrite** -- decompose ruleString into structured fields, parser to production, adapter/SQLite mapping, read-side tests
2. **Write model + bridge + service** -- RepetitionRuleSpec on edit/create specs, builder, bridge handler, validation, write-side tests

## Research Artifacts

- `.research/deep-dives/rrule-validator/` -- parser + builder (~200 lines), 79 tests, zero deps. Code is directly portable to production.
- `.research/deep-dives/repetition-rule/repetition-rule-guide.md` -- full OmniJS API reference

See also: `2026-03-10-repetition-rule-write-support.md`

## Key Acceptance Criteria

- Read model returns structured frequency fields (type, interval, onDays, etc.) instead of ruleString
- `build_rrule` and `parse_rrule` round-trip correctly for all frequency types
- `add_tasks` can create tasks with repetition rules using structured fields
- `edit_tasks` can set, modify (partial update), and remove repetition rules
- Partial update merges correctly: same type preserves omitted fields, type change requires full replacement
- All three schedule values work: `regularly`, `regularly_with_catch_up`, `from_completion`
- All basedOn values work: `due_date`, `defer_date`, `planned_date`
- End conditions work: by date, by occurrences, no end
- Type-specific validation rejects invalid field combinations
- No existing rule + partial update produces clear error
- Tool descriptions document the schema clearly enough for an LLM to construct valid repetition rules
- No new tools -- extends existing `add_tasks` and `edit_tasks`

## Tools After This Milestone

Six (unchanged from v1.2): `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`.
