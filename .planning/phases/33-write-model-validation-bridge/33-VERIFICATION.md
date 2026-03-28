---
phase: 33-write-model-validation-bridge
verified: 2026-03-28T22:30:00Z
status: passed
score: 16/16 must-haves verified
re_verification: false
---

# Phase 33: Write Model, Validation & Bridge Verification Report

**Phase Goal:** Agents can create tasks with repetition rules, partially update existing rules (merge within type, clear, change type), and receive educational errors for invalid input -- all through existing `add_tasks` and `edit_tasks` tools
**Verified:** 2026-03-28
**Status:** passed
**Re-verification:** No -- initial verification

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | RepetitionRuleAddSpec accepts all 9 frequency types with required schedule/basedOn and optional end | VERIFIED | `contracts/use_cases/repetition_rule.py` — class with `frequency: Frequency`, `schedule: Schedule`, `based_on: BasedOn`, `end: EndCondition | None = None`. Spot-check confirms instantiation works. |
| 2 | RepetitionRuleEditSpec allows independent patching of schedule/basedOn/end and patching of frequency | VERIFIED | All fields default to UNSET. test_service.py TestEditTaskRepetitionRule covers EDIT-03/04/05/06/07/08. |
| 3 | AddTaskCommand embeds RepetitionRuleAddSpec | None = None | VERIFIED | `add_task.py` line 40: `repetition_rule: RepetitionRuleAddSpec | None = None` |
| 4 | EditTaskCommand embeds PatchOrClear[RepetitionRuleEditSpec] = UNSET | VERIFIED | `edit_task.py` line 56: `repetition_rule: PatchOrClear[RepetitionRuleEditSpec] = UNSET` |
| 5 | RepetitionRuleRepoPayload has 4 bridge-ready fields (ruleString, scheduleType, anchorDateKey, catchUpAutomatically) | VERIFIED | `contracts/use_cases/repetition_rule.py` lines 52-63 — 4 fields present with correct types. |
| 6 | schedule_to_bridge and based_on_to_bridge produce correct inverse mappings | VERIFIED | Spot-check confirms all 6 mappings produce correct values. Round-trip tested in test_rrule_schedule_inverse.py. |
| 7 | Validation rejects cross-type fields, out-of-range values, and invalid structures | VERIFIED | validate.py covers interval, day codes, ordinals, day names, on_dates range, end occurrences. Spot-checks confirmed. Cross-type field rejection is handled by Pydantic discriminated union. |
| 8 | Agent message constants exist for all repetition rule errors and warnings | VERIFIED | errors.py: 9 REPETITION_* constants. warnings.py: 4 REPETITION_* constants. All non-empty strings with correct content. |
| 9 | Bridge JS constructs Task.RepetitionRule from bridge payload on add_task | VERIFIED | bridge.js lines 270-277: `handleAddTask` constructs Task.RepetitionRule using reverseRst/reverseAdk. |
| 10 | Bridge JS constructs Task.RepetitionRule from bridge payload on edit_task | VERIFIED | bridge.js lines 311-316: `handleEditTask` constructs Task.RepetitionRule for set path. |
| 11 | Bridge JS clears task.repetitionRule when payload.repetitionRule is null | VERIFIED | bridge.js lines 307-309: `task.repetitionRule = null` when payload is null. |
| 12 | Bridge JS has reverse enum lookups for scheduleType and anchorDateKey | VERIFIED | bridge.js lines 81-92: `reverseRst` and `reverseAdk` functions. Both exported in module.exports. |
| 13 | add_tasks tool docstring documents all 9 frequency types with examples | VERIFIED | server.py lines 221-253: minutely through yearly listed, 3 examples (daily from completion, weekly on days with end, monthly day of week). |
| 14 | edit_tasks tool docstring documents partial update semantics with examples | VERIFIED | server.py lines 304-324: partial update semantics explained, 4 examples (schedule change, interval, type switch, clear). |
| 15 | add_task with RepetitionRuleAddSpec produces correct bridge payload | VERIFIED | service.py _AddTaskPipeline._validate_repetition_rule wired to validate.py. payload.py _build_repetition_rule_payload wired to build_rrule + schedule_to_bridge + based_on_to_bridge. 15 tests in TestAddTaskRepetitionRule all pass. |
| 16 | edit_task merge and clear logic works correctly for all EDIT scenarios | VERIFIED | service.py _EditTaskPipeline._apply_repetition_rule: UNSET passthrough (EDIT-03), null clear (EDIT-02), same-type merge via model_fields_set overlay (EDIT-09/10/11/12), type-change replacement (EDIT-13), no-existing-rule error (EDIT-15), no-op detection (EDIT-16). 16 tests in TestEditTaskRepetitionRule all pass. |

**Score:** 16/16 truths verified

---

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/contracts/use_cases/repetition_rule.py` | RepetitionRuleAddSpec, RepetitionRuleEditSpec, RepetitionRuleRepoPayload | VERIFIED | All 3 classes present, correct inheritance (CommandModel), camelCase aliases work, exports in `__all__`. |
| `src/omnifocus_operator/rrule/schedule.py` | schedule_to_bridge, based_on_to_bridge inverse mappings | VERIFIED | Both functions present at lines 51-61. Dict-based lookup, no branches needed. |
| `src/omnifocus_operator/service/validate.py` | validate_repetition_rule_add with sub-validators | VERIFIED | Function at line 67. Internal helpers: _validate_and_normalize_frequency, _validate_interval, _normalize_on_days, _validate_monthly_day_of_week, _validate_monthly_day_in_month, _validate_end. |
| `src/omnifocus_operator/agent_messages/errors.py` | REPETITION_* error constants (9 total) | VERIFIED | REPETITION_TYPE_CHANGE_INCOMPLETE, REPETITION_NO_EXISTING_RULE, REPETITION_INVALID_INTERVAL, REPETITION_INVALID_DAY_CODE, REPETITION_INVALID_ORDINAL, REPETITION_INVALID_DAY_NAME, REPETITION_INVALID_ON_DATE, REPETITION_INVALID_END_OCCURRENCES, REPETITION_INVALID_FREQUENCY_TYPE. |
| `src/omnifocus_operator/agent_messages/warnings.py` | REPETITION_* warning constants (4 total) | VERIFIED | REPETITION_END_DATE_PAST, REPETITION_EMPTY_ON_DATES, REPETITION_NO_OP, REPETITION_ON_COMPLETED_TASK. All non-empty, balanced braces confirmed by test_warnings.py. |
| `src/omnifocus_operator/service/service.py` | _AddTaskPipeline._validate_repetition_rule, _EditTaskPipeline._apply_repetition_rule, _merge_same_type_frequency | VERIFIED | All three present and wired. Lines 193, 290, 381 respectively. |
| `src/omnifocus_operator/service/payload.py` | PayloadBuilder._build_repetition_rule_payload | VERIFIED | Present at line 116. Calls build_rrule + schedule_to_bridge + based_on_to_bridge. build_add and build_edit both wire the repetition rule payload. |
| `src/omnifocus_operator/service/domain.py` | check_repetition_warnings, normalize_empty_on_dates, _repetition_rule_matches | VERIFIED | Lines 168, 195, 531 respectively. REPETITION_END_DATE_PAST, REPETITION_EMPTY_ON_DATES, REPETITION_NO_OP, REPETITION_ON_COMPLETED_TASK all imported and used. |
| `tests/doubles/bridge.py` | InMemoryBridge handles repetitionRule in add_task and edit_task | VERIFIED | Lines 370-371 (add_task), 425-426 (edit_task), 444 (lifecycle repetition handling). |
| `src/omnifocus_operator/bridge/bridge.js` | reverseRst, reverseAdk, repetitionRule handling in handleAddTask/handleEditTask | VERIFIED | Lines 81-92 (functions), 270-277 (add), 306-316 (edit), 441-442 (module.exports). |
| `src/omnifocus_operator/server.py` | Updated add_tasks/edit_tasks docstrings, _format_validation_errors helper | VERIFIED | All 9 frequency types documented. Partial update semantics explained. Both docstrings have examples. Server-level union_tag_invalid error handled for repetitionRule/frequency discriminator errors. |

---

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `contracts/use_cases/repetition_rule.py` | `models/repetition_rule.py` | imports Frequency union, EndCondition | WIRED | Line 19: `from omnifocus_operator.models.repetition_rule import EndCondition, Frequency` |
| `contracts/use_cases/add_task.py` | `contracts/use_cases/repetition_rule.py` | imports RepetitionRuleAddSpec | WIRED | Lines 13-16: both AddSpec and RepoPayload imported. Used at lines 40, 64. |
| `contracts/use_cases/edit_task.py` | `contracts/use_cases/repetition_rule.py` | imports RepetitionRuleEditSpec | WIRED | Lines 18-21: both EditSpec and RepoPayload imported. Used at lines 56, 94. |
| `service/service.py _AddTaskPipeline` | `service/validate.py validate_repetition_rule_add` | calls validation in _validate_repetition_rule step | WIRED | Line 201: `spec = validate_repetition_rule_add(spec)` |
| `service/service.py _EditTaskPipeline` | `service/domain.py` | calls domain logic for merge, warnings, no-op | WIRED | Lines 358-373: normalize_empty_on_dates, check_repetition_warnings called from _apply_repetition_rule. |
| `service/payload.py` | `rrule/builder.py build_rrule` | converts frequency+end to ruleString | WIRED | Line 124: `rule_string = build_rrule(frequency, end)` |
| `service/payload.py` | `rrule/schedule.py schedule_to_bridge` | converts Schedule enum to bridge strings | WIRED | Lines 125-126: schedule_to_bridge and based_on_to_bridge both called. |
| `bridge/bridge.js handleAddTask` | `bridge/bridge.js reverseRst` | reverse lookup for scheduleType enum | WIRED | Line 275: `reverseRst(rr.scheduleType)` |
| `server.py add_tasks` | `contracts/use_cases/add_task.py AddTaskCommand` | model_validate parses repetitionRule from agent JSON | WIRED | Line 264: `AddTaskCommand.model_validate(items[0])` — repetitionRule field present in AddTaskCommand. |

---

### Data-Flow Trace (Level 4)

| Artifact | Data Variable | Source | Produces Real Data | Status |
|----------|---------------|--------|--------------------|--------|
| `service/service.py _AddTaskPipeline` | `self._repo_payload.repetition_rule` | PayloadBuilder._build_repetition_rule_payload called from _build_payload | Yes — builds RepetitionRuleRepoPayload from fully-validated spec | FLOWING |
| `service/service.py _EditTaskPipeline` | `self._repetition_rule_payload` | _apply_repetition_rule merges existing + submitted spec, calls _build_repetition_rule_payload | Yes — real merge from existing task state + command fields | FLOWING |
| `bridge/bridge.js handleAddTask` | `task.repetitionRule` | params.repetitionRule from Python model_dump(by_alias=True) | Yes — constructed from ruleString + reverseRst + reverseAdk + catchUpAutomatically | FLOWING |
| `tests/doubles/bridge.py InMemoryBridge` | `task["repetitionRule"]` | Direct assignment from params | Yes — stored and retrievable, lifecycle repetition also handled | FLOWING |

---

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| schedule_to_bridge produces correct tuples for all 3 schedule values | `uv run python -c "..."` | All 3 mappings correct (FROM_COMPLETION, REGULARLY_WITH_CATCH_UP, REGULARLY) | PASS |
| based_on_to_bridge produces correct strings for all 3 basedOn values | `uv run python -c "..."` | DueDate, DeferDate, PlannedDate all correct | PASS |
| validate_repetition_rule_add passes valid spec and raises on invalid interval | `uv run python -c "..."` | Valid spec returns unchanged; interval=0 raises ValueError with "Interval must be" | PASS |
| Day code normalization: lowercase "mo", "fr" normalized to "MO", "FR" | `uv run python -c "..."` | result.frequency.on_days == ['MO', 'FR'] confirmed | PASS |
| Pydantic rejects type change with incomplete frequency (EDIT-14) | `uv run python -c "..."` | ValidationError raised for weekly_on_days without on_days | PASS |
| bridge.js exports reverseRst and reverseAdk as functions | `node -e "..."` | Both exported as functions, confirmed | PASS |
| Full test suite (1016 tests) passes without failures | `uv run pytest -x -q --no-cov` | 1016 passed in 12.64s | PASS |
| Output schema tests pass with AddTaskResult.warnings field | `uv run pytest tests/test_output_schema.py --no-cov` | 20 passed | PASS |

---

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|------------|------------|-------------|--------|---------|
| ADD-01 | 33-01, 33-02 | Create task with repetition rule using structured fields | SATISFIED | AddTaskCommand.repetition_rule field; service pipeline validates + builds payload |
| ADD-02 | 33-01, 33-02 | All 9 frequency types supported for creation | SATISFIED | test_service.py test_all_9_frequency_types passes all 9 types |
| ADD-03 | 33-01, 33-02 | Interval > 1 supported | SATISFIED | DailyFrequency(interval=3) test passes; validate_repetition_rule_add permits interval >= 1 |
| ADD-04 | 33-01, 33-02 | Weekly onDays field with case-insensitive input normalized to uppercase | SATISFIED | _normalize_on_days in validate.py; test confirms ['mo','fr'] -> ['MO','FR'] |
| ADD-05 | 33-01, 33-02 | Weekly frequency without onDays repeats every N weeks | SATISFIED | WeeklyFrequency separate from WeeklyOnDaysFrequency; test_weekly_bare passes |
| ADD-06 | 33-01, 33-02 | monthly_day_of_week supports on field with ordinal/day | SATISFIED | _validate_monthly_day_of_week in validate.py; valid ordinals and days checked |
| ADD-07 | 33-01, 33-02 | monthly_day_in_month supports onDates field (1-31, -1) | SATISFIED | _validate_monthly_day_in_month; valid range (-1, 1-31) enforced |
| ADD-08 | 33-01, 33-02 | monthly_day_in_month with empty onDates triggers warning | SATISFIED | domain.py normalize_empty_on_dates; REPETITION_EMPTY_ON_DATES warning emitted |
| ADD-09 | 33-02, 33-03 | All 3 schedule values work | SATISFIED | schedule_to_bridge covers all 3; bridge.js reverseRst covers Regularly/FromCompletion |
| ADD-10 | 33-02, 33-03 | All 3 basedOn values work | SATISFIED | based_on_to_bridge covers all 3; bridge.js reverseAdk covers DueDate/DeferDate/PlannedDate |
| ADD-11 | 33-02 | End by date supported | SATISFIED | EndByDate in EndCondition; build_rrule handles it; test_end_by_date passes |
| ADD-12 | 33-02 | End by occurrences supported | SATISFIED | EndByOccurrences in EndCondition; validate checks occurrences >= 1; test passes |
| ADD-13 | 33-01, 33-02 | No end (omitted) creates open-ended repetition | SATISFIED | end=None default; build_rrule handles None end |
| ADD-14 | 33-01, 33-02 | Interval defaults to 1 when omitted | SATISFIED | All frequency subtypes default interval=1; validated by DailyFrequency() test |
| EDIT-01 | 33-02 | Set repetition rule on non-repeating task | SATISFIED | _apply_repetition_rule handles UNSET frequency -> no-existing-rule error only when partial; full spec works |
| EDIT-02 | 33-02, 33-03 | Remove repetition rule (repetitionRule: null) | SATISFIED | None check at service.py line 307 sets clear=True; bridge.js sets null |
| EDIT-03 | 33-01, 33-02 | Omitting repetitionRule entirely = no change | SATISFIED | UNSET check at service.py line 303 returns early |
| EDIT-04 | 33-02 | Change schedule without resending frequency | SATISFIED | schedule falls back to existing.schedule when UNSET; test_schedule_only_change passes |
| EDIT-05 | 33-02 | Change basedOn without resending frequency | SATISFIED | based_on falls back to existing.based_on when UNSET; test_based_on_only_change passes |
| EDIT-06 | 33-02 | Add end condition to task with no end | SATISFIED | is_set(spec.end) check uses submitted end; test passes |
| EDIT-07 | 33-02 | Remove end condition (end: null within spec) | SATISFIED | PatchOrClear[EndCondition] allows None; test_clear_end passes |
| EDIT-08 | 33-02 | Change end type (date to occurrences) | SATISFIED | Full end replacement; test_change_end_type passes |
| EDIT-09 | 33-02 | Same-type frequency update merges — omitted fields preserved | SATISFIED | _merge_same_type_frequency via model_fields_set overlay |
| EDIT-10 | 33-02 | Change frequency interval on same type | SATISFIED | model_fields_set overlay: only interval overridden, on_days preserved; test passes |
| EDIT-11 | 33-02 | Change onDays on weekly task | SATISFIED | Same-type merge: only on_days overridden, interval preserved; test passes |
| EDIT-12 | 33-02 | Change on field on monthly_day_of_week task | SATISFIED | Same-type merge: only on overridden; test passes |
| EDIT-13 | 33-02 | Change frequency type — full replacement required | SATISFIED | Different type = no merge; Pydantic discriminated union requires all type-specific fields; test_type_change_full_replacement passes |
| EDIT-14 | 33-01, 33-02 | Type change with incomplete frequency → clear error | SATISFIED | Pydantic discriminated union raises ValidationError for incomplete type. REPETITION_TYPE_CHANGE_INCOMPLETE constant exists but is deferred to Phase 33.1 (flat frequency model). Current behavior produces a Pydantic ValidationError converted to educational error via _format_validation_errors. |
| EDIT-15 | 33-01, 33-02 | No existing rule + partial update → clear error | SATISFIED | service.py line 339: raises ValueError(REPETITION_NO_EXISTING_RULE) when frequency/schedule/based_on is None |
| EDIT-16 | 33-02 | No-op detection with educational warning | SATISFIED | domain.py _all_fields_match/_repetition_rule_matches; REPETITION_NO_OP emitted; test_noop_same_rule passes |
| VALID-01 | 33-01 | Pydantic rejects invalid structures | SATISFIED | RepetitionRuleAddSpec(CommandModel) with extra="forbid"; discriminated union rejects bad types |
| VALID-02 | 33-01 | Type-specific constraints: valid ranges, valid codes | SATISFIED | validate_repetition_rule_add covers all sub-validators; 25 tests in test_validation_repetition.py |
| VALID-03 | 33-01, 33-03 | Educational error messages consistent with agent_messages patterns | SATISFIED | All error constants in errors.py; _format_validation_errors in server.py for Pydantic errors |
| VALID-04 | 33-03 | Tool descriptions document schema clearly enough for LLM | SATISFIED | add_tasks docstring: all 9 types hierarchically, 3 examples. edit_tasks: partial update semantics, 4 examples. |
| VALID-05 | 33-01, 33-02 | End date in the past triggers warning | SATISFIED | domain.py check_repetition_warnings: REPETITION_END_DATE_PAST emitted when end.date < now |

---

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| `tests/test_warnings.py` | 33-52 | `_FORWARD_DECLARED_WARNINGS` and `_FORWARD_DECLARED_ERRORS` sets retain all repetition constants despite most being wired in Plan 02 | Info | The constants ARE wired (domain.py, validate.py, service.py), but validate.py is not in `_ERROR_CONSUMERS`. Decision was intentional (SUMMARY-01: "service/validate.py not added to _ERROR_CONSUMERS due to pre-existing inline msg pattern"). No functional impact — tests pass. Cleanup opportunity for a future phase. |

No blockers or functional anti-patterns found.

---

### Human Verification Required

#### 1. EDIT-14 Error Message Quality

**Test:** Submit `edit_tasks` with `{id: "...", repetitionRule: {frequency: {type: "weekly_on_days"}}}` (missing `onDays`) to a live agent session.
**Expected:** Error message explains that `onDays` is required for `weekly_on_days` type, ideally mentioning valid frequency types.
**Why human:** The Pydantic discriminated union error message formatting (via `_format_validation_errors`) may produce a different error message than `REPETITION_TYPE_CHANGE_INCOMPLETE` would. The educational quality of the fallback Pydantic error needs human assessment. The automated check confirms an error IS raised, not whether the message is educational enough.

#### 2. Bridge JS repetitionRule Construction (OmniJS Runtime)

**Test:** Create a task with a daily repetition rule via `add_tasks` tool against live OmniFocus.
**Expected:** Task appears in OmniFocus with the correct repetition rule (daily, regularly, due date anchored).
**Why human:** `reverseRst`/`reverseAdk` use OmniJS globals (`Task.RepetitionScheduleType`, `Task.AnchorDateKey`) that don't exist in the Node.js test environment. The logic is correct by inspection but can only be confirmed in the OmniJS runtime.

#### 3. Partial Update Semantics End-to-End

**Test:** Create a repeating task, then send `edit_tasks` with only `{repetitionRule: {schedule: "from_completion"}}`.
**Expected:** Schedule changes, frequency and basedOn are preserved from the existing rule.
**Why human:** Full round-trip through the real bridge, including reading back the updated repetition rule via `get_task` or `get_all`.

---

### Gaps Summary

No gaps blocking goal achievement. All 35 requirements have satisfied implementations. The one intentional deferral (REPETITION_TYPE_CHANGE_INCOMPLETE not actively used until Phase 33.1) is by design and covered by Pydantic validation.

The forward-declared exclusion sets in test_warnings.py are stale (constants are now wired) but this is a non-functional cleanup item, not a gap. Tests pass with or without cleanup.

---

_Verified: 2026-03-28_
_Verifier: Claude (gsd-verifier)_
