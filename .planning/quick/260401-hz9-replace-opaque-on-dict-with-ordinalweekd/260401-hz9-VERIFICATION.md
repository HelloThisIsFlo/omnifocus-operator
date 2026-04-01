---
phase: quick-260401-hz9
verified: 2026-04-01T00:00:00Z
status: passed
score: 5/5 must-haves verified
re_verification: false
---

# Quick Task 260401-hz9: Replace opaque on: dict with OrdinalWeekday — Verification Report

**Task Goal:** Replace opaque `on: dict` with `OrdinalWeekday` model for JSON Schema clarity
**Verified:** 2026-04-01
**Status:** passed
**Re-verification:** No — initial verification

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | JSON Schema for `on` field exposes 6 named ordinal fields with DayName enum, not opaque additionalProperties | VERIFIED | `Frequency.model_json_schema()["$defs"]["OrdinalWeekday"]` shows 6 properties (first/second/third/fourth/fifth/last), each with `enum: [monday, tuesday, ..., weekend_day]` and `additionalProperties: false` |
| 2 | Wire format unchanged: `{"last": "friday"}` round-trips through add/edit/read | VERIFIED | `Frequency(type="monthly", on={"last": "friday"}).model_dump(exclude_defaults=True)` returns `{"type": "monthly", "on": {"last": "friday"}}` |
| 3 | Empty `on: {}` still flows through gracefully with warning (no crash) | VERIFIED | `Frequency(type="monthly", on={})` creates `OrdinalWeekday` with all None fields; domain.py checks `all(getattr(frequency.on, f) is None ...)` at line 266 and normalizes to `on=None` + warning |
| 4 | At-most-one validator rejects `{"first": "monday", "last": "friday"}` | VERIFIED | `OrdinalWeekday(first="monday", last="friday")` raises `ValidationError`; `check_at_most_one_ordinal()` standalone function counts non-None fields and raises if > 1 |
| 5 | All existing tests pass after migration (no behavioral regression) | VERIFIED | Full test suite: **1395 passed**, 0 failed, 98.13% coverage |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/models/repetition_rule.py` | OrdinalWeekday model, DayName type, normalize_day_name(), check_at_most_one_ordinal() | VERIFIED | Class `OrdinalWeekday` at line 102; `DayName` Literal at line 41; `normalize_day_name()` at line 83; `check_at_most_one_ordinal()` at line 91; all exported in `__all__` |
| `src/omnifocus_operator/contracts/shared/repetition_rule.py` | OrdinalWeekdaySpec with CommandModel base | VERIFIED | Class `OrdinalWeekdaySpec(CommandModel)` at line 55 with identical 6 ordinal fields, field_validator, and model_validator; `FrequencyAddSpec.on: OrdinalWeekdaySpec | None`; `FrequencyEditSpec.on: PatchOrClear[OrdinalWeekdaySpec]` |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `rrule/parser.py` | `models/repetition_rule.py` | Constructs `OrdinalWeekday(last="friday")` instead of dict | WIRED | Lines 211, 245: `on=OrdinalWeekday(**{ordinal: day_name})` in both `_parse_monthly_byday` and `_parse_monthly_bysetpos` |
| `rrule/builder.py` | `models/repetition_rule.py` | Extracts single set field from OrdinalWeekday | WIRED | `_build_byday_positional(on: OrdinalWeekday)` at line 118; field extraction via `on.first`, `on.second`, etc. at lines 126-134 |
| `service/domain.py` | `models/repetition_rule.py` | Empty OrdinalWeekday detection | WIRED | Line 266: `all(getattr(frequency.on, f) is None for f in _ordinal_fields)`; Line 312: `edit_val.model_dump(exclude_defaults=True)` boundary for Spec→Core conversion |

### Data-Flow Trace (Level 4)

Not applicable — this task produces model/schema infrastructure, not UI components rendering dynamic data. The wire format round-trip (Truth 2) covers the data-flow contract directly.

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| JSON Schema shows 6 ordinal fields with DayName enum | `python -c "from ... import Frequency; Frequency.model_json_schema()['$defs']['OrdinalWeekday']"` | 6 properties, each with 9-value enum, `additionalProperties: false` | PASS |
| Wire format `{"last": "friday"}` round-trips | `model_dump(exclude_defaults=True)` | `{"type": "monthly", "on": {"last": "friday"}}` | PASS |
| At-most-one validator fires | `OrdinalWeekday(first="monday", last="friday")` | ValidationError raised | PASS |
| Empty `on: {}` accepted | `Frequency(type="monthly", on={})` | OrdinalWeekday with all-None fields, no exception | PASS |
| Case normalization | `OrdinalWeekday(first="MONDAY").first` | `"monday"` | PASS |
| Full test suite | `uv run pytest tests/ -x -q` | 1395 passed | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|-------------|-------------|--------|----------|
| hz9-01 | 260401-hz9-PLAN.md | Replace opaque `on: dict` with typed OrdinalWeekday model | SATISFIED | OrdinalWeekday/OrdinalWeekdaySpec models exist; all consumers updated; JSON Schema structured; `normalize_on()` removed |

### Anti-Patterns Found

None. Scan of all 12 modified files shows:
- No TODO/FIXME/placeholder comments in implementation files
- No stub implementations or empty returns in new code
- `normalize_on()` removed as planned (no dead code left)
- `REPETITION_INVALID_ORDINAL` removed (was dead code after `normalize_on()` removal)
- `_VALID_ORDINALS` set removed (replaced by field names in OrdinalWeekday)

### Human Verification Required

None. All observable truths are fully verifiable programmatically.

### Gaps Summary

No gaps. All 5 must-haves verified against the actual codebase:

- JSON Schema produces structured, agent-readable schema with named ordinal fields and DayName enum (9 values per field)
- Wire format `{"last": "friday"}` round-trips correctly through `model_dump(exclude_defaults=True)` — Pydantic's recursive exclude_defaults handles nested OrdinalWeekday serialization without needing `@model_serializer`
- Empty `on: {}` coercion to all-None OrdinalWeekday is graceful; domain.py detection updated to match
- At-most-one validator (allows 0 or 1 set fields, rejects 2+) is enforced in both OrdinalWeekday and OrdinalWeekdaySpec
- 1395 tests pass with 98% coverage — no behavioral regression

---

_Verified: 2026-04-01_
_Verifier: Claude (gsd-verifier)_
