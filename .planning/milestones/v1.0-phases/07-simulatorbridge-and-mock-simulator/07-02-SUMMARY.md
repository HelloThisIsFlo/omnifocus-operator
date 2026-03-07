---
phase: 07-simulatorbridge-and-mock-simulator
plan: 02
subsystem: testing
tags: [simulator, ipc, integration-testing, subprocess, file-bridge]

# Dependency graph
requires:
  - phase: 07-simulatorbridge-and-mock-simulator
    provides: SimulatorBridge class (RealBridge subclass with no-op trigger)
  - phase: 06-file-ipc-engine
    provides: RealBridge with file-based IPC mechanics
provides:
  - Mock simulator process (python -m omnifocus_operator.simulator)
  - Realistic SIMULATOR_SNAPSHOT data (10 tasks, 3 projects, 4 tags, 2 folders, 3 perspectives)
  - CLI error injection (--fail-mode, --fail-after, --delay)
  - Integration test suite proving full IPC pipeline end-to-end
affects: [08-realbridge]

# Tech tracking
tech-stack:
  added: []
  patterns: [subprocess-fixture-with-readiness-detection, file-ipc-round-trip-testing]

key-files:
  created:
    - src/omnifocus_operator/simulator/__init__.py
    - src/omnifocus_operator/simulator/_data.py
    - src/omnifocus_operator/simulator/__main__.py
    - tests/test_simulator_integration.py
  modified: []

key-decisions:
  - "Simulator uses sys.stderr.write() for readiness marker (not print()) to avoid stdout print() detection test"
  - "Subprocess fixture reads stderr line-by-line for 'ready' keyword as synchronization signal"
  - "Integration tests use json.JSONDecodeError for malformed test (not BridgeProtocolError) because json.loads() in _wait_response raises before _validate_response runs"

patterns-established:
  - "Subprocess readiness detection: write 'Ready: ...' to stderr, fixture reads until match"
  - "Integration test isolation: each test gets fresh tmp_path IPC directory"

requirements-completed: [TEST-01, BRDG-03]

# Metrics
duration: 4min
completed: 2026-03-02
---

# Phase 7 Plan 2: Mock Simulator and Integration Tests Summary

**Standalone mock simulator process with realistic OmniFocus data, CLI error injection, and 10 integration tests proving full file-based IPC round-trip**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-02T18:26:18Z
- **Completed:** 2026-03-02T18:31:10Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Created mock simulator as standalone subprocess (`python -m omnifocus_operator.simulator`)
- Built realistic SIMULATOR_SNAPSHOT covering 10 tasks (inbox, flagged, completed, due-dated, tagged, with children), 3 projects, 4 tags, 2 folders, 3 perspectives
- CLI supports error injection: --fail-mode (timeout/error/malformed), --fail-after N, --delay seconds
- 10 integration tests proving complete IPC pipeline: bridge -> request file -> simulator -> response file -> bridge

## Task Commits

Each task was committed atomically:

1. **Task 1: Create simulator package with realistic data and CLI entry point** - `26adaa2` (feat)
2. **Task 2: Integration tests for simulator + SimulatorBridge round-trip** - `c0d7451` (test)

## Files Created/Modified
- `src/omnifocus_operator/simulator/__init__.py` - Package marker
- `src/omnifocus_operator/simulator/_data.py` - SIMULATOR_SNAPSHOT with realistic OmniFocus data
- `src/omnifocus_operator/simulator/__main__.py` - Simulator entry point with argparse CLI and file watcher loop
- `tests/test_simulator_integration.py` - 10 integration tests (process lifecycle, round-trip, error modes, MCP integration)

## Decisions Made
- Simulator uses `sys.stderr.write()` for the readiness marker (not `print()`) to comply with the source-wide stdout clean test
- Subprocess fixture reads stderr line-by-line for "ready" keyword as synchronization signal with configurable timeout
- Malformed JSON test catches `json.JSONDecodeError` (not `BridgeProtocolError`) because `json.loads()` in `_wait_response` raises before `_validate_response` runs
- Request PID extracted from filename (not `os.getpid()`) so response files use the requester's PID for correct path matching

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Full simulator pipeline validated end-to-end
- Phase 7 complete -- SimulatorBridge class + mock simulator + integration tests all working
- Phase 8 (RealBridge) can proceed: only addition is URL scheme trigger in `_trigger_omnifocus()`
- No blockers

---
*Phase: 07-simulatorbridge-and-mock-simulator*
*Completed: 2026-03-02*
