---
phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon
plan: 02
subsystem: service
tags: [preferences, date-normalization, due-soon, domain-logic, dependency-injection]

# Dependency graph
requires:
  - phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon (plan 01)
    provides: OmniFocusPreferences module with bridge-based settings loading
provides:
  - Fully wired preferences in service layer for field-aware date normalization
  - DueSoon threshold sourced from preferences module instead of repository
  - All legacy DueSoon code paths deleted (SQLite plist, env var, protocol method)
  - Updated tool descriptions documenting default time behavior and soon threshold
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Preferences collaborator injected alongside repository in OperatorService constructor"
    - "Async _normalize_dates fetches per-field default times from preferences"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/server.py
    - src/omnifocus_operator/contracts/protocols.py
    - src/omnifocus_operator/config.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - src/omnifocus_operator/agent_messages/descriptions.py

key-decisions:
  - "plistlib import retained in hybrid.py -- still used for perspective row mapping"
  - "DueSoon fallback upgraded from TODAY (1 day) to TWO_DAYS (OmniFocus factory default)"
  - "EDIT_TASKS_TOOL_DOC trimmed to fit 2048-byte client limit after _DATE_INPUT_NOTE expansion"

patterns-established:
  - "OmniFocusPreferences injected via constructor alongside repository"
  - "Write pipeline _normalize_dates is async and field-aware (fetches default_time per field)"

requirements-completed: [PREF-04, PREF-05, PREF-06, PREF-07, PREF-08, PREF-09, PREF-10, PREF-11, PREF-12, PREF-13]

# Metrics
duration: 13min
completed: 2026-04-11
---

# Phase 50 Plan 02: Service Rewiring and Legacy Cleanup Summary

**Preferences wired through service layer: field-aware date normalization with user-configured default times, DueSoon from bridge-based preferences, all SQLite plist/env var paths deleted**

## Performance

- **Duration:** 13 min
- **Started:** 2026-04-11T13:20:30Z
- **Completed:** 2026-04-11T13:33:43Z
- **Tasks:** 2
- **Files modified:** 14 (8 src, 6 test)

## Accomplishments
- OperatorService accepts OmniFocusPreferences as constructor collaborator, injected alongside repository
- normalize_date_input() takes default_time parameter; _AddTaskPipeline and _EditTaskPipeline fetch per-field defaults from preferences
- _ReadPipeline uses preferences.get_due_soon_setting() instead of repository method
- Deleted get_due_soon_setting from Repository protocol, HybridRepository (SQLite plist parsing), BridgeOnlyRepository (env var)
- Deleted due_soon_threshold field and validator from config.py (OPERATOR_DUE_SOON_THRESHOLD env var eliminated)
- Deleted tests/test_due_soon_setting.py (replaced by test_preferences.py from Plan 01)
- Tool descriptions updated: date-only default time note, soon threshold preference note, server restart note
- 1981 tests pass, 98% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Service rewiring -- preferences injection, DueSoon migration, field-aware date normalization** - `87f4186` (feat)
2. **Task 2: Delete legacy DueSoon paths + update tool descriptions** - `a7d9afd` (chore)

## Files Created/Modified
- `src/omnifocus_operator/service/service.py` - OperatorService constructor takes preferences; pipelines pass preferences; _normalize_dates async
- `src/omnifocus_operator/service/domain.py` - normalize_date_input(default_time=); DueSoon fallback upgraded to TWO_DAYS
- `src/omnifocus_operator/server.py` - Lifespan creates OmniFocusPreferences from repository bridge
- `src/omnifocus_operator/contracts/protocols.py` - Removed get_due_soon_setting from Repository protocol
- `src/omnifocus_operator/config.py` - Removed due_soon_threshold field, validator, DueSoonSetting import
- `src/omnifocus_operator/repository/hybrid/hybrid.py` - Deleted _SETTING_MAP, _read_due_soon_setting_sync, get_due_soon_setting
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` - Deleted get_due_soon_setting, removed unused imports
- `src/omnifocus_operator/agent_messages/descriptions.py` - Updated _DATE_INPUT_NOTE, added soon notes, trimmed EDIT_TASKS doc
- `tests/conftest.py` - service fixture passes preferences from bridge
- `tests/test_service.py` - AsyncMock tests pass preferences=AsyncMock()
- `tests/test_server.py` - Inline OperatorService construction passes preferences
- `tests/test_service_domain.py` - Updated normalize tests for default_time, DueSoon fallback for TWO_DAYS
- `tests/test_list_pipelines.py` - Updated DueSoon pipeline test for TWO_DAYS behavior
- `tests/test_due_soon_setting.py` - Deleted (replaced by test_preferences.py)

## Decisions Made
- Retained plistlib import in hybrid.py -- still needed for perspective SQLite row mapping (plan assumed it was only used by deleted plist parsing)
- DueSoon fallback in domain.py upgraded from timedelta(days=1) to timedelta(days=2) to match OmniFocus factory default
- EDIT_TASKS_TOOL_DOC condensed from 2208 to 1305 bytes after _DATE_INPUT_NOTE expansion pushed it over 2048-byte client limit

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Restored plistlib import in hybrid.py**
- **Found during:** Task 2 (Delete legacy DueSoon paths)
- **Issue:** Plan instructed to remove `import plistlib` from hybrid.py, but it's still used for perspective row mapping at line 486
- **Fix:** Re-added the import after test failure confirmed it was still needed
- **Files modified:** src/omnifocus_operator/repository/hybrid/hybrid.py
- **Verification:** Full test suite passes (1981 tests)
- **Committed in:** a7d9afd (Task 2 commit)

**2. [Rule 1 - Bug] Updated DueSoon pipeline integration test**
- **Found during:** Task 1 (Service rewiring)
- **Issue:** test_list_pipelines.py expected old behavior (DueSoon from repository returning None, fallback to TODAY with 1-day bounds). With preferences module, DueSoon always returns a value (TWO_DAYS factory default), and "soon" bounds use after=None (including overdue)
- **Fix:** Updated test to expect TWO_DAYS behavior: both today and tomorrow tasks match, overdue tasks also match (after=None)
- **Files modified:** tests/test_list_pipelines.py
- **Verification:** Full test suite passes
- **Committed in:** 87f4186 (Task 1 commit)

**3. [Rule 1 - Bug] Trimmed EDIT_TASKS_TOOL_DOC to fit client byte limit**
- **Found during:** Task 2 (Update tool descriptions)
- **Issue:** _DATE_INPUT_NOTE expansion added ~120 bytes, pushing EDIT_TASKS_TOOL_DOC to 2208 bytes (160 over 2048-byte Claude Code limit)
- **Fix:** Condensed repetition rule examples and action descriptions while preserving all essential information
- **Files modified:** src/omnifocus_operator/agent_messages/descriptions.py
- **Verification:** DESC-08 test passes (1305 bytes)
- **Committed in:** a7d9afd (Task 2 commit)

---

**Total deviations:** 3 auto-fixed (3 bugs)
**Impact on plan:** All auto-fixes necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 50 complete: OmniFocus preferences fully wired through the stack
- Bridge settings command (Plan 01) + service wiring (Plan 02) deliver the full feature
- OPERATOR_DUE_SOON_THRESHOLD env var eliminated -- single source of truth is OmniFocus preferences via bridge

## Self-Check: PASSED

- All 8 modified source files exist
- All 2 task commits verified (87f4186, a7d9afd)
- Deleted file (tests/test_due_soon_setting.py) confirmed absent
- Full test suite: 1981 passed, 98% coverage

---
*Phase: 50-use-omnifocus-settings-api-for-date-preferences-and-due-soon*
*Completed: 2026-04-11*
