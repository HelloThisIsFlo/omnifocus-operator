---
created: 2026-03-03T20:56:38.420Z
title: Redesign RepetitionRule model with full OmniFocus fields
area: models
files:
  - src/omnifocus_operator/models/_common.py:13-25
  - src/omnifocus_operator/bridge/bridge.js:26-33
  - .research/Deep Dives/Repetition Rule/repetition-rule-guide.md
  - .planning/debug/repetition-rule-validation-failure.md
---

## Problem

The RepetitionRule Pydantic model currently has only 2 fields (`rule_string`, `schedule_type`) based on an outdated understanding of the OmniFocus API. The `schedule_type` field is temporarily optional (`str | None = None`) as a workaround because OmniFocus's `scheduleType.name` returns `undefined` in the JS runtime — see debug session `repetition-rule-validation-failure.md`.

The real OmniFocus `Task.RepetitionRule` object exposes **4 usable fields** (a 5th is deprecated and always null). The deep dive research in `.research/Deep Dives/Repetition Rule/repetition-rule-guide.md` documents all of them with their types, semantics, and edge cases.

The current state is explicitly marked TEMPORARY in the code (see `_common.py` docstring).

## Solution

Insert a follow-up phase to:

1. **Update the spec** — incorporate the 4-field RepetitionRule structure from the deep dive research
2. **Redesign the Pydantic model** — replace the 2-field model with all 4 fields as **required** (no optional workarounds)
3. **Update bridge.js `rr()` function** — extract all 4 fields from OmniFocus, not just `ruleString` and `scheduleType`
4. **Update JS bridge tests** — cover the new extraction logic
5. **Update Python model tests** — cover serialization/deserialization of all 4 fields
6. **Update seed data** — any InMemoryBridge seed data with repetition rules needs all 4 fields
7. **Re-run UAT** — verify against live OmniFocus that all 4 fields populate correctly

### Key references

- Deep dive research: `.research/Deep Dives/Repetition Rule/repetition-rule-guide.md`
- Debug session (root cause): `.planning/debug/repetition-rule-validation-failure.md`
- Temporary fix commit: `8c79c1f`
- TEMPORARY marker in code: `src/omnifocus_operator/models/_common.py:15-19`
