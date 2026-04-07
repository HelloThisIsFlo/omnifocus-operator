---
created: 2026-03-03T20:56:38.420Z
title: Redesign RepetitionRule model with full OmniFocus fields
area: models
files:
  - src/omnifocus_operator/models/_common.py:13-25
  - src/omnifocus_operator/bridge/bridge.js:26-33
  - src/omnifocus_operator/models/_enums.py
  - .research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md
  - .research/deep-dives/repetition-rule/repetition-rule-guide.md
  - .planning/debug/repetition-rule-validation-failure.md
---

## Problem

The RepetitionRule Pydantic model currently has only 2 fields (`rule_string`, `schedule_type`)
based on an outdated understanding of the OmniFocus API. The `schedule_type` field is temporarily
optional (`str | None = None`) as a workaround because OmniFocus's enum `.name` returns
`undefined` in the JS runtime — see debug session `repetition-rule-validation-failure.md`.

BRIDGE-SPEC Section 2.6 confirms RepetitionRule has **4 readable properties**, all required:
`ruleString`, `scheduleType`, `anchorDateKey`, `catchUpAutomatically`.

Both `scheduleType` and `anchorDateKey` are **opaque enums** that MUST be resolved via `===`
comparison against known constants — `.name` does NOT work (confirmed by BRIDGE-SPEC Section 3:
"All enums are opaque — `.name` returns `undefined`"). This is the same root cause as the
status enum bug in todo 3.

**Note:** The repetition-rule-guide.md uses `.name` for reading enums in its examples (e.g.,
`r.scheduleType.name`). This is **incorrect per BRIDGE-SPEC** — BRIDGE-SPEC is the source of
truth (empirically verified with live scripts).

**Source of truth:** `.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md` Section 2.6

## Solution

### 1. Bridge: add enum resolvers for RepetitionRule (JavaScript)

Create two new `===` switch resolvers (same pattern as `ts()` and the per-entity status
resolvers from todo 3):

- **`rst(s)` — RepetitionScheduleType** (3 values):
  `Task.RepetitionScheduleType.Regularly` -> `"Regularly"`,
  `Task.RepetitionScheduleType.FromCompletion` -> `"FromCompletion"`,
  `Task.RepetitionScheduleType.None` -> `"None"`.
  Throw on unknown with `String(s)`.

- **`adk(s)` — AnchorDateKey** (3 values):
  `Task.AnchorDateKey.DueDate` -> `"DueDate"`,
  `Task.AnchorDateKey.DeferDate` -> `"DeferDate"`,
  `Task.AnchorDateKey.PlannedDate` -> `"PlannedDate"`.
  Throw on unknown with `String(s)`.

### 2. Bridge: update `rr()` function to extract all 4 fields

Replace current `rr()` (lines 26-33) which only extracts `ruleString` and broken
`scheduleType.name`:

```javascript
function rr(v) {
    if (!v) return null;
    return {
        ruleString: v.ruleString,
        scheduleType: rst(v.scheduleType),
        anchorDateKey: adk(v.anchorDateKey),
        catchUpAutomatically: v.catchUpAutomatically,
    };
}
```

### 3. Python: add two new enums

In `_enums.py`, add:

- **`ScheduleType(StrEnum)`**: `REGULARLY = "Regularly"`, `FROM_COMPLETION = "FromCompletion"`,
  `NONE = "None"`
- **`AnchorDateKey(StrEnum)`**: `DUE_DATE = "DueDate"`, `DEFER_DATE = "DeferDate"`,
  `PLANNED_DATE = "PlannedDate"`

### 4. Python: redesign RepetitionRule model

Replace the 2-field model in `_common.py` with all 4 fields as **required** (no optional
workarounds). Use typed enums, not `str`:

- `rule_string: str` (the ICS RRULE string)
- `schedule_type: ScheduleType` (was `str | None = None`)
- `anchor_date_key: AnchorDateKey` (new field)
- `catch_up_automatically: bool` (new field)

Remove the `# TEMPORARY` comment block.

### 5. Update bridge JS tests

- Add tests for `rst()` and `adk()` resolvers (known values + unknown value throw)
- Update `rr()` tests to verify all 4 fields are extracted
- Test `rr(null)` still returns `null`

### 6. Update Python model tests

- Update RepetitionRule serialization/deserialization tests for all 4 fields
- Test that `schedule_type` and `anchor_date_key` validate against their enum types
- Remove any tests for `schedule_type: None` (no longer optional)

### 7. Update seed data

Any InMemoryBridge seed data with repetition rules needs all 4 fields populated.

### 8. Re-run UAT

Verify against live OmniFocus that all 4 fields populate correctly with the new
`===` resolvers. This is the definitive test — BRIDGE-SPEC was derived from this
exact environment.

### Key references

- BRIDGE-SPEC (authoritative): `.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md`
- Deep dive research (useful context, but .name examples are wrong): `.research/deep-dives/repetition-rule/repetition-rule-guide.md`
- Debug session (root cause): `.planning/debug/repetition-rule-validation-failure.md`
- Temporary fix commit: `8c79c1f`
- TEMPORARY marker in code: `src/omnifocus_operator/models/_common.py:15-19`
