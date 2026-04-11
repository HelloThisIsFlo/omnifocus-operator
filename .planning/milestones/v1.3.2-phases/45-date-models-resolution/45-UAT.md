---
status: diagnosed
phase: 45-date-models-resolution
source: [45-01-SUMMARY.md, 45-02-SUMMARY.md, 45-03-SUMMARY.md]
started: 2026-04-08T10:00:00Z
updated: 2026-04-08T10:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. DateFilter Validation & Error Quality
expected: DateFilter rejects invalid combinations (shorthand + absolute mixed) and invalid formats (this="2w") with educational error messages that guide the agent. Mutual exclusion between shorthand group (this/last/next) and absolute group (before/after) is enforced.
result: issue
reported: "the first one is a pass, but the second one is very confusing because the error message looks good for the other fields, but for this it's very confusing. The error says: Invalid duration '2w' -- use a number followed by d/w/m/y (e.g. '3d', '2w', 'm'). Count defaults to 1 when omitted, so 'w' means '1w'. — the message suggests '2w' is valid (it's in the example!) but this field only accepts single unit chars."
severity: major

### 2. ListTasksQuery Date Field Unions
expected: All 7 date fields on ListTasksQuery accept both their shorthand form and DateFilter dicts. Run: `uv run python -c "from omnifocus_operator.contracts.use_cases.list import ListTasksQuery; q = ListTasksQuery(due='overdue'); print(type(q.due).__name__)"` → DueDateShortcut. Run: `uv run python -c "from omnifocus_operator.contracts.use_cases.list import ListTasksQuery; q = ListTasksQuery(due={'this':'w'}); print(type(q.due).__name__)"` → DateFilter. Both forms accepted without error.
result: pass

### 3. Date Filter Resolution — Shortcuts
expected: resolve_date_filter converts shortcuts to datetime tuples. Run: `uv run python -c "from omnifocus_operator.service.resolve_dates import resolve_date_filter; from omnifocus_operator.contracts.use_cases.list._enums import DueDateShortcut; from datetime import datetime; r = resolve_date_filter(DueDateShortcut.TODAY, 'due', datetime(2026,4,8,14,30)); print(r)"` → (datetime(2026,4,8,0,0), datetime(2026,4,9,0,0)) — midnight-to-midnight bounds for "today".
result: pass

### 4. Date Filter Resolution — Relative Periods
expected: resolve_date_filter handles relative date filters. Run: `uv run python -c "from omnifocus_operator.service.resolve_dates import resolve_date_filter; from omnifocus_operator.contracts.use_cases.list import DateFilter; from datetime import datetime; r = resolve_date_filter(DateFilter(last='3d'), 'due', datetime(2026,4,8,14,30)); print(r)"` → (after, before) where after is 3 days ago at midnight and before is now. The {this: "w"} form produces calendar-aligned week boundaries.
result: pass

### 5. Week Start Configuration
expected: OPERATOR_WEEK_START env var defaults to Monday and affects week boundaries. Run: `uv run python -c "from omnifocus_operator.config import get_week_start; print(get_week_start())"` → 0 (Monday). Setting env var: `OPERATOR_WEEK_START=sunday uv run python -c "from omnifocus_operator.config import get_week_start; print(get_week_start())"` → 6 (Sunday).
result: pass

### 6. Full Test Suite Green
expected: All tests pass after phase 45 changes. Run: `uv run pytest -x -q` — expect 1777+ passed, no failures, coverage ~98%.
result: pass

### 7. DueSoon Domain Modeling
expected: resolve_date_filter's "soon" shortcut should use a domain enum (DueSoonSetting) representing OmniFocus's 7 discrete preference values, not raw interval/granularity ints that leak the SQLite storage format.
result: issue
reported: "The due_soon_interval and due_soon_granularity parameters expose SQLite internals as the public API. OmniFocus has exactly 7 discrete settings (Today, 24h, 2d, 3d, 4d, 5d, 1w) — these should be a DueSoonSetting enum. Under the hood the enum can store interval/granularity, but callers should never think in those terms. Only '24 hours' has granularity=0 (rolling); the other 6 are calendar-aligned (granularity=1)."
severity: major

### 8. Config Consolidation (pydantic-settings)
expected: All OPERATOR_* env vars should be consolidated into a single pydantic-settings Settings class in config.py, replacing scattered os.environ.get() calls across 5 files. OPERATOR_WEEK_START should be documented in docs/configuration.md. Stale OPERATOR_BRIDGE entry should be removed from docs/configuration.md. PYTEST_CURRENT_TEST is excluded (safety guard, not user config).
result: issue
reported: "7 OPERATOR_* env vars scattered across 5 source files (config.py, __main__.py, server.py, factory.py, hybrid.py) using raw os.environ.get(). Should be a pydantic-settings Settings class. OPERATOR_WEEK_START undocumented. OPERATOR_BRIDGE is stale in docs (bridges other than real are test-only). Clean up docs and consolidate."
severity: major

## Summary

total: 8
passed: 5
issues: 3
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "DateFilter rejects invalid 'this' values with educational error messages that guide the agent"
  status: failed
  reason: "User reported: error message for this='2w' says 'use a number followed by d/w/m/y (e.g. 3d, 2w, m)' — suggests '2w' is valid (it's in the example!) but this field only accepts single unit chars (d/w/m/y). The duration validator message is reused but doesn't apply to 'this'."
  severity: major
  test: 1
  root_cause: "_validate_this_unit in _date_filter.py:41-50 reuses DATE_FILTER_INVALID_DURATION error constant (errors.py:147-150) which is designed for last/next duration format. 'this' has different semantics (single unit char only) and needs its own error constant."
  artifacts:
    - path: "src/omnifocus_operator/contracts/use_cases/list/_date_filter.py"
      issue: "Line 49: uses err.DATE_FILTER_INVALID_DURATION instead of a this-specific constant"
    - path: "src/omnifocus_operator/agent_messages/errors.py"
      issue: "Lines 147-150: DATE_FILTER_INVALID_DURATION message mentions counts and '2w' example"
  missing:
    - "Add DATE_FILTER_INVALID_THIS_UNIT constant in errors.py — must NOT mention counts, only bare unit chars (d/w/m/y)"
    - "Update _validate_this_unit to use the new constant"
    - "Update test_date_filter_contracts.py to verify correct error message"
  debug_session: ""

- truth: "resolve_date_filter 'soon' shortcut uses domain-appropriate DueSoonSetting enum, not raw interval/granularity ints"
  status: failed
  reason: "User reported: due_soon_interval and due_soon_granularity leak SQLite storage format into domain API. OmniFocus has 7 discrete settings (Today/24h/2d/3d/4d/5d/1w) — should be a DueSoonSetting enum. Mapping: Today(86400,1), 24h(86400,0), 2d(172800,1), 3d(259200,1), 4d(345600,1), 5d(432000,1), 1w(604800,1). Only 24h is rolling (granularity=0), rest are calendar-aligned."
  severity: major
  test: 7
  root_cause: "resolve_date_filter (resolve_dates.py:21-28) takes raw due_soon_interval/due_soon_granularity ints because the function was designed pre-enum as a pure resolver. No DueSoonSetting enum existed — DueDateShortcut defines 'soon' as a filter value but has no config attached. The raw ints flow through to _resolve_shortcut (line 54-55), validation (line 82), and _compute_soon_threshold (lines 231-240)."
  artifacts:
    - path: "src/omnifocus_operator/service/resolve_dates.py"
      issue: "Lines 21-28: signature takes due_soon_interval/due_soon_granularity as raw ints"
    - path: "src/omnifocus_operator/service/resolve_dates.py"
      issue: "Lines 231-240: _compute_soon_threshold uses raw interval/granularity"
    - path: "tests/test_resolve_dates.py"
      issue: "Lines 71-112: TestSoonShortcut passes raw ints (172800/1, 86400/0)"
    - path: "src/omnifocus_operator/contracts/use_cases/list/_enums.py"
      issue: "No DueSoonSetting enum exists"
  missing:
    - "Create DueSoonSetting enum with 7 members mapping to (interval, granularity) tuples"
    - "Replace due_soon_interval/due_soon_granularity params with due_soon_setting: DueSoonSetting | None"
    - "Update _compute_soon_threshold to unpack from enum"
    - "Update all tests to use enum values instead of raw ints"
  debug_session: ""

- truth: "All OPERATOR_* env vars consolidated in pydantic-settings Settings class, OPERATOR_WEEK_START documented, stale OPERATOR_BRIDGE removed from docs"
  status: failed
  reason: "User reported: 7 OPERATOR_* env vars scattered across 5 source files using raw os.environ.get(). Should be a pydantic-settings Settings class in config.py. OPERATOR_WEEK_START is undocumented in docs/configuration.md. OPERATOR_BRIDGE entry in docs is stale — non-real bridges are test-only, the env var is no longer read in source. PYTEST_CURRENT_TEST excluded (safety guard)."
  severity: major
  test: 8
  root_cause: "Historical accumulation — each milestone added env var reads where needed without a centralized config strategy. pydantic-settings is not a dependency (pyproject.toml only has fastmcp). config.py exists but only has constants and get_week_start(). Env vars read at startup in factory.py (5 vars), __main__.py (1), server.py (1 duplicate), config.py (1 lazy), hybrid.py (1 duplicate)."
  artifacts:
    - path: "src/omnifocus_operator/__main__.py"
      issue: "Line 23: OPERATOR_LOG_LEVEL"
    - path: "src/omnifocus_operator/config.py"
      issue: "Line 46: OPERATOR_WEEK_START"
    - path: "src/omnifocus_operator/server.py"
      issue: "Line 103: OPERATOR_REPOSITORY (duplicate read for logging)"
    - path: "src/omnifocus_operator/repository/factory.py"
      issue: "Lines 55,71,73,86,119: OPERATOR_REPOSITORY, OPERATOR_IPC_DIR, OPERATOR_BRIDGE_TIMEOUT, OPERATOR_SQLITE_PATH, OPERATOR_OFOCUS_PATH"
    - path: "src/omnifocus_operator/repository/hybrid/hybrid.py"
      issue: "Line 598: OPERATOR_SQLITE_PATH (duplicate read)"
    - path: "docs/configuration.md"
      issue: "Lines 42-52: stale OPERATOR_BRIDGE entry; missing OPERATOR_WEEK_START"
  missing:
    - "Add pydantic-settings to pyproject.toml dependencies"
    - "Create Settings(BaseSettings) class in config.py with all 7 OPERATOR_* fields"
    - "Update __main__.py, factory.py, server.py, hybrid.py to consume Settings instead of os.environ.get()"
    - "Document OPERATOR_WEEK_START in docs/configuration.md"
    - "Remove stale OPERATOR_BRIDGE section from docs/configuration.md"
  debug_session: ""
