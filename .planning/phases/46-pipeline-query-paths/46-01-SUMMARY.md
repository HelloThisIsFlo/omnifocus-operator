---
phase: 46-pipeline-query-paths
plan: 01
subsystem: repository
tags: [sqlite, env-var, pydantic-settings, due-soon, config]

# Dependency graph
requires:
  - phase: 45-date-models-resolution
    provides: DueSoonSetting enum with 7 members and domain properties
provides:
  - Repository protocol with get_due_soon_setting() method
  - HybridRepository reads due-soon setting from SQLite Setting table
  - BridgeOnlyRepository reads due-soon setting from OPERATOR_DUE_SOON_THRESHOLD env var
  - Settings.due_soon_threshold field for env var access
affects: [46-03, resolve_date_filter, pipeline]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "SQLite Setting table key-value lookup with forward-compatible None fallback"
    - "Env var -> enum mapping with case-insensitive .upper() and educational ValueError"

key-files:
  created:
    - tests/test_due_soon_setting.py
  modified:
    - src/omnifocus_operator/contracts/protocols.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - src/omnifocus_operator/config.py

key-decisions:
  - "Runtime import for DueSoonSetting in hybrid.py -- module-level constant _SETTING_MAP requires runtime access, not TYPE_CHECKING"
  - "Inline imports in BridgeOnlyRepository.get_due_soon_setting -- follows existing bridge_only.py pattern for lazy imports"

patterns-established:
  - "Setting table read pattern: SELECT key, value FROM Setting WHERE key IN (...) with dict comprehension"
  - "Env var -> enum mapping: DueSoonSetting[name.upper()] with KeyError -> ValueError conversion"

requirements-completed: [RESOLVE-12]

# Metrics
duration: 7min
completed: 2026-04-08
---

# Phase 46 Plan 01: Due-Soon Setting Repository Summary

**Repository protocol extended with get_due_soon_setting() -- HybridRepository reads SQLite Setting table (7 interval/granularity pairs), BridgeOnlyRepository reads OPERATOR_DUE_SOON_THRESHOLD env var**

## Performance

- **Duration:** 7 min
- **Started:** 2026-04-08T11:02:34Z
- **Completed:** 2026-04-08T11:09:28Z
- **Tasks:** 2
- **Files modified:** 5

## Accomplishments
- Repository protocol extended with `async get_due_soon_setting() -> DueSoonSetting | None`
- HybridRepository reads DueSoonInterval + DueSoonGranularity from SQLite Setting table, maps to enum via `_SETTING_MAP` (7 entries)
- BridgeOnlyRepository reads OPERATOR_DUE_SOON_THRESHOLD env var via pydantic-settings, case-insensitive matching
- Both return None when source unavailable (no crash), unknown SQLite pairs return None (forward-compatible)
- 16 new tests covering all 7 settings, None cases, invalid input, protocol structural check
- Full suite green: 1,824 tests, 97.77% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Add get_due_soon_setting() to Repository protocol and HybridRepository**
   - `9b589b8` (test: failing tests for HybridRepository)
   - `bde0666` (feat: protocol + HybridRepository implementation)
2. **Task 2: Implement get_due_soon_setting() in BridgeOnlyRepository**
   - `eeb62cc` (test: failing tests for BridgeOnlyRepository)
   - `3639237` (feat: BridgeOnlyRepository + Settings.due_soon_threshold)

_TDD tasks: RED (failing test) then GREEN (implementation) commits_

## Files Created/Modified
- `src/omnifocus_operator/contracts/protocols.py` -- Added get_due_soon_setting to Repository protocol with DueSoonSetting TYPE_CHECKING import
- `src/omnifocus_operator/repository/hybrid/hybrid.py` -- _SETTING_MAP constant (7 entries), _read_due_soon_setting_sync, async get_due_soon_setting
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` -- async get_due_soon_setting reading from env var via get_settings()
- `src/omnifocus_operator/config.py` -- Added due_soon_threshold: str | None = None to Settings
- `tests/test_due_soon_setting.py` -- 16 tests: 11 HybridRepository, 5 BridgeOnlyRepository

## Decisions Made
- Runtime import for DueSoonSetting in hybrid.py: `_SETTING_MAP` is a module-level constant that references enum members at import time, so the import cannot be under TYPE_CHECKING
- Inline imports in BridgeOnlyRepository.get_due_soon_setting: follows existing bridge_only.py lazy import pattern, avoids circular imports

## Deviations from Plan

None -- plan executed exactly as written.

## Issues Encountered
- Linter (ruff) repeatedly removed DueSoonSetting import from hybrid.py because `from __future__ import annotations` made the type annotation in `_SETTING_MAP: dict[...]` lazy, and the linter saw the import as unused. Resolved by placing the import in the runtime model imports section (after TYPE_CHECKING block) where other model imports live.

## User Setup Required

None -- no external service configuration required.

## Next Phase Readiness
- get_due_soon_setting() ready for Plan 03 to wire into resolve_date_filter pipeline
- Both repository paths tested and working -- HybridRepository (primary) and BridgeOnlyRepository (fallback)

## Self-Check: PASSED

All 5 created/modified files verified present. All 4 commit hashes verified in git log.

---
*Phase: 46-pipeline-query-paths*
*Completed: 2026-04-08*
