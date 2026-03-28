---
status: diagnosed
phase: 32-read-model-rewrite
source: 32-01-SUMMARY.md, 32-02-SUMMARY.md
started: 2026-03-28T15:00:00Z
updated: 2026-03-28T15:10:00Z
retroactive: true
note: "UAT was performed during phase 32.1 testing cycle. Phase 32 was verified (16/16) but UAT was skipped — issues surfaced when 32.1 exercised the models end-to-end."
---

## Current Test

[testing complete]

## Tests

### 1. All 8 frequency types parse from RRULE strings
expected: parse_rrule produces correct structured output for minutely, hourly, daily, weekly, monthly (3 variants), yearly
result: pass

### 2. RepetitionRule exposes structured fields
expected: Task.repetition_rule has frequency/schedule/basedOn/end — not ruleString/scheduleType/anchorDateKey/catchUpAutomatically
result: pass

### 3. Round-trip parse/build/parse is identity
expected: For all 8 frequency types, parse_rrule(build_rrule(parse_rrule(rrule))) equals parse_rrule(rrule)
result: pass

### 4. Both read paths produce identical output
expected: SQLite and bridge read paths share the same rrule module and produce identical structured output for the same raw data
result: pass

### 5. Schedule enum derives correctly from raw columns
expected: regularly, regularly_with_catch_up, and from_completion all derive correctly from scheduleType + catchUpAutomatically
result: pass

### 6. WeeklyFrequency omits onDays when unset
expected: A bare weekly repetition rule (no specific days) serializes as {"type": "weekly", "interval": 1} — no onDays field present
result: issue
reported: "WeeklyFrequency emits onDays: null when no specific days are selected. Should split into WeeklyFrequency (bare) and WeeklyOnDaysFrequency (type: weekly_on_days, on_days required) following the monthly pattern."
severity: major

### 7. from_completion with catchUpAutomatically=true maps correctly
expected: A from_completion repetition rule with catchUpAutomatically=true maps to the from_completion schedule category without error
result: issue
reported: "from_completion + catchUpAutomatically=true crashes instead of mapping. Server throws data corruption error. This is normal OmniFocus behavior — the flag has no effect in from_completion context."
severity: blocker

## Summary

total: 7
passed: 5
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "A bare weekly repetition rule serializes without onDays field"
  status: failed
  reason: "User reported: WeeklyFrequency emits onDays: null when no specific days are selected."
  severity: major
  test: 6
  root_cause: "WeeklyFrequency has on_days: list[str] | None = None as single model. Pydantic serializes None fields."
  artifacts:
    - path: "src/omnifocus_operator/models/repetition_rule.py"
      issue: "WeeklyFrequency carries optional on_days — needs split into bare + on_days variant"
  missing:
    - "Split into WeeklyFrequency (bare) + WeeklyOnDaysFrequency (on_days required)"
  fix_plan: ".planning/phases/32.1-output-schema-validation-gap/32.1-03-PLAN.md"

- truth: "from_completion + catchUpAutomatically=true maps to from_completion schedule without error"
  status: failed
  reason: "User reported: from_completion + catchUpAutomatically=true crashes. OmniFocus UI legitimately produces this state."
  severity: blocker
  test: 7
  root_cause: "_derive_schedule() raises ValueError for from_completion + catch_up=True — duplicated in adapter.py and hybrid.py"
  artifacts:
    - path: "src/omnifocus_operator/bridge/adapter.py"
      issue: "_derive_schedule raises ValueError for valid real-world state"
    - path: "src/omnifocus_operator/repository/hybrid.py"
      issue: "Duplicate _derive_schedule with same incorrect ValueError"
  missing:
    - "Accept either catch_up value for from_completion — extract to shared rrule/schedule.py"
  fix_plan: ".planning/phases/32.1-output-schema-validation-gap/32.1-02-PLAN.md"
