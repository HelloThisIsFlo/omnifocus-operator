---
phase: 06-file-ipc-engine
plan: 01
subsystem: bridge
tags: [ipc, asyncio, file-io, uuid, atomic-write, polling]

# Dependency graph
requires:
  - phase: 03-bridge-protocol-and-inmemorybridge
    provides: Bridge protocol, BridgeError hierarchy
provides:
  - RealBridge class with file-based IPC mechanics
  - Atomic request writing via .tmp + os.replace()
  - Async response polling with asyncio.to_thread
  - Dispatch protocol with uuid::::operation format
  - Timeout handling with BridgeTimeoutError naming OmniFocus
  - _trigger_omnifocus() no-op hook for Phase 8
affects: [07-simulator-bridge, 08-real-bridge-trigger]

# Tech tracking
tech-stack:
  added: []
  patterns: [atomic-file-write, async-polling, template-method-hook]

key-files:
  created:
    - src/omnifocus_operator/bridge/_real.py
    - tests/test_real_bridge.py
  modified:
    - src/omnifocus_operator/bridge/_errors.py
    - tests/test_bridge.py

key-decisions:
  - "BridgeTimeoutError message updated to include OmniFocus for user-actionability (IPC-05)"
  - "50ms polling interval for response detection (balances responsiveness vs CPU)"
  - "JSON envelope for request files (extensible for future write payloads)"

patterns-established:
  - "Atomic file write: write .tmp then os.replace() for all IPC file writes"
  - "Non-blocking file I/O: all file ops wrapped in asyncio.to_thread(closure)"
  - "Template method: _trigger_omnifocus() hook overridable by subclasses"

requirements-completed: [IPC-01, IPC-02, IPC-03, IPC-05]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 6 Plan 01: RealBridge IPC Mechanics Summary

**RealBridge with atomic file writes, async polling, UUID4 dispatch protocol, and timeout handling via stdlib-only IPC**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T15:45:48Z
- **Completed:** 2026-03-02T15:50:04Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 4

## Accomplishments
- RealBridge class implementing Bridge protocol via structural typing with full IPC lifecycle
- Atomic request file writes using .tmp + os.replace() pattern (IPC-01)
- All file I/O non-blocking via asyncio.to_thread() wrapping (IPC-02)
- Dispatch protocol with uuid::::operation format and UUID4 validation (IPC-03)
- Timeout raises BridgeTimeoutError with "OmniFocus" in message for user-actionability (IPC-05)
- 17 tests across 6 test classes, all passing

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests for RealBridge** - `b7a8751` (test)
2. **Task 1 GREEN: Implement RealBridge with IPC mechanics** - `6702e43` (feat)

_TDD task with RED (failing tests) then GREEN (implementation) commits._

## Files Created/Modified
- `src/omnifocus_operator/bridge/_real.py` - RealBridge class with send_command, atomic _write_request, polling _wait_response, _validate_response, _trigger_omnifocus hook
- `tests/test_real_bridge.py` - 17 tests: TestAtomicWrite, TestNonBlockingIO, TestDispatchProtocol, TestTimeout, TestSuccessfulRoundTrip, TestTriggerHook
- `src/omnifocus_operator/bridge/_errors.py` - Updated BridgeTimeoutError message to include "OmniFocus" per IPC-05
- `tests/test_bridge.py` - Updated test_timeout_error_message_format for new message format

## Decisions Made
- BridgeTimeoutError message updated to include "OmniFocus" for user-actionability (IPC-05 requirement). Message now reads: "OmniFocus did not respond within Ns (operation: 'op'). Is OmniFocus running?"
- 50ms polling interval for response file detection -- balances 25ms average latency vs minimal CPU overhead
- JSON envelope `{"dispatch": "uuid::::op"}` for request files -- extensible for future write payloads in M5

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated BridgeTimeoutError message to include OmniFocus**
- **Found during:** Task 1 GREEN phase
- **Issue:** BridgeTimeoutError.__init__ constructed message "Operation 'X' timed out after Ns" which didn't include "OmniFocus" as required by IPC-05
- **Fix:** Updated _errors.py BridgeTimeoutError to use "OmniFocus did not respond within Ns (operation: 'X'). Is OmniFocus running?"
- **Files modified:** src/omnifocus_operator/bridge/_errors.py, tests/test_bridge.py
- **Verification:** test_timeout_error_message_names_omnifocus passes, existing test_bridge.py updated to match
- **Committed in:** 6702e43 (GREEN phase commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Required for IPC-05 compliance. Updated shared error class message and its existing test. No scope creep.

## Issues Encountered
None -- plan executed smoothly after the BridgeTimeoutError message fix.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- RealBridge core IPC mechanics complete, ready for Plan 06-02 (startup sweep, factory wiring, IPC directory configuration)
- _trigger_omnifocus() is a no-op placeholder -- Phase 8 will fill in URL scheme trigger
- SimulatorBridge (Phase 7) can inherit from RealBridge and override _trigger_omnifocus()

---
*Phase: 06-file-ipc-engine*
*Completed: 2026-03-02*
