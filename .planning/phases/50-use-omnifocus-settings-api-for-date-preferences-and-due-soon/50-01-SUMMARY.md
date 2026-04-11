---
phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon
plan: 01
subsystem: service/preferences, bridge
tags: [bridge, preferences, settings, due-soon, lazy-cache]
dependency_graph:
  requires: []
  provides: [bridge-get-settings, omnifocus-preferences, settings-factory-defaults]
  affects: [service/domain.py, service/service.py, repository/hybrid/hybrid.py]
tech_stack:
  added: []
  patterns: [lazy-singleton-cache, factory-default-fallback, time-normalization]
key_files:
  created:
    - src/omnifocus_operator/service/preferences.py
    - tests/test_preferences.py
  modified:
    - src/omnifocus_operator/bridge/bridge.js
    - tests/doubles/bridge.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - tests/test_bridge.py
    - tests/test_warnings.py
decisions:
  - "Preferences module placed in service/ package (infrastructure consumed by service, not entity CRUD)"
  - "_SETTING_MAP migrated from hybrid.py to preferences.py as internal implementation detail"
  - "Factory defaults initialized in constructor, _loaded=True set before bridge call (T-50-02)"
  - "_normalize_time handles both HH:MM and HH:MM:SS OmniJS inconsistency"
metrics:
  duration: ~7 minutes
  completed: "2026-04-11T13:18Z"
  tasks: 2/2
  tests_added: 25
  tests_total: 2000
---

# Phase 50 Plan 01: Bridge get_settings + OmniFocusPreferences Summary

Bridge `get_settings` command reading 5 OmniFocus date preference keys via `settings.objectForKey()`, plus `OmniFocusPreferences` module with lazy-load, server-lifetime cache, factory-default fallback, and domain-typed DueSoonSetting/time outputs.

## Completed Tasks

| # | Task | Commits | Key Files |
|---|------|---------|-----------|
| 1 | Bridge get_settings command + InMemoryBridge handler | `aa6e26f` (RED), `cc85db1` (GREEN) | bridge.js, tests/doubles/bridge.py, tests/test_bridge.py |
| 2 | OmniFocusPreferences module | `93b5de6` (RED), `20eb5f1` (GREEN) | service/preferences.py, tests/test_preferences.py, warnings.py |

## Implementation Details

### Bridge Layer (bridge.js)
- `handleGetSettings()` reads 5 keys via `settings.objectForKey()`: DefaultDueTime, DefaultStartTime, DefaultPlannedTime, DueSoonInterval, DueSoonGranularity
- Dispatch routes `get_settings` operation between `edit_task` and the unknown-operation fallback

### InMemoryBridge (tests/doubles/bridge.py)
- `_settings` dict initialized with OmniFocus factory defaults
- `configure_settings(overrides)` merges test overrides into settings
- `get_settings` dispatch returns a copy (prevents mutation)

### OmniFocusPreferences (service/preferences.py)
- `_FACTORY_DEFAULTS`: 5-key dict with OmniFocus factory default values
- `_SETTING_MAP`: 7-entry dict mapping `(interval_seconds, granularity)` tuples to `DueSoonSetting` enum (migrated from hybrid.py)
- `_DEFAULT_TIME_MAP`: maps `due_date/defer_date/planned_date` to settings keys
- `_normalize_time()`: pads `HH:MM` to `HH:MM:SS`, passes `HH:MM:SS` through
- `_ensure_loaded()`: sets `_loaded=True` before bridge call (re-entry prevention per T-50-02)
- On bridge failure: factory defaults used, `SETTINGS_FALLBACK_WARNING` emitted
- On unknown DueSoon pair: TWO_DAYS fallback, `SETTINGS_UNKNOWN_DUE_SOON_PAIR` emitted

### Warnings (agent_messages/warnings.py)
- `DUE_SOON_THRESHOLD_NOT_DETECTED`: updated to reference OmniFocus preferences (was: env var)
- `SETTINGS_FALLBACK_WARNING`: new, for bridge-unavailable fallback
- `SETTINGS_UNKNOWN_DUE_SOON_PAIR`: new, for unrecognized DueSoon values

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added preferences module to warning consumer list**
- **Found during:** Task 2, full test suite run
- **Issue:** `test_warnings.py` enforces that all warning constants are referenced in consumer modules; new constants in preferences.py weren't in the consumer list
- **Fix:** Added `service.preferences` to `_WARNING_CONSUMERS` in test_warnings.py
- **Files modified:** tests/test_warnings.py
- **Commit:** 20eb5f1

## Decisions Made

1. **Preferences in service/ package** -- OmniFocus preferences are infrastructure config consumed by the service layer, analogous to how config.py handles env vars but needing a bridge. Not a repository concern.
2. **Constructor initializes factory defaults** -- No separate "apply defaults" path needed; constructor sets all instance vars to factory values, `_apply()` only overrides what the bridge provides.
3. **_loaded = True before bridge call** -- Prevents infinite re-entry if bridge call fails and caller retries (T-50-02 threat mitigation).
4. **Time normalization as static method** -- Stateless transformation, no instance dependencies. Handles OmniJS inconsistency (some keys return HH:MM, others HH:MM:SS).

## Self-Check: PASSED

All 8 files found. All 4 commits verified.
