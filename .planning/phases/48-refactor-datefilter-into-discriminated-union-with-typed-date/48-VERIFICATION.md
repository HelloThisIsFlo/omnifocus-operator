---
phase: 48-refactor-datefilter-into-discriminated-union-with-typed-date
verified: 2026-04-10T17:30:00Z
status: passed
score: 5/5 must-haves verified
overrides_applied: 0
---

# Phase 48: Refactor DateFilter into Discriminated Union Verification Report

**Phase Goal:** Replace flat DateFilter with 4-model discriminated union, type before/after bounds as Literal["now"] | AwareDatetime | date | None, cascade through resolver and tests
**Verified:** 2026-04-10T17:30:00Z
**Status:** PASSED
**Re-verification:** No — initial verification

## Requirements Coverage Note

The plans declare `UNION-01` through `UNION-08` as requirement IDs. These IDs appear only in `ROADMAP.md` (Phase 48 metadata) and not in `.planning/REQUIREMENTS.md`, which tracks the v1.3.2 milestone requirements (DATE-*, RESOLVE-*, EXEC-*, BREAK-*). The UNION-* IDs are phase-internal requirement labels used for plan traceability; the v1.3.2 REQUIREMENTS.md has no corresponding rows. This is consistent — Phase 48 is a structural refactor (not a new capability) and the v1.3.2 requirements document tracks feature behavior, not internal structural quality. No REQUIREMENTS.md rows are orphaned.

## Goal Achievement

### Observable Truths

| # | Truth | Status | Evidence |
|---|-------|--------|----------|
| 1 | DateFilter is a discriminated union of ThisPeriodFilter, LastPeriodFilter, NextPeriodFilter, AbsoluteRangeFilter with callable Discriminator routing | VERIFIED | `_date_filter.py` defines 4 concrete `QueryModel` subclasses. `DateFilter = Annotated[Union[...], Discriminator(_route_date_filter)]` at line 127. `_route_date_filter` routes by dict key presence, defaults to `absolute_range`. Smoke test confirmed all 4 branches dispatch correctly. |
| 2 | Naive datetimes rejected structurally via BeforeValidator on before/after fields | VERIFIED | `_reject_naive_datetime` BeforeValidator on both `before` and `after` fields in `AbsoluteRangeFilter`. Checks `T` in string + lack of timezone indicator. Smoke test confirmed `2026-04-01T14:00:00` raises educational error with "timezone" message. |
| 3 | Resolver uses isinstance dispatch on concrete classes, parse functions accept typed values | VERIFIED | `resolve_dates.py` lines 130-143: `isinstance(df, ThisPeriodFilter)` ... `isinstance(df, AbsoluteRangeFilter)` dispatch. `_parse_absolute_after`/`_parse_absolute_before` accept `str | datetime | date` typed values. `_is_date_only` deleted (0 occurrences). No `datetime.fromisoformat` in parse functions. No attribute probing (`df.this is not None` patterns absent). |
| 4 | domain.py isinstance targets AbsoluteRangeFilter for defer hint detection | VERIFIED | `domain.py` line 60: `from omnifocus_operator.contracts.use_cases.list._date_filter import AbsoluteRangeFilter` (runtime import, not TYPE_CHECKING). Line 187: `isinstance(value, AbsoluteRangeFilter)`. No remaining `isinstance(value, DateFilter)`. |
| 5 | Full test suite passes with all constructions migrated to concrete classes | VERIFIED | `uv run pytest -x -q` → 1931 passed. No `DateFilter(...)` constructions remain in test files. `test_date_filter_contracts.py`, `test_resolve_dates.py`, `test_service_domain.py` all use concrete classes. NOW fixture tz-aware (`datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)`). |

**Score:** 5/5 truths verified

### Required Artifacts

| Artifact | Expected | Status | Details |
|----------|----------|--------|---------|
| `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py` | 4 concrete filter models + callable discriminator + DateFilter type alias | VERIFIED | All 4 classes present (`ThisPeriodFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `AbsoluteRangeFilter`). `_route_date_filter` callable discriminator. `DateFilter` is `Annotated[Union[...], Discriminator(...)]` type alias. No `class DateFilter(QueryModel)`. `BeforeValidator(_reject_naive_datetime)` on both bounds fields. |
| `src/omnifocus_operator/agent_messages/errors.py` | 5 dead constants deleted, 2 new constants added | VERIFIED | 0 occurrences of `DATE_FILTER_MIXED_GROUPS`, `DATE_FILTER_MULTIPLE_SHORTHAND`, `DATE_FILTER_INVALID_THIS_UNIT`, `DATE_FILTER_INVALID_ABSOLUTE`, `DATE_FILTER_EMPTY`. `ABSOLUTE_RANGE_FILTER_EMPTY` at line 132, `DATE_FILTER_NAIVE_DATETIME` at line 138. |
| `src/omnifocus_operator/agent_messages/descriptions.py` | 9 new description constants, DATE_FILTER_DOC removed | VERIFIED | 0 occurrences of `DATE_FILTER_DOC`. `THIS_PERIOD_FILTER_DOC`, `LAST_PERIOD_FILTER_DOC`, `NEXT_PERIOD_FILTER_DOC`, `ABSOLUTE_RANGE_FILTER_DOC`, `THIS_PERIOD_UNIT`, `LAST_PERIOD_DURATION`, `NEXT_PERIOD_DURATION`, `ABSOLUTE_RANGE_BEFORE`, `ABSOLUTE_RANGE_AFTER` all present. 7 field descriptions updated to "Or use a period/range filter." (confirmed count = 7). |
| `src/omnifocus_operator/contracts/use_cases/list/__init__.py` | Re-exports all 4 concrete classes | VERIFIED | `AbsoluteRangeFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `ThisPeriodFilter` in both imports (lines 7-12) and `__all__` (lines 45, 51, 65, 68). |
| `tests/test_date_filter_contracts.py` | Contract tests using concrete model classes | VERIFIED | All concrete classes imported and used. `ThisPeriodFilter(this=`, `LastPeriodFilter(last=`, `AbsoluteRangeFilter(before=` present. No `DateFilter(this=` etc. `DATE_FILTER_NAIVE_DATETIME` tested. TypeAdapter-based discriminator routing tests present. |
| `src/omnifocus_operator/service/resolve_dates.py` | isinstance-based dispatch + typed parse functions | VERIFIED | 4 concrete imports at module level (not TYPE_CHECKING). `isinstance(df, ThisPeriodFilter/LastPeriodFilter/NextPeriodFilter/AbsoluteRangeFilter)` at lines 130-139. No `_is_date_only`. No `datetime.fromisoformat` in parse functions. WR-01 defensive fix removed. |
| `src/omnifocus_operator/service/domain.py` | AbsoluteRangeFilter isinstance check | VERIFIED | Runtime import at line 60. `isinstance(value, AbsoluteRangeFilter)` at line 187. |
| `tests/test_resolve_dates.py` | Tests using concrete filter classes with tz-aware NOW | VERIFIED | `ThisPeriodFilter` imported and used. `NOW = datetime(2026, 4, 7, 14, 0, 0, tzinfo=UTC)`. No `DateFilter(` constructions. |
| `tests/test_service_domain.py` | Tests using concrete filter classes | VERIFIED | `AbsoluteRangeFilter`, `ThisPeriodFilter` imported. 9 `DateFilter(` constructions replaced. Defer hint tests use `AbsoluteRangeFilter(after="now")`. |

### Key Link Verification

| From | To | Via | Status | Details |
|------|----|-----|--------|---------|
| `_date_filter.py` | `agent_messages/errors.py` | `err.ABSOLUTE_RANGE_FILTER_EMPTY` | WIRED | `AbsoluteRangeFilter._validate_bounds` raises `ValueError(err.ABSOLUTE_RANGE_FILTER_EMPTY)` at line 99. `_reject_naive_datetime` raises `ValueError(err.DATE_FILTER_NAIVE_DATETIME)` at line 31. |
| `_date_filter.py` | `agent_messages/descriptions.py` | `desc.THIS_PERIOD_FILTER_DOC`, `desc.ABSOLUTE_RANGE_FILTER_DOC`, etc. | WIRED | All 4 model `__doc__` and all 5 field `description=` assignments reference description constants. |
| `contracts/use_cases/list/__init__.py` | `_date_filter.py` | re-export concrete classes | WIRED | `AbsoluteRangeFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `ThisPeriodFilter` imported and in `__all__`. |
| `resolve_dates.py` | `_date_filter.py` | runtime imports for isinstance dispatch | WIRED | `from omnifocus_operator.contracts.use_cases.list._date_filter import AbsoluteRangeFilter, LastPeriodFilter, NextPeriodFilter, ThisPeriodFilter` at module level (lines 16-21). |
| `domain.py` | `_date_filter.py` | runtime import for isinstance | WIRED | `from omnifocus_operator.contracts.use_cases.list._date_filter import AbsoluteRangeFilter` at line 60. Used at line 187. |

### Data-Flow Trace (Level 4)

Not applicable — this phase is a structural refactor. All artifacts are contract/validation models and service dispatch logic, not components that render dynamic data from external sources. The data flow is validated by the full test suite (1931 tests passing).

### Behavioral Spot-Checks

| Behavior | Command | Result | Status |
|----------|---------|--------|--------|
| Discriminator routes all 4 variants | `TypeAdapter(DateFilter).validate_python({this/last/next/before key})` | All 4 concrete types confirmed | PASS |
| Naive datetime rejected with educational error | `TypeAdapter(DateFilter).validate_python({'before': '2026-04-01T14:00:00'})` | ValidationError with "timezone" message | PASS |
| Empty AbsoluteRangeFilter rejected | `TypeAdapter(DateFilter).validate_python({})` | ValidationError with "requires at least one of" | PASS |
| Non-dict input rejected | `TypeAdapter(DateFilter).validate_python(42)` | ValidationError raised | PASS |
| Date-only parses as `date` type | `AbsoluteRangeFilter(before='2026-04-14').before` | `isinstance(result, date)` True | PASS |
| Tz-aware datetime parses as `AwareDatetime` | `AbsoluteRangeFilter(before='2026-04-14T14:00:00Z').before` | `isinstance(result, datetime)` with tzinfo | PASS |
| Resolver isinstance dispatch (ThisPeriod) | `resolve_date_filter(ThisPeriodFilter(this='d'), 'due', NOW)` | Both `after` and `before` non-None | PASS |
| Resolver isinstance dispatch (AbsoluteRange) | `resolve_date_filter(AbsoluteRangeFilter(after='now'), 'due', NOW)` | `after == NOW`, `before is None` | PASS |
| Full test suite | `uv run pytest -x -q` | 1931 passed in 16.38s | PASS |

### Requirements Coverage

| Requirement | Source Plan | Description | Status | Evidence |
|-------------|------------|-------------|--------|----------|
| UNION-01 | 48-01 | 4-model discriminated union structure | SATISFIED | `_date_filter.py` defines `ThisPeriodFilter`, `LastPeriodFilter`, `NextPeriodFilter`, `AbsoluteRangeFilter` with `Discriminator(_route_date_filter)` |
| UNION-02 | 48-01 | Naive datetime rejection via BeforeValidator | SATISFIED | `_reject_naive_datetime` BeforeValidator on `before`/`after` fields; educational error `DATE_FILTER_NAIVE_DATETIME` |
| UNION-03 | 48-01 | Empty AbsoluteRangeFilter rejected | SATISFIED | `_validate_bounds` model_validator raises `ABSOLUTE_RANGE_FILTER_EMPTY` when both fields are None |
| UNION-04 | 48-01 | Non-dict input routed to absolute_range for Pydantic rejection | SATISFIED | `_route_date_filter` returns `"absolute_range"` for non-dict inputs; smoke test confirms ValidationError |
| UNION-05 | 48-01 | Dead error constants removed, new constants added; description constants updated | SATISFIED | 5 dead constants deleted, 2 new added; `DATE_FILTER_DOC` removed, 9 new description constants; 7 field descriptions updated |
| UNION-06 | 48-02 | Resolver uses isinstance dispatch, parse functions accept typed values | SATISFIED | `_resolve_date_filter_obj` uses `isinstance` on all 4 classes; `_parse_absolute_after/before` accept `str\|datetime\|date` |
| UNION-07 | 48-02 | `_is_date_only` deleted, WR-01 defensive fix removed; domain.py targets AbsoluteRangeFilter | SATISFIED | 0 occurrences of `_is_date_only`; `domain.py` line 187 uses `isinstance(value, AbsoluteRangeFilter)` |
| UNION-08 | 48-02 | All test files migrated to concrete classes; full suite passes | SATISFIED | 0 `DateFilter(` in test files; `uv run pytest -x -q` → 1931 passed |

**Note on REQUIREMENTS.md coverage:** UNION-* IDs are not present in `.planning/REQUIREMENTS.md` (which tracks v1.3.2 behavioral requirements DATE-*, RESOLVE-*, etc.). Phase 48 is an internal structural refactor; its requirements are self-contained to the ROADMAP.md phase definition. No REQUIREMENTS.md rows are orphaned by this phase.

### Anti-Patterns Found

| File | Line | Pattern | Severity | Impact |
|------|------|---------|----------|--------|
| None found | — | — | — | — |

No TODO, FIXME, placeholder, or stub patterns found in any of the 9 modified files. All implementations are substantive.

### Human Verification Required

None. All phase behaviors are structural (contract validation, isinstance dispatch) and are fully verifiable programmatically. The full test suite (1931 tests) covers all observable behaviors. No UI, real-time behavior, or external service integration is involved.

## Gaps Summary

No gaps. All 5 roadmap success criteria are verified against the actual codebase.

---

_Verified: 2026-04-10T17:30:00Z_
_Verifier: Claude (gsd-verifier)_
