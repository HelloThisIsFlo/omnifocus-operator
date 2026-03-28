---
created: 2026-03-28T20:07:35.108Z
title: "Fix D-05: Support BYSETPOS for multi-day positional BYDAY rules"
area: rrule
files:
  - src/omnifocus_operator/rrule/parser.py
  - tests/test_rrule.py
---

## Problem

D-05 rejects all `BYSETPOS` rules with an educational error, assuming OmniFocus always uses the prefix form (`BYDAY=2TU`). This assumption is correct for single-day rules but **wrong for multi-day positional rules**.

The OmniFocus UI offers "weekday" and "weekend day" as day options in the monthly repeat picker. These expand to multi-day BYDAY + BYSETPOS, which the prefix form cannot express:

- "1st weekend day" → `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1`
- "2nd weekday" → `FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2`

There's no prefix equivalent — you can't write `1SU,SA` or `2MO,TU,WE,TH,FR`.

**Impact**: Any `edit_tasks` or `get_task` call can crash if the read path encounters a task with a multi-day BYSETPOS rule anywhere in the database. During UAT, this blocked all `beginning`/`ending` move operations (the "Do Monthly Review" task was the culprit).

## Root Cause

`_validate_no_bysetpos()` in `parser.py:149` unconditionally rejects any rule containing `BYSETPOS`.

## Evidence from Real Database (466 repeating tasks, 60 distinct rules)

**Single-day positional → always prefix form** (D-05 correct here):
- `BYDAY=-1SA`, `BYDAY=1SA`, `BYDAY=2TU`, `BYDAY=-1FR`, `BYDAY=3SU`, etc.
- Zero instances of single-day BYSETPOS (e.g., `BYDAY=TU;BYSETPOS=2` never appears)

**Multi-day positional → always BYSETPOS** (D-05 wrong here):
- `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1` (2 tasks — "Do Monthly Review")
- `FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2` (confirmed via live UI experiment)

## Fix

- Remove `_validate_no_bysetpos()` rejection
- Support BYSETPOS when BYDAY contains multiple day codes
- The structured model needs to represent this — likely `on: {"second": "weekday"}` or `on: {"first": "weekend_day"}` (check milestone spec, `weekend_day`/`weekday` are already listed as valid day values)
- Keep prefix-only parsing for single-day BYDAY (no change needed there)
- Add test cases:
  - `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=1` → first weekend day
  - `FREQ=MONTHLY;BYDAY=MO,TU,WE,TH,FR;BYSETPOS=2` → second weekday
  - `FREQ=MONTHLY;BYDAY=SU,SA;BYSETPOS=-1` → last weekend day (plausible)
- Update D-05 in phase 32 context docs to reflect the corrected understanding

## Why D-05 Was Wrong

The original research (PITFALLS.md, FINDINGS.md) actually contained the counterexample `BYDAY=SU,SA;BYSETPOS=1` in the real data, but the live query during the Phase 32 discussion only validated a single-day rule (`BYDAY=2TU`). The multi-day case was missed because it's rare (2 out of 466 tasks) and the "interchangeable" claim was only tested against single-day rules.

## Related

- Separate from Frequency model refactor (2026-03-28-refactor-frequency-to-flat-model)
- Separate from repetition rule write support (2026-03-10)
- This is a read-side parser fix
