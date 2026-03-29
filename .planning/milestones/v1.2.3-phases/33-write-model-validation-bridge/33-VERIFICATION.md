---
phase: 33-write-model-validation-bridge
verified: 2026-03-29T00:08:44Z
status: gaps_found
score: 4/5 must-haves verified
re_verification:
  previous_status: passed
  previous_score: 16/16
  gaps_closed:
    - "onDates=[1, 15, -1] round-trips correctly (UAT 1d -- builder hardcoded on_dates[0], parser called int() on raw string)"
    - "No-op repetition rule warning fires even when other task fields are modified in same edit (UAT 11b)"
  gaps_remaining:
    - "Partial same-type frequency update (interval-only on weekly_on_days) rejected by Pydantic before service merge runs"
  regressions: []
gaps:
  - truth: "Agent can partially update a repeating task's rule (change interval) without re-sending the entire rule -- omitted frequency fields are preserved from the existing rule when the type doesn't change"
    status: failed
    reason: "Pydantic discriminated union validates the submitted frequency object as a complete subtype before the service layer merge logic can run. Sending {type: 'weekly_on_days', interval: 4} (omitting onDays) raises ValidationError 'Field required' for onDays. The merge logic in _merge_same_type_frequency only runs if Pydantic parsing succeeds first. UAT test 3c confirmed this. Deferred to Phase 33.1 (flat FrequencyEditSpec)."
    artifacts:
      - path: "src/omnifocus_operator/contracts/use_cases/edit_task.py"
        issue: "RepetitionRuleEditSpec.frequency uses the Frequency union (discriminated by type), which requires all subtype-specific fields. There is no partial/edit variant of frequency subtypes."
    missing:
      - "Phase 33.1: flat FrequencyEditSpec with all fields optional except type -- allows interval-only or on_days-only updates without providing all required subtype fields"
human_verification:
  - test: "Submit edit_tasks with {id: '...', repetitionRule: {frequency: {type: 'weekly_on_days', interval: 4}}} to live agent"
    expected: "Error message explains onDays is required, not just a raw Pydantic discriminator error"
    why_human: "Error message educational quality cannot be verified programmatically"
  - test: "Create a task with daily repetition rule via add_tasks tool against live OmniFocus"
    expected: "Task appears with correct recurrence (daily, regularly, due date anchored)"
    why_human: "reverseRst/reverseAdk use OmniJS globals not available in test environment"
  - test: "Create repeating task, then edit_tasks with only {repetitionRule: {schedule: 'from_completion'}}"
    expected: "Schedule changes, frequency and basedOn preserved. Confirmed via get_task."
    why_human: "Full round-trip through real bridge, including read-back"
---

# Phase 33: Write Model, Validation & Bridge Verification Report

**Phase Goal:** Agents can create tasks with repetition rules, partially update existing rules (merge within type, clear, change type), and receive educational errors for invalid input -- all through existing `add_tasks` and `edit_tasks` tools
**Verified:** 2026-03-29T00:08:44Z
**Status:** gaps_found
**Re-verification:** Yes -- after Plan 05 gap closure (UAT bugs 1d and 11b)

## Re-Verification Summary

Previous verification (2026-03-28) returned `status: passed` (16/16 truths). UAT then discovered three bugs:

| UAT Test | Bug | Severity | Plan 05 Status |
|----------|-----|----------|----------------|
| 1d (test 11) | `onDates=[1, 15, -1]` -- extra values silently dropped in builder/parser | Blocker | Fixed (852385a) |
| 11b (test 40) | No-op warning suppressed when other fields also changed | Major | Fixed (456b2a6) |
| 3c (test 17) | Interval-only change on `weekly_on_days` rejected by Pydantic before service merge | Blocker | Deferred to Phase 33.1 |

Plan 05 closed bugs 1d and 11b. Bug 3c remains open by architectural design (requires flat frequency model refactor in Phase 33.1).

---

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|---------|
| 1 | Agent can create a task with a repetition rule (all 9 frequency types, all fields) | VERIFIED | 1020 tests pass; UAT 1a/1b/1c/1e pass; UAT 1d fixed -- builder now emits `BYMONTHDAY=1,15,-1` correctly |
| 2 | Agent can partially update a repeating task's rule (change schedule, basedOn, end, onDays) without re-sending entire rule | PARTIAL | Schedule/basedOn/end/onDays changes work (UAT 3a/3b/3d/3e/3f/3g pass). Interval-only on `weekly_on_days` fails (UAT 3c). See gap below. |
| 3 | Agent can clear a repetition rule with `repetitionRule: null` and change type by providing complete new frequency | VERIFIED | UAT 2b, 4a pass. EDIT-02 and EDIT-13 covered in service tests. |
| 4 | Invalid input is rejected with educational error messages | VERIFIED | UAT 9a-9g all pass. All 9 error constants wired. validate.py covers all sub-validators. |
| 5 | Tool descriptions document repetition rule schema clearly enough for LLM use | VERIFIED | UAT 10a passes. Server.py docstrings: all 9 types listed, partial update semantics explained, 7 examples total. |

**Score:** 4/5 truths verified (truth 2 is partial -- one specific pattern fails)

---

### Gap Closure Verification (Plan 05)

#### Bug 1: Multi-Value BYMONTHDAY (UAT 1d) -- FIXED

**Root cause confirmed fixed:**
- `builder.py` line 99 was: `parts.append(f"BYMONTHDAY={frequency.on_dates[0]}")` -- hardcoded index 0
- `parser.py` `_parse_monthly_bymonthday` was: `day = int(bymonthday_value)` -- failed on comma-separated values

**Fix in place:**
- `builder.py` line 99: `parts.append(f"BYMONTHDAY={','.join(str(d) for d in frequency.on_dates)}")`
- `parser.py` lines 263-264: `days = [int(d) for d in bymonthday_value.split(",")]`

**Test coverage (all pass):**
- `tests/test_rrule.py::TestBuildRrule::test_monthly_day_in_month_multi_values`
- `tests/test_rrule.py::TestParseRrule::test_monthly_bymonthday_multi_values` (class: `TestParseRruleMonthly`)
- `tests/test_rrule.py::TestRoundTrip::test_round_trip_frequency["FREQ=MONTHLY;BYMONTHDAY=1,15,-1"]`

**Spot-check:** `build_rrule(MonthlyDayInMonthFrequency(on_dates=[1, 15, -1]))` -> `"FREQ=MONTHLY;BYMONTHDAY=1,15,-1"`. Round-trip confirmed PASS.

#### Bug 2: No-Op Warning Suppressed with Other Field Changes (UAT 11b) -- FIXED

**Root cause confirmed fixed:**
- `REPETITION_NO_OP` was only generated inside `_all_fields_match` (domain.py), which short-circuits when any other field differs
- `_apply_repetition_rule` in service.py had no independent no-op detection

**Fix in place:**
- `service.py` lines 387-403: after building `self._repetition_rule_payload`, compares against existing rule using `build_rrule` + `schedule_to_bridge` + `based_on_to_bridge`. Sets payload to None and appends `REPETITION_NO_OP` when matched.

**Test coverage (all pass):**
- `tests/test_service.py::TestEditTaskRepetitionRule::test_noop_same_rule_with_other_field_change` -- same rule + name change -> warning fires AND name applied
- `tests/test_service.py::TestEditTaskRepetitionRule::test_noop_same_rule` -- pure repetition no-op still works (regression)

---

### Remaining Open Gap (Known Limitation)

#### UAT 3c: Interval-Only Change on `weekly_on_days` Rejected Before Merge

**Confirmed still failing:**

Calling `EditTaskCommand.model_validate({"id": "t1", "repetitionRule": {"frequency": {"type": "weekly_on_days", "interval": 4}}})` raises:
```
ValidationError: 3 validation errors for EditTaskCommand
repetitionRule.RepetitionRuleEditSpec.frequency.tagged-union[...] Field required [on_days]
```

**Scope of limitation:** Applies to any incomplete frequency object where the subtype has required fields beyond `interval` and `type`:
- `weekly_on_days` (requires `on_days`)
- `monthly_day_of_week` (requires `on`)
- `monthly_day_in_month` (requires `on_dates`)

**Not affected:** `daily`, `weekly`, `monthly`, `minutely`, `hourly`, `yearly` -- no required fields beyond the discriminator, so interval-only changes work.

**Assessment against success criterion 2:** The criterion lists "change interval" as a case that should work without re-sending the entire rule. This fails for the three structurally-complex subtypes. The merge logic in service.py is correct; the gap is pre-merge Pydantic validation.

**Documented disposition:** UAT classifies this as `severity: blocker`. Phase 33.1 will introduce a flat `FrequencyEditSpec` with all frequency fields optional, resolved before the discriminated union.

---

### Required Artifacts (Regression Check)

| Artifact | Modified by Plan 05 | Regression |
|----------|---------------------|------------|
| `src/omnifocus_operator/rrule/builder.py` | Yes | None -- existing single-value tests still pass |
| `src/omnifocus_operator/rrule/parser.py` | Yes | None |
| `src/omnifocus_operator/service/service.py` | Yes | None -- 17/17 TestEditTaskRepetitionRule pass |
| All other phase 33 artifacts | No | None -- 1020 total tests, mypy strict clean |

---

### Behavioral Spot-Checks

| Behavior | Result | Status |
|----------|--------|--------|
| `build_rrule(MonthlyDayInMonthFrequency(on_dates=[1, 15, -1]))` produces `"FREQ=MONTHLY;BYMONTHDAY=1,15,-1"` | Confirmed | PASS |
| `parse_rrule("FREQ=MONTHLY;BYMONTHDAY=1,15,-1")` produces correct model | Confirmed | PASS |
| `test_noop_same_rule_with_other_field_change`: warning fires AND name applied | 1 passed | PASS |
| UAT 3c: interval-only on `weekly_on_days` still raises ValidationError | ValidationError confirmed | FAIL (gap) |
| Full test suite (1020 tests) | 1020 passed in 12.63s | PASS |
| mypy strict | No issues in 49 source files | PASS |

---

### Requirements Coverage

All 35 requirements carry forward from the previous report. Plan 05 re-closes EDIT-16 (no-op) and ADD-01 (creation). Two requirements are now partial:

| Requirement | Status | Note |
|-------------|--------|------|
| EDIT-09 | PARTIAL | Merge works when submitted frequency is Pydantic-valid. Interval-only on `weekly_on_days` fails pre-merge. |
| EDIT-10 | PARTIAL | Same root cause as EDIT-09. `DailyFrequency(interval=5)` works; `WeeklyOnDaysFrequency(interval=4)` without `on_days` does not. |
| All other 33 requirements | SATISFIED | No change from previous verification. |

---

### Human Verification Required

#### 1. UAT 3c Error Message Quality

**Test:** Submit `edit_tasks` with `{id: "...", repetitionRule: {frequency: {type: "weekly_on_days", interval: 4}}}` to a live agent session.
**Expected:** Error message explains that `on_days` is required for `weekly_on_days` and ideally provides guidance on what to include.
**Why human:** The Pydantic discriminated union error message quality cannot be verified programmatically. The automated check confirms an error IS raised; whether the message is educational enough requires human judgment.

#### 2. Bridge JS repetitionRule Construction (OmniJS Runtime)

**Test:** Create a task with a daily repetition rule via `add_tasks` against live OmniFocus.
**Expected:** Task appears with correct recurrence (daily, regularly, due date anchored).
**Why human:** `reverseRst`/`reverseAdk` use OmniJS globals (`Task.RepetitionScheduleType`, `Task.AnchorDateKey`) that only exist in the OmniJS runtime.

#### 3. Partial Update Semantics End-to-End

**Test:** Create a repeating task, then send `edit_tasks` with only `{repetitionRule: {schedule: "from_completion"}}`.
**Expected:** Schedule changes, frequency and basedOn are preserved from the existing rule. Confirmed via `get_task`.
**Why human:** Requires full round-trip through the real bridge including read-back.

---

### Gaps Summary

One gap remains after Plan 05 gap closure:

Success criterion 2 is partially satisfied. Schedule, basedOn, end, and subtype-specific fields (like `onDays`) can all be changed without re-sending the entire rule. However, sending only `interval` for a structurally-complex frequency subtype (`weekly_on_days`, `monthly_day_of_week`, `monthly_day_in_month`) fails because Pydantic requires all discriminated union fields before the service merge can run.

The fix path is clear (Phase 33.1: flat `FrequencyEditSpec`). The current implementation delivers the majority of the stated partial-update benefit, with a specific and documented exception.

---

_Verified: 2026-03-29T00:08:44Z_
_Verifier: Claude (gsd-verifier)_
_Mode: Re-verification after Plan 05 gap closure_
