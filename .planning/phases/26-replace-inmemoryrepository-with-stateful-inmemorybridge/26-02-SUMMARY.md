---
phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
plan: 02
subsystem: testing
tags: [test-doubles, bridge, repository, migration, fixture-composition]

# Dependency graph
requires:
  - phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge
    plan: 01
    provides: "Stateful InMemoryBridge with add_task/edit_task/get_all dispatch"
provides:
  - "InMemoryRepository fully removed from codebase"
  - "All test files use BridgeRepository + InMemoryBridge for write test fidelity"
  - "Fixture composition (bridge -> repo) in test_service.py and test_service_resolve.py"
affects: [27-repository-contract-tests]

# Tech tracking
tech-stack:
  added: []
  patterns: ["fixture composition: bridge fixture -> repo fixture per D-11/D-12/D-13"]

key-files:
  created: []
  modified:
    - tests/test_service.py
    - tests/test_server.py
    - tests/test_service_resolve.py
    - tests/test_simulator_bridge.py
    - tests/test_repository.py
    - tests/test_bridge.py
    - tests/test_service_domain.py
    - tests/doubles/__init__.py
    - tests/doubles/bridge.py
  deleted:
    - tests/doubles/repository.py

key-decisions:
  - "Inline BridgeRepository construction for tests with custom snapshot data (most tests), fixture injection for default-snapshot tests"
  - "Identity assertion (assert result is snapshot) replaced with structural equality check (BridgeRepository deserializes fresh each call)"
  - "str(datetime) assertions replaced with .isoformat() for correct ISO format comparison through serialization round-trip"

patterns-established:
  - "All write tests exercise real serialization path: service -> BridgeWriteMixin._send_to_bridge (model_dump by_alias=True) -> InMemoryBridge"

requirements-completed: [INFRA-11, INFRA-12]

# Metrics
duration: 12min
completed: 2026-03-21
---

# Phase 26 Plan 02: Delete InMemoryRepository and Migrate All Tests Summary

**All test files migrated from InMemoryRepository to BridgeRepository + InMemoryBridge; InMemoryRepository deleted; write tests now exercise real serialization path**

## Performance

- **Duration:** 12 min
- **Started:** 2026-03-21T01:50:31Z
- **Completed:** 2026-03-21T02:02:42Z
- **Tasks:** 2
- **Files modified:** 10 (1 deleted)

## Accomplishments
- Migrated 121 InMemoryRepository sites across 4 test files to BridgeRepository + InMemoryBridge
- Deleted InMemoryRepository module and removed from all exports
- All 640 tests pass with 98% coverage, no behavioral changes
- Write tests now exercise BridgeWriteMixin._send_to_bridge (model_dump by_alias=True) serialization path

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate test_service.py, test_server.py, test_service_resolve.py, test_simulator_bridge.py** - `da881de` (feat)
2. **Task 2: Delete InMemoryRepository, update exports and guard tests** - `4b30006` (feat)

## Files Created/Modified
- `tests/test_service.py` - 94 InMemoryRepository sites migrated, bridge/repo fixtures added, identity check replaced with structural equality
- `tests/test_server.py` - 17 sites migrated (monkeypatch lambdas + _make_server_with_data helpers)
- `tests/test_service_resolve.py` - 6 sites migrated, bridge/repo/resolver fixture chain added per D-11
- `tests/test_simulator_bridge.py` - 4 sites migrated, helper renamed _make_in_memory_repo -> _make_repo
- `tests/test_repository.py` - Removed TestInMemoryRepository, TestInMemoryAddTask, TestInMemoryEditTaskLifecycle classes
- `tests/test_bridge.py` - Added test_in_memory_repository_not_in_doubles_exports guard test
- `tests/test_service_domain.py` - Comment references to InMemoryRepository removed
- `tests/doubles/__init__.py` - InMemoryRepository removed from exports
- `tests/doubles/repository.py` - DELETED (InMemoryRepository module)
- `tests/doubles/bridge.py` - InMemoryBridge edit_task move handler now sets parent dict with type/name resolution

## Decisions Made
- **Inline construction for custom-snapshot tests:** Most tests use `make_snapshot_dict(tasks=[...], tags=[...])` with overrides, so inline BridgeRepository+InMemoryBridge construction is cleaner than fixture injection with parametrization. Default-snapshot tests can use the shared `bridge`/`repo` fixtures.
- **Identity assertion replaced with structural equality:** `assert result is snapshot` (line 50 of test_service.py) changed to `assert len(result.tasks) == 1; assert result.tasks[0].id == "task-001"` because BridgeRepository deserializes a fresh AllEntities on each get_all() call.
- **datetime assertions use .isoformat():** `str(task.defer_date)` comparison changed to `task.defer_date.isoformat()` because the serialization round-trip through BridgeRepository produces proper datetime objects where `str()` uses space-separator, but the tests expected T-separator (ISO 8601).

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] InMemoryBridge move handler missing parent dict resolution**
- **Found during:** Task 1 (test_move_to_project_ending failure)
- **Issue:** InMemoryBridge's _handle_edit_task set `inInbox=False` on move but did not set the `parent` dict with type/id/name. Tests that verified `task.parent is not None` after a move failed.
- **Fix:** Added parent resolution logic: checks _projects then _tasks to determine type, sets `task["parent"] = {"type": ..., "id": ..., "name": ...}`.
- **Files modified:** tests/doubles/bridge.py
- **Verification:** All 197 tests in migrated files pass
- **Committed in:** da881de (Task 1 commit)

**2. [Rule 1 - Bug] datetime assertion format mismatch through serialization round-trip**
- **Found during:** Task 1 (test_set_defer_and_planned_dates failure)
- **Issue:** Old InMemoryRepository stored dates as strings via setattr (bypassing Pydantic validation), so `str(task.defer_date)` returned the original ISO string with T-separator. With BridgeRepository, dates are properly parsed into datetime objects, and `str(datetime)` uses space-separator instead of T.
- **Fix:** Changed `str(task.defer_date) == "..."` to `task.defer_date.isoformat() == "..."` for correct ISO format comparison.
- **Files modified:** tests/test_service.py
- **Verification:** All tests pass
- **Committed in:** da881de (Task 1 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correct test migration. InMemoryBridge's move handler was incomplete (Plan 01 only implemented simplified move), and the datetime comparison was a pre-existing fragility exposed by the migration.

## Issues Encountered
None beyond the deviations documented above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- InMemoryRepository fully deleted, all tests use BridgeRepository + InMemoryBridge
- Phase 27 (repository contract tests) can now validate behavioral equivalence between InMemoryBridge and RealBridge
- No blockers

## Known Stubs
None - all tests wired to real BridgeRepository path.

## Self-Check: PASSED

- FOUND: tests/test_service.py
- FOUND: tests/test_server.py
- FOUND: tests/test_service_resolve.py
- FOUND: tests/test_simulator_bridge.py
- FOUND: tests/doubles/__init__.py
- FOUND: tests/doubles/bridge.py
- CONFIRMED DELETED: tests/doubles/repository.py
- FOUND: da881de (Task 1 commit)
- FOUND: 4b30006 (Task 2 commit)
- FOUND: 26-02-SUMMARY.md

---
*Phase: 26-replace-inmemoryrepository-with-stateful-inmemorybridge*
*Completed: 2026-03-21*
