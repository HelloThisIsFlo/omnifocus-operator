---
phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
plan: 04
subsystem: testing
tags: [pytest-markers, fixtures, test-boilerplate, conftest, declarative-tests]

# Dependency graph
requires:
  - phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
    plan: 02
    provides: "All test files use BridgeRepository + InMemoryBridge"
provides:
  - "@pytest.mark.snapshot marker infrastructure for declarative test data"
  - "bridge/repo/service fixture chain in conftest.py"
  - "TestOperatorService and TestAddTask refactored to fixture injection (~28 methods)"
affects: [26-05-PLAN]

# Tech tracking
tech-stack:
  added: []
  patterns: ["@pytest.mark.snapshot(...) marker for declarative snapshot data in tests", "conftest.py fixture chain: bridge -> repo -> service with late imports to avoid circular deps"]

key-files:
  created: []
  modified:
    - tests/conftest.py
    - tests/test_service.py
    - pyproject.toml

key-decisions:
  - "Late imports in conftest.py fixtures to break circular dependency (tests.doubles.bridge imports make_task_dict from conftest)"
  - "Fixture return types annotated as Any to avoid circular import at type-check time"

patterns-established:
  - "@pytest.mark.snapshot(tags=[...], tasks=[...]) for custom snapshot data, no marker for default snapshot"
  - "service fixture for most tests, service+repo for tests needing repo verification, service+bridge for bridge inspection"

requirements-completed: [INFRA-11, INFRA-12]

# Metrics
duration: 5min
completed: 2026-03-21
---

# Phase 26 Plan 04: Snapshot Marker Infrastructure and First-Class Refactoring Summary

**@pytest.mark.snapshot marker with bridge/repo/service fixture chain; TestOperatorService (8 methods) and TestAddTask (16 methods) converted to declarative fixture injection**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-21T12:37:30Z
- **Completed:** 2026-03-21T12:43:02Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created @pytest.mark.snapshot custom marker registered in pyproject.toml (--strict-markers compatible)
- Built bridge/repo/service fixture chain in conftest.py with marker-driven snapshot seeding
- Refactored TestOperatorService: 8 default-snapshot methods now use `service` fixture injection (1 AsyncMock test unchanged)
- Refactored TestAddTask: 16 methods use fixture injection, 5 with @pytest.mark.snapshot for custom data (2 AsyncMock/validation tests unchanged)
- Reduced inline bridge/repo/service construction from 93 to 68 sites (remaining 68 are TestEditTask, scope of plan 05)
- All 640 tests pass, zero behavioral changes

## Task Commits

Each task was committed atomically:

1. **Task 1: Create snapshot marker infrastructure and service fixture** - `ab58206` (feat)
2. **Task 2: Refactor TestOperatorService and TestAddTask to use fixtures** - `ca9586d` (refactor)

## Files Created/Modified
- `pyproject.toml` - Added `markers` config registering `snapshot` marker
- `tests/conftest.py` - Added bridge/repo/service fixture chain with marker-driven snapshot seeding
- `tests/test_service.py` - Removed per-file fixtures; refactored TestOperatorService and TestAddTask to fixture injection

## Decisions Made
- **Late imports in conftest fixtures:** `tests.doubles.bridge` imports `make_task_dict` from `tests.conftest`, creating a circular import if conftest imports from `tests.doubles` at module level. Solved with late imports inside fixture functions, annotating return types as `Any`.
- **Any return types on fixtures:** Concrete types (InMemoryBridge, BridgeRepository, OperatorService) would require imports that trigger the circular dependency. The `Any` annotation trades type precision for correct module loading, with docstrings documenting actual types.

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Circular import between conftest.py and tests.doubles.bridge**
- **Found during:** Task 1 (adding fixtures to conftest.py)
- **Issue:** Plan specified top-level imports for InMemoryBridge, ConstantMtimeSource, BridgeRepository, and OperatorService in conftest.py. But tests.doubles.bridge already imports make_task_dict from conftest, creating a circular import at module load time.
- **Fix:** Moved all fixture-related imports inside fixture function bodies (late imports) and annotated return types as `Any` instead of concrete types.
- **Files modified:** tests/conftest.py
- **Verification:** All 640 tests pass, pytest collection succeeds, ruff + mypy pass
- **Committed in:** ab58206 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to resolve circular import. No scope creep -- same behavior, different import strategy.

## Issues Encountered
None beyond the circular import deviation documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Marker infrastructure established, ready for plan 05 to apply to TestEditTask (~65 remaining inline constructions)
- Fixture chain in conftest.py is shared across all test files
- No blockers

## Known Stubs
None - all fixtures wired to real bridge/repo/service chain.

## Self-Check: PASSED

- FOUND: tests/conftest.py
- FOUND: tests/test_service.py
- FOUND: pyproject.toml
- FOUND: 26-04-SUMMARY.md
- FOUND: ab58206 (Task 1 commit)
- FOUND: ca9586d (Task 2 commit)

---
*Phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge*
*Completed: 2026-03-21*
