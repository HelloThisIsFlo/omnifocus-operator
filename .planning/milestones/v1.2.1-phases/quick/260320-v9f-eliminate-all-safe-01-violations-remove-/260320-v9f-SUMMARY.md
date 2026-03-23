---
phase: quick-260320-v9f
plan: 01
subsystem: testing
tags: [safe-01, monkeypatch, safety-guard, factory]

requires:
  - phase: 23
    provides: SimulatorBridge, repository factory with _create_real_bridge
provides:
  - Zero SAFE-01 violations outside enforcement test
  - Smoke guard preventing future violations
affects: [testing, CI, safety]

tech-stack:
  added: []
  patterns:
    - "Monkeypatch _create_real_bridge for factory routing tests"
    - "Monkeypatch create_repository for server integration tests"
    - "Smoke guard with allowed-exceptions set for enforcement tests"

key-files:
  created: []
  modified:
    - tests/test_repository_factory.py
    - tests/test_server.py
    - tests/test_simulator_integration.py
    - tests/test_smoke.py

key-decisions:
  - "Monkeypatch at _create_real_bridge level (not create_repository) for factory tests -- preserves factory routing logic under test"
  - "Monkeypatch at create_repository level for server tests -- bypasses factory entirely since server tests care about annotations/schemas, not repository selection"
  - "Shared _stub_real_bridge helper in factory test module to DRY the 6 tests"

patterns-established:
  - "Factory tests: monkeypatch _create_real_bridge to return SimulatorBridge"
  - "Server tests needing real lifespan: monkeypatch create_repository to return BridgeRepository(SimulatorBridge)"

requirements-completed: [SAFE-01]

duration: 4min
completed: 2026-03-20
---

# Quick Task 260320-v9f: Eliminate SAFE-01 Violations Summary

**Removed 12 delenv("PYTEST_CURRENT_TEST") violations from factory/server/simulator tests, replaced with monkeypatching at factory layer, added smoke guard to catch future violations**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-20T22:34:13Z
- **Completed:** 2026-03-20T22:38:38Z
- **Tasks:** 3 (2 implementation + 1 verification)
- **Files modified:** 4

## Accomplishments
- Eliminated all 12 SAFE-01 violations (6 factory, 5 server, 1 simulator integration)
- Factory tests now monkeypatch `_create_real_bridge` -- preserves routing logic testing without touching RealBridge
- Server tests now monkeypatch `create_repository` -- same pattern already proven in test_simulator_integration.py
- Smoke guard `test_no_test_removes_pytest_current_test` catches future violations automatically

## Task Commits

Each task was committed atomically:

1. **Task 1: Fix factory and server tests** - `45e1b1a` (fix) - Replace delenv with monkeypatch in 11 tests across 3 files
2. **Task 2: Update smoke guard** - `ad2d089` (fix) - Add test_ipc_engine.py exception to smoke guard

Task 3 was verification-only (full suite + mypy), no commit needed.

## Files Modified
- `tests/test_repository_factory.py` - 6 tests: replaced delenv with _stub_real_bridge helper
- `tests/test_server.py` - 5 tests: replaced delenv with monkeypatched create_repository
- `tests/test_simulator_integration.py` - 1 test: already fixed from investigation, committed here
- `tests/test_smoke.py` - Added smoke guard with test_ipc_engine.py exception

## Decisions Made
- Monkeypatch at `_create_real_bridge` for factory tests (preserves routing logic)
- Monkeypatch at `create_repository` for server tests (bypasses factory, matches existing pattern)
- Created shared `_stub_real_bridge()` helper in factory tests to DRY the 6 identical setups

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## Verification Results

- `grep -rn 'delenv.*PYTEST_CURRENT_TEST' tests/` -- only test_ipc_engine.py (enforcement test)
- `pytest tests/test_smoke.py::test_no_test_removes_pytest_current_test` -- PASSED
- `pytest --tb=short -q` -- 611 passed
- `mypy src/ tests/` -- no new errors (60 pre-existing, none in modified files)

## Self-Check: PASSED

- All 4 modified files exist on disk
- Both task commits verified in git log
- Zero SAFE-01 violations outside allowed exception

---
*Quick task: 260320-v9f*
*Completed: 2026-03-20*
