---
phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
plan: 03
subsystem: testing
tags: [test-doubles, stub-bridge, single-responsibility, bridge-protocol]

# Dependency graph
requires:
  - phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
    plan: 02
    provides: "Stateful InMemoryBridge with add_task/edit_task handlers"
provides:
  - "StubBridge class for canned-response testing (separate from stateful InMemoryBridge)"
  - "InMemoryBridge cleaned of dual-mode logic (_stateful flag, auto-detection removed)"
  - "All stub-mode test usages migrated to StubBridge"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns: ["StubBridge for canned-response bridge testing, InMemoryBridge for stateful snapshot testing"]

key-files:
  created:
    - tests/doubles/stub_bridge.py
  modified:
    - tests/doubles/bridge.py
    - tests/doubles/__init__.py
    - tests/test_hybrid_repository.py
    - tests/test_bridge.py
    - tests/test_stateful_bridge.py
    - tests/test_repository.py

key-decisions:
  - "StubBridge uses BridgeCall records (same as InMemoryBridge) for call tracking consistency"
  - "InMemoryBridge unknown operations return assembled snapshot instead of raw data"

patterns-established:
  - "StubBridge for write-through tests that need canned bridge responses (HybridRepository tests)"
  - "InMemoryBridge exclusively for snapshot-based stateful testing"

requirements-completed: [INFRA-10]

# Metrics
duration: 7min
completed: 2026-03-21
---

# Phase 26 Plan 03: Split InMemoryBridge into StubBridge and Stateful InMemoryBridge Summary

**StubBridge extracted as canned-response test double, InMemoryBridge cleaned of dual-mode auto-detection; 12 hybrid repo + 10 bridge test usages migrated**

## Performance

- **Duration:** 7 min
- **Started:** 2026-03-21T13:08:35Z
- **Completed:** 2026-03-21T13:15:51Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Created StubBridge class in tests/doubles/stub_bridge.py with canned-response behavior (returns seed data for every operation)
- Removed _stateful flag, _data raw backup, and auto-detection heuristic from InMemoryBridge
- Migrated 12 canned-response usages in test_hybrid_repository.py to StubBridge
- Renamed TestInMemoryBridge to TestStubBridge in test_bridge.py (10 stub-behavior tests)
- Updated unknown operation tests in test_stateful_bridge.py (now returns assembled snapshot)
- All 641 tests pass with 98% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Create StubBridge and clean InMemoryBridge** - `dd81a57` (feat)
2. **Task 2: Migrate stub-mode usages to StubBridge** - `7e5f715` (refactor)

## Files Created/Modified
- `tests/doubles/stub_bridge.py` - New StubBridge class: canned-response bridge for non-stateful testing
- `tests/doubles/bridge.py` - InMemoryBridge cleaned: no _stateful, no _data, no auto-detection; unknown ops return snapshot
- `tests/doubles/__init__.py` - Added StubBridge to package exports
- `tests/test_hybrid_repository.py` - 12 canned-response InMemoryBridge usages migrated to StubBridge
- `tests/test_bridge.py` - TestInMemoryBridge renamed to TestStubBridge; added StubBridge protocol test
- `tests/test_stateful_bridge.py` - Unknown operation tests updated for new snapshot-return behavior
- `tests/test_repository.py` - 2 tests fixed: replaced _data attribute access with entity list population

## Decisions Made
- **StubBridge uses BridgeCall:** Kept BridgeCall dataclass for call tracking (shared with InMemoryBridge) so existing tests checking `.operation` and `.params` work unchanged.
- **Unknown operations return snapshot:** InMemoryBridge now returns `_handle_get_all()` for unknown operations instead of raw seed data, which is consistent with its stateful nature.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed 2 tests in test_repository.py that accessed removed _data attribute**
- **Found during:** Task 2 (full test suite verification)
- **Issue:** `test_failed_refresh_preserves_none_cache` and `test_failed_first_load_allows_retry` set `bridge._data = make_snapshot_dict()` which no longer exists after removing dual-mode logic.
- **Fix:** Replaced `_data` assignment with direct population of entity lists (`_tasks`, `_projects`, `_tags`, `_folders`, `_perspectives`).
- **Files modified:** tests/test_repository.py
- **Verification:** All 641 tests pass
- **Committed in:** 7e5f715 (Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Necessary fix for tests that relied on removed internal state. No scope creep.

## Issues Encountered
None beyond the deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- InMemoryBridge is now a single-purpose stateful test double
- StubBridge is available for any test needing canned bridge responses
- No blockers

## Known Stubs
None - all classes fully implemented.

## Self-Check: PASSED

- FOUND: tests/doubles/stub_bridge.py
- FOUND: tests/doubles/bridge.py
- FOUND: tests/doubles/__init__.py
- FOUND: tests/test_hybrid_repository.py
- FOUND: tests/test_bridge.py
- FOUND: tests/test_stateful_bridge.py
- FOUND: tests/test_repository.py
- FOUND: 26-03-SUMMARY.md
- FOUND: dd81a57 (Task 1 commit)
- FOUND: 7e5f715 (Task 2 commit)

---
*Phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge*
*Completed: 2026-03-21*
