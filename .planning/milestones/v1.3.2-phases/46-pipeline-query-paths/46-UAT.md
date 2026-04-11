---
status: diagnosed
phase: 46-pipeline-query-paths
source: 46-01-SUMMARY.md, 46-02-SUMMARY.md, 46-03-SUMMARY.md
started: 2026-04-08T13:00:00Z
updated: 2026-04-08T13:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Full test suite green
expected: Run `uv run pytest -x -q` — all ~1853 tests pass, no failures or errors.
result: pass

### 2. Due-soon setting: SQLite 7-interval mapping
expected: HybridRepository._SETTING_MAP maps all 7 (DueSoonInterval, DueSoonGranularity) pairs to correct DueSoonSetting enum members. Walk through `tests/test_due_soon_setting.py::TestHybridGetDueSoonSetting` — each parametrized case inserts a pair into the Setting table and asserts the correct enum value is returned.
result: pass

### 3. Due-soon setting: Env var path
expected: BridgeOnlyRepository reads OPERATOR_DUE_SOON_THRESHOLD env var, case-insensitive matching (e.g., "one_day" -> DueSoonSetting.ONE_DAY). Walk through `tests/test_due_soon_setting.py::TestBridgeOnlyGetDueSoonSetting` — parametrized cases set the env var and assert correct enum mapping.
result: issue
reported: "Invalid env var should fail fast at startup, not at query time. Settings.due_soon_threshold is str | None — pydantic accepts any string, enum validation deferred to get_due_soon_setting() at query time. Should validate at Settings boundary (field_validator or DueSoonSetting | None type) so bad config triggers error-serving mode on boot. Error message should surface in the error file."
severity: major

### 4. Due-soon setting: Graceful None fallback
expected: Both repos return None when their source is unavailable — HybridRepository returns None for missing/unknown Setting rows, BridgeOnlyRepository returns None when env var unset. Tests: `test_returns_none_when_no_setting_rows` and `test_returns_none_when_env_var_not_set`.
result: pass

### 5. SQL date predicates: 7 dimensions with CF epoch
expected: `build_list_tasks_sql()` generates parameterized `t.{col} >= ?` and `t.{col} < ?` predicates for all 7 date dimensions (due/defer/planned/completed/dropped/added/modified). Values are CF epoch seconds. Walk through `tests/test_query_builder.py::TestDatePredicates` — 13 tests covering individual dimensions, combined filters, and count query parity.
result: pass

### 6. Bridge date filtering: Matching semantics
expected: BridgeOnlyRepository.list_tasks() filters in-memory with >= after (inclusive), < before (exclusive), NULL excluded. Walk through `tests/test_list_pipelines.py::TestListTasksDateFiltering` — 5 tests covering after/before/combined filtering and NULL handling on bridge path.
result: pass

### 7. Pipeline: _resolve_date_filters integration
expected: _ListTasksPipeline._resolve_date_filters() resolves date expressions (relative like "last_1w", absolute like "2026-01-15") to _after/_before datetime bounds on ListTasksRepoQuery. Single `datetime.now(UTC)` capture for consistency. Walk through `tests/test_list_pipelines.py::TestListTasksDateFilterPipeline` — tests verify end-to-end resolution from service input to repo query.
result: issue
reported: "Three design issues: (1) Domain should own due-soon fallback logic — when get_due_soon_setting() returns None and due='soon' is used, default to TODAY and emit agent-facing warning: 'Due-soon threshold was not detected. Defaulting to today. Set OPERATOR_DUE_SOON_THRESHOLD to override.' Warning preserves polymorphism — service doesn't branch on repo type. (2) Resolver should return a rich type (ResolvedDateBounds with dates + warnings list) instead of mutating query fields directly. (3) Inline # noqa imports in _resolve_date_filters are a red flag — move to top-level runtime imports section."
severity: major

### 8. Lifecycle availability auto-include
expected: When completed or dropped date filters are set, _resolve_date_filters automatically adds Availability.COMPLETED or Availability.DROPPED via set-union merge — agent doesn't need to set availability manually. Tests: `test_completed_today_auto_includes_completed_availability` and `test_dropped_last_1w_auto_includes_dropped_availability`.
result: pass

### 9. "any" shortcut bypass
expected: completed="any" / dropped="any" adds lifecycle availability (COMPLETED/DROPPED) without setting any date bounds — no resolver call, purely additive. Test: `test_completed_any_returns_all_completed_regardless_of_date` and `test_dropped_any_returns_all_dropped_regardless_of_date`.
result: pass

## Summary

total: 9
passed: 7
issues: 2
pending: 0
skipped: 0
blocked: 0

## Gaps

- truth: "Invalid OPERATOR_DUE_SOON_THRESHOLD env var should fail at startup and trigger error-serving mode"
  status: failed
  reason: "User reported: Invalid env var should fail fast at startup, not at query time. Settings.due_soon_threshold is str | None — pydantic accepts any string, enum validation deferred to get_due_soon_setting() at query time. Should validate at Settings boundary so bad config triggers error-serving mode on boot."
  severity: major
  test: 3
  root_cause: "Settings.due_soon_threshold is str | None — pydantic-settings accepts any string without validation. Enum conversion deferred to BridgeOnlyRepository.get_due_soon_setting() at query time. Validation should happen at Settings construction (startup) so invalid values trigger error-serving mode."
  artifacts:
    - path: "src/omnifocus_operator/config.py"
      issue: "due_soon_threshold field is str | None, needs field_validator or DueSoonSetting | None type"
    - path: "src/omnifocus_operator/repository/bridge_only/bridge_only.py"
      issue: "get_due_soon_setting() does enum conversion that should move to Settings validation"
  missing:
    - "Add field_validator on Settings.due_soon_threshold that validates against DueSoonSetting member names at construction time"
    - "Invalid value at startup should trigger error-serving mode with educational error message"
  debug_session: ""

- truth: "Domain should own due-soon fallback + warning; resolver returns rich type; no inline noqa imports"
  status: failed
  reason: "User reported: (1) When get_due_soon_setting() returns None and due='soon' is used, domain should default to TODAY and emit agent-facing warning preserving polymorphism. (2) Resolver should return ResolvedDateBounds (dates + warnings) not mutate query directly. (3) Inline # noqa imports in _resolve_date_filters should move to top-level."
  severity: major
  test: 7
  root_cause: "Three issues: (1) Due-soon fallback logic lives in service layer (_resolve_date_filters) but should be domain concern — when get_due_soon_setting() returns None and due='soon', domain should default to TODAY + emit warning. (2) _resolve_date_filters mutates query fields directly instead of returning a rich type with dates + warnings. (3) Inline imports with # noqa: PLC0415 caused by from __future__ import annotations making top-level imports appear unused — should be placed in runtime imports section."
  artifacts:
    - path: "src/omnifocus_operator/service/service.py"
      issue: "_resolve_date_filters owns fallback logic + uses inline noqa imports"
    - path: "src/omnifocus_operator/service/resolve_dates.py"
      issue: "resolve_date_filter should return rich type (ResolvedDateBounds) with dates + warnings"
  missing:
    - "Domain resolver returns ResolvedDateBounds (dates + warnings list) instead of bare datetime bounds"
    - "When due_soon_setting is None and due='soon' is used, default to TODAY and add agent-facing warning: 'Due-soon threshold was not detected. Defaulting to today. Set OPERATOR_DUE_SOON_THRESHOLD to override.'"
    - "Move inline imports to top-level runtime imports section in service.py"
  debug_session: ""
