---
status: complete
phase: 33-write-model-validation-bridge
source: [33-01-SUMMARY.md, 33-02-SUMMARY.md, 33-03-SUMMARY.md]
started: 2026-03-28T22:00:00Z
updated: 2026-03-29T00:15:00Z
---

## Current Test

[testing complete]

## Tests

### Code Review Gaps (found by human review, fixed by gap closure 33-04)

### 4. Stale _FORWARD_DECLARED_* exclusion sets
expected: test_warnings.py consolidation test catches unwired constants — no exclusion bypass sets present
result: pass
note: fixed in df632c2 (gap closure 33-04)

### 5. REPETITION_TYPE_CHANGE_INCOMPLETE dead constant
expected: No dead/unused error constants in agent_messages/errors.py
result: pass
note: fixed in df632c2 (gap closure 33-04)

### 6. validate.py excluded from _ERROR_CONSUMERS
expected: All modules using error constants are registered in _ERROR_CONSUMERS so consolidation test catches inline strings
result: pass
note: fixed in df632c2 (gap closure 33-04)

### 7. Golden master write path coverage
expected: Golden master tests exercise the full write path including repetition rule handling in add/edit
result: skipped
reason: user handling separately — agent creates test infra, snapshot capture is human-only

### UAT Regression (33 tests run by human against live OmniFocus)

### 8. Create: daily + interval (1a)
expected: Daily freq, interval=3, regularly, due_date; structured round-trip, no ruleString
result: pass

### 9. Create: weekly_on_days (1b)
expected: onDays case-normalized to uppercase; regularly_with_catch_up; end by occurrences
result: pass

### 10. Create: monthly_day_of_week (1c)
expected: on={"second":"tuesday"}; from_completion; end by date
result: pass

### 11. Create: monthly_day_in_month (1d)
expected: onDates=[1, 15, -1] round-trips correctly
result: issue
reported: "onDates returned as [1] — values 15 and -1 were silently dropped. No warning or error, data just vanishes."
severity: blocker

### 12. Create: yearly (1e)
expected: Yearly freq; planned_date basedOn
result: pass

### 13. Edit: set rule (2a)
expected: Set complete rule on non-repeating task
result: pass

### 14. Edit: clear rule (2b)
expected: Set then clear with null; get_task confirms gone
result: pass

### 15. Partial: schedule only (3a)
expected: Change schedule; frequency/basedOn/end preserved
result: pass

### 16. Partial: basedOn only (3b)
expected: Change basedOn; others preserved
result: pass

### 17. Partial: interval only — same-type merge (3c)
expected: Sending {frequency: {type: "weekly_on_days", interval: 4}} merges with existing rule, preserving onDays
result: issue
reported: "Error 'Field required' — Pydantic validation rejects the frequency object because onDays is missing, before the merge logic can run"
severity: blocker

### 18. Partial: onDays — same-type merge (3d)
expected: Change onDays; interval preserved via same-type merge
result: pass

### 19. Partial: add end (3e)
expected: Add end condition; others preserved
result: pass

### 20. Partial: change end type (3f)
expected: Date to occurrences
result: pass

### 21. Partial: clear end (3g)
expected: end: null; others preserved
result: pass

### 22. Type change: daily to weekly (4a)
expected: Full frequency replacement; no merging
result: pass

### 23. No-op: identical rule (5a)
expected: Same rule back returns "identical" warning
result: pass

### 24. No-op: omitted + field edit (5b)
expected: No repetition warning; field change applied
result: pass

### 25. Status: completed task (6a)
expected: Set rule on completed task; "completed" warning
result: pass

### 26. Status: dropped task (6b)
expected: Set rule on dropped task; "dropped" warning
result: pass

### 27. Lifecycle: complete repeating (7a)
expected: Complete repeating task; "next occurrence created"
result: pass

### 28. Lifecycle: drop repeating (7b)
expected: Drop repeating task; "occurrence was skipped"
result: pass

### 29. Normalize: empty onDates (8a)
expected: Empty onDates normalized to monthly; warning present
result: pass

### 30. Warning: end date past (8b)
expected: End date in past; "no future occurrences" warning
result: pass

### 31. Error: invalid interval (9a)
expected: interval=0 returns clean error
result: pass

### 32. Error: invalid day code (9b)
expected: onDays=["XX"] returns clean error
result: pass

### 33. Error: invalid ordinal (9c)
expected: on={"sixth":...} returns clean error
result: pass

### 34. Error: invalid day name (9d)
expected: on={...:"funday"} returns clean error
result: pass

### 35. Error: invalid onDate (9e)
expected: onDates=[0] returns clean error
result: pass

### 36. Error: invalid end occurrences (9f)
expected: occurrences=0 returns clean error
result: pass

### 37. Error: no existing rule (9g)
expected: Partial update on non-repeating task errors
result: pass

### 38. Clean error format (10a)
expected: Missing type field; no pydantic internals leaked
result: pass
note: passes criteria, but "Unable to extract tag using discriminator 'type'" is still Pydantic-internal jargon — could be more educational

### 39. Combo: rule + field edit (11a)
expected: Set rule and flagged in same call; both applied
result: pass

### 40. Combo: no-op rule + name change (11b)
expected: No-op warning present alongside name change
result: issue
reported: "Name changed correctly, but warnings: null. No-op detection for repetition rules is suppressed when other fields are also modified in the same call."
severity: major

## Summary

total: 37
passed: 30
issues: 3
pending: 0
skipped: 1
blocked: 0

## Gaps

### Resolved (gap closure 33-04, commit df632c2)

- truth: "test_warnings.py consolidation test catches unwired constants without exclusion bypass"
  status: resolved
  test: 4

- truth: "No dead/unused error constants in agent_messages"
  status: resolved
  test: 5

- truth: "All error-constant-using modules registered in _ERROR_CONSUMERS"
  status: resolved
  test: 6

### Open

- truth: "onDates=[1, 15, -1] round-trips correctly for monthly_day_in_month"
  status: failed
  reason: "User reported: onDates returned as [1] — values 15 and -1 were silently dropped. No warning or error, data just vanishes."
  severity: blocker
  test: 11
  root_cause: "Two independent bugs in rrule module: builder (line 99) hardcodes on_dates[0], parser (lines 261-264) calls int() on raw string instead of splitting on commas"
  artifacts:
    - path: "src/omnifocus_operator/rrule/builder.py"
      issue: "Line 99: parts.append(f'BYMONTHDAY={frequency.on_dates[0]}') — only emits first value"
    - path: "src/omnifocus_operator/rrule/parser.py"
      issue: "Lines 261-264: _parse_monthly_bymonthday() calls int(bymonthday_value) — cannot parse comma-separated values"
  missing:
    - "Builder: emit all values comma-separated per RFC 5545"
    - "Parser: split on commas before parsing each int"
    - "Add multi-value BYMONTHDAY test coverage"
  debug_session: ".planning/debug/ondates-silently-dropped.md"

- truth: "Partial update with only interval on same-type frequency merges without requiring all fields"
  status: failed
  reason: "User reported: Error 'Field required' — Pydantic validation rejects the frequency object because onDays is missing, before the merge logic can run"
  severity: blocker
  test: 17
  root_cause: "Pydantic discriminated union validates frequency as complete subtype before service layer merge logic runs. Known limitation — resolved by Phase 33.1 flat frequency model refactor."
  artifacts:
    - path: "src/omnifocus_operator/contracts/use_cases/edit_task.py"
      issue: "EditTaskCommand.repetition_rule uses Frequency union which requires all subtype fields"
  missing:
    - "Phase 33.1: flat FrequencyEditSpec with optional type resolves this"

- truth: "No-op repetition rule warning fires even when other task fields are modified in same call"
  status: failed
  reason: "User reported: Name changed correctly, but warnings: null. No-op detection for repetition rules is suppressed when other fields are also modified in the same call."
  severity: major
  test: 40
  root_cause: "REPETITION_NO_OP only generated inside _all_fields_match (domain.py line 511), which short-circuits at line 496 when any other field differs (e.g. name). _apply_repetition_rule (service.py) never performs its own no-op detection."
  artifacts:
    - path: "src/omnifocus_operator/service/domain.py"
      issue: "Lines 507-511: REPETITION_NO_OP only appended inside _all_fields_match, unreachable when other fields differ"
    - path: "src/omnifocus_operator/service/service.py"
      issue: "Lines 290-379: _apply_repetition_rule lacks its own no-op detection"
  missing:
    - "Move repetition no-op detection into _apply_repetition_rule itself"
    - "Compare built payload against existing rule after merge"
    - "Append REPETITION_NO_OP and skip repo update if match"
  debug_session: ".planning/debug/noop-rep-rule-warning-lost.md"
