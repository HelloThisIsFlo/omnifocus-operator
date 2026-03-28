---
status: partial
phase: 33-write-model-validation-bridge
source: [33-VERIFICATION.md]
started: 2026-03-28T22:00:00Z
updated: 2026-03-28T22:00:00Z
---

## Current Test

[awaiting human testing]

## Tests

### 1. EDIT-14 Error Message Quality
expected: Error message explains that `onDays` is required for `weekly_on_days` type, mentioning valid frequency types — educational, not cryptic Pydantic dump
result: [pending]

### 2. Bridge JS repetitionRule Construction (OmniJS Runtime)
expected: Task created via `add_tasks` with daily repetition rule appears in OmniFocus with correct recurrence (daily, regularly, due date anchored)
result: [pending]

### 3. Partial Update Semantics End-to-End
expected: After editing only `schedule` on a repeating task, frequency and basedOn are preserved from existing rule — verified via `get_task` round-trip
result: [pending]

## Summary

total: 3
passed: 0
issues: 0
pending: 3
skipped: 0
blocked: 0

## Gaps
