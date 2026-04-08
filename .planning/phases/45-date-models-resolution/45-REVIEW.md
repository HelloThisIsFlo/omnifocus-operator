---
phase: 45-date-models-resolution
reviewed: 2026-04-08T09:46:23Z
depth: standard
files_reviewed: 21
files_reviewed_list:
  - docs/configuration.md
  - pyproject.toml
  - src/omnifocus_operator/__main__.py
  - src/omnifocus_operator/agent_messages/descriptions.py
  - src/omnifocus_operator/agent_messages/errors.py
  - src/omnifocus_operator/config.py
  - src/omnifocus_operator/contracts/use_cases/list/__init__.py
  - src/omnifocus_operator/contracts/use_cases/list/_date_filter.py
  - src/omnifocus_operator/contracts/use_cases/list/_enums.py
  - src/omnifocus_operator/contracts/use_cases/list/tasks.py
  - src/omnifocus_operator/repository/factory.py
  - src/omnifocus_operator/repository/hybrid/hybrid.py
  - src/omnifocus_operator/server.py
  - src/omnifocus_operator/service/resolve_dates.py
  - tests/conftest.py
  - tests/test_date_filter_constants.py
  - tests/test_date_filter_contracts.py
  - tests/test_descriptions.py
  - tests/test_errors.py
  - tests/test_list_contracts.py
  - tests/test_resolve_dates.py
findings:
  critical: 0
  warning: 1
  info: 3
  total: 4
status: issues_found
---

# Phase 45: Code Review Report

**Reviewed:** 2026-04-08T09:46:23Z
**Depth:** standard
**Files Reviewed:** 21
**Status:** issues_found

## Summary

Phase 45 delivers three major changes:

1. **Centralized Settings via pydantic-settings** -- All `os.environ.get("OPERATOR_*")` calls migrated to a `Settings` singleton in `config.py`, with `get_settings()` / `reset_settings()` lifecycle. Factory, server, `__main__`, and hybrid repository now use the singleton. An autouse test fixture `_reset_settings_cache` in `conftest.py` ensures monkeypatched env vars propagate correctly.

2. **DueSoonSetting enum** -- Replaces raw `(interval_seconds, granularity_int)` parameters with a domain-property enum exposing `days` (int) and `calendar_aligned` (bool). The `resolve_date_filter` function signature now accepts `DueSoonSetting` instead of two raw integers. All 7 OmniFocus "due soon" threshold options are captured as enum members.

3. **DATE_FILTER_INVALID_THIS_UNIT error constant** -- Bug fix from prior review: the `this` field validator was incorrectly reusing `DATE_FILTER_INVALID_DURATION`. Now uses a dedicated constant with contextually correct guidance ("use one of: d, w, m, y").

The prior review (2026-04-07) found 3 warnings and 2 info items. **WR-01** (wrong error constant on `this` validator) and **WR-02** (`_parse_to_comparable` type mismatch crash) are both resolved. **WR-03** (pending consumer constants TODO) has been addressed with the recommended TODO comment.

The code is well-structured. Settings consolidation is clean, the DueSoonSetting enum is solid domain modeling, and test coverage is comprehensive. One warning-level issue remains plus minor observations.

## Warnings

### WR-01: `_parse_local_datetime` uses `replace(tzinfo=)` which does not resolve DST gaps

**File:** `src/omnifocus_operator/repository/hybrid/hybrid.py:168`
**Issue:** The function does `naive.replace(tzinfo=_LOCAL_TZ)` to attach timezone info. Python's `replace(tzinfo=...)` stamps a fixed UTC offset derived from the timezone for that date, but does not correctly resolve ambiguous times during DST transitions. When a local time falls in a DST "gap" (e.g., 2:30 AM on US spring-forward day), `replace` may assign the pre-transition offset, producing a wall-clock time that never existed.

With `ZoneInfo` (as used here), the behavior is better than with `pytz` -- `ZoneInfo` does consult the transition table. However, gap times remain ambiguous: `replace` defaults to `fold=0`, which selects the pre-transition offset. For OmniFocus dates this is very low risk since tasks are unlikely to have due dates precisely during a DST gap (a 1-hour window once per year). But it is technically incorrect for those edge cases.

**Fix:** If the trade-off is acceptable (and it likely is), add a comment documenting it:
```python
def _parse_local_datetime(value: str | None) -> str | None:
    if value is None:
        return None
    naive = datetime.fromisoformat(value)
    # ZoneInfo handles DST correctly for unambiguous times. For DST gap times
    # (which occur in a 1-hour window once/year), fold=0 is used (pre-transition
    # offset). This matches OmniFocus behavior -- gap times are vanishingly rare
    # in task dates.
    local_dt = naive.replace(tzinfo=_LOCAL_TZ)
    utc_dt = local_dt.astimezone(UTC)
    return utc_dt.isoformat()
```

## Info

### IN-01: Duplicated `_DATE_DURATION_PATTERN` regex

**File:** `src/omnifocus_operator/service/resolve_dates.py:19` and `src/omnifocus_operator/contracts/use_cases/list/_date_filter.py:14`
**Issue:** The regex `re.compile(r"^(\d*)([dwmy])$")` is defined independently in both files. If the pattern changes (e.g., adding hour support), both need synchronized updates.
**Fix:** Defensible as-is for layer isolation. Could extract to a shared location if the pattern grows more complex.

### IN-02: Pending description constants tracked in test

**File:** `tests/test_descriptions.py:125-133`
**Issue:** Seven description constants (`DUE_FILTER_DESC`, `COMPLETED_FILTER_DESC`, etc.) are defined and imported but listed as `pending_consumer_constants` in the description consolidation test. The TODO comment correctly tracks this for Phase 46 wiring. Flagging for visibility only.
**Fix:** No action needed now. Phase 46 should remove the exemption set when wiring these into `Field(description=...)` calls.

### IN-03: `_is_date_only` heuristic relies on upstream validation

**File:** `src/omnifocus_operator/service/resolve_dates.py:222-224`
**Issue:** `_is_date_only` checks `"T" not in value and len(value) == 10`. This works for ISO 8601 date strings but would misclassify arbitrary 10-character strings. Safe in practice because all inputs have already passed through `DateFilter._validate_absolute`.
**Fix:** Add a brief comment noting the precondition: `# Precondition: value already validated by DateFilter._validate_absolute`.

---

_Reviewed: 2026-04-08T09:46:23Z_
_Reviewer: Claude (gsd-code-reviewer)_
_Depth: standard_
