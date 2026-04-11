---
phase: 46-pipeline-query-paths
plan: 04
subsystem: config
tags: [validation, startup, due-soon, pydantic]
dependency_graph:
  requires: []
  provides: [startup-time-due-soon-validation]
  affects: [config.py, bridge_only.py]
tech_stack:
  added: []
  patterns: [field_validator-with-lazy-import, startup-time-validation]
key_files:
  created: []
  modified:
    - src/omnifocus_operator/config.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - tests/test_due_soon_setting.py
decisions:
  - Used lazy import inside field_validator to break circular dependency (config -> contracts -> config)
  - Field type is Any (not DueSoonSetting | None) to avoid pydantic forward-ref resolution triggering the circular import
  - Validator returns DueSoonSetting | None at runtime; type safety preserved by tests
metrics:
  duration: ~5 minutes
  completed: "2026-04-08T13:34:00Z"
  tasks_completed: 1
  tasks_total: 1
  test_count: 20
  test_pass: 20
---

# Phase 46 Plan 04: Startup-Time Due-Soon Validation Summary

Moved OPERATOR_DUE_SOON_THRESHOLD validation from query-time (BridgeOnlyRepository.get_due_soon_setting) to startup-time (Settings field_validator) so invalid values trigger error-serving mode immediately.

## What Changed

- **config.py**: Added `@field_validator("due_soon_threshold", mode="before")` that converts str -> DueSoonSetting via case-insensitive enum lookup. Invalid values raise ValueError (wrapped by pydantic into ValidationError with educational message listing valid options). Lazy import of DueSoonSetting inside validator to avoid circular dependency.
- **bridge_only.py**: Simplified `get_due_soon_setting()` from 10-line try/except/KeyError block to single `return get_settings().due_soon_threshold`. Moved DueSoonSetting import from runtime to TYPE_CHECKING block.
- **tests/test_due_soon_setting.py**: Updated `test_raises_for_invalid_value` to expect ValidationError at `get_settings()` call (not at `get_due_soon_setting()`). Added `TestSettingsDueSoonValidation` class with 4 direct tests: none_accepted, valid_value_accepted, case_insensitive, invalid_value_raises.

## Commits

| Task | Type | Hash | Description |
|------|------|------|-------------|
| 1 (RED) | test | 62a27a5 | Add failing tests for startup-time validation |
| 1 (GREEN) | feat | f345da5 | Move validation from query-time to startup-time |

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import: config.py -> contracts -> config.py**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Top-level `from omnifocus_operator.contracts.use_cases.list._enums import DueSoonSetting` in config.py created circular import because contracts/__init__.py imports from contracts.use_cases.list.folders, which imports DEFAULT_LIST_LIMIT from config.py
- **Fix:** Lazy import inside `_validate_due_soon_threshold` method; field type changed to `Any` instead of `DueSoonSetting | None` to avoid pydantic forward-ref resolution
- **Files modified:** src/omnifocus_operator/config.py
- **Commit:** f345da5

## Verification

1. `uv run pytest tests/test_due_soon_setting.py -x -q` -- 20 passed
2. `uv run pytest -x -q` -- 1857 passed, 97.74% coverage
3. `OPERATOR_DUE_SOON_THRESHOLD=INVALID ... get_settings()` -- raises ValidationError with educational message
4. `OPERATOR_DUE_SOON_THRESHOLD=TWO_DAYS ... get_settings().due_soon_threshold` -- prints DueSoonSetting.TWO_DAYS

## Self-Check: PASSED

- All 3 modified files exist on disk
- Both commits (62a27a5, f345da5) found in git log
