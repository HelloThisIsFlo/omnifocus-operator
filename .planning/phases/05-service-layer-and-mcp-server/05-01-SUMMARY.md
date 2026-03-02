---
phase: 05-service-layer-and-mcp-server
plan: 01
subsystem: service
tags: [service-layer, bridge-factory, mtime, dependency-injection]

# Dependency graph
requires:
  - phase: 04-repository-and-snapshot-management
    provides: OmniFocusRepository with MtimeSource protocol
  - phase: 03-bridge-protocol-and-inmemorybridge
    provides: Bridge protocol, InMemoryBridge, BridgeError hierarchy
provides:
  - OperatorService thin passthrough to repository
  - ConstantMtimeSource for InMemoryBridge (no cache invalidation)
  - create_bridge factory function routing inmemory/simulator/real
affects: [05-02-mcp-server, 07-simulator-bridge, 08-real-bridge]

# Tech tracking
tech-stack:
  added: []
  patterns: [service-layer passthrough, bridge factory with match/case, runtime_checkable protocol]

key-files:
  created:
    - src/omnifocus_operator/service/__init__.py
    - src/omnifocus_operator/service/_service.py
    - src/omnifocus_operator/bridge/_factory.py
    - tests/test_service.py
  modified:
    - src/omnifocus_operator/repository/_mtime.py
    - src/omnifocus_operator/repository/__init__.py
    - src/omnifocus_operator/bridge/__init__.py

key-decisions:
  - "Bridge factory placed in bridge/_factory.py (bridge concern, not server concern)"
  - "Added @runtime_checkable to MtimeSource protocol for isinstance checks in tests"
  - "create_bridge returns empty collections for inmemory (not None/default snapshot)"

patterns-established:
  - "Service layer: thin passthrough delegating to repository (OperatorService pattern)"
  - "Bridge factory: match/case routing with NotImplementedError for future bridges"
  - "ConstantMtimeSource: always-zero pattern for test/inmemory scenarios"

requirements-completed: [ARCH-01, ARCH-02]

# Metrics
duration: 2min
completed: 2026-03-02
---

# Phase 05 Plan 01: Service Layer Foundations Summary

**OperatorService passthrough to repository, ConstantMtimeSource for InMemoryBridge, and create_bridge factory with match/case routing**

## Performance

- **Duration:** 2 min
- **Started:** 2026-03-02T12:26:58Z
- **Completed:** 2026-03-02T12:29:15Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 7

## Accomplishments
- OperatorService delegates get_all_data() to repository.get_snapshot() as a thin passthrough
- ConstantMtimeSource always returns 0 for InMemoryBridge usage (no cache invalidation)
- Bridge factory correctly routes inmemory/simulator/real/unknown with appropriate errors
- 10 new tests, full suite at 94 tests passing with 99.24% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `acc15f0` (test)
2. **Task 1 GREEN: Implementation** - `28505f5` (feat)

_TDD task: RED then GREEN, no REFACTOR needed (ruff + mypy clean)_

## Files Created/Modified
- `src/omnifocus_operator/service/__init__.py` - Service package re-exports OperatorService
- `src/omnifocus_operator/service/_service.py` - OperatorService class with get_all_data()
- `src/omnifocus_operator/bridge/_factory.py` - create_bridge() factory function
- `src/omnifocus_operator/repository/_mtime.py` - Added ConstantMtimeSource, @runtime_checkable on MtimeSource
- `src/omnifocus_operator/repository/__init__.py` - Re-exports ConstantMtimeSource
- `src/omnifocus_operator/bridge/__init__.py` - Re-exports create_bridge
- `tests/test_service.py` - 10 tests for OperatorService, ConstantMtimeSource, bridge factory

## Decisions Made
- Bridge factory placed in `bridge/_factory.py` rather than `server/_factory.py` since it's a bridge concern (selecting which bridge to create)
- Added `@runtime_checkable` to MtimeSource protocol to support isinstance checks in tests
- create_bridge("inmemory") returns InMemoryBridge with empty collections (not None default)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Added @runtime_checkable to MtimeSource protocol**
- **Found during:** Task 1 GREEN phase
- **Issue:** test_satisfies_mtime_protocol used isinstance(source, MtimeSource) but MtimeSource lacked @runtime_checkable
- **Fix:** Added @runtime_checkable decorator to MtimeSource Protocol class
- **Files modified:** src/omnifocus_operator/repository/_mtime.py
- **Verification:** isinstance check passes, mypy clean, ruff clean
- **Committed in:** 28505f5 (GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug fix)
**Impact on plan:** Minor -- @runtime_checkable is the standard way to enable Protocol isinstance checks. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Service layer ready for MCP server wiring (Plan 02)
- OperatorService, ConstantMtimeSource, and create_bridge are independently tested building blocks
- Plan 02 will wire these together via FastMCP server

## Self-Check: PASSED

All files verified present, all commits verified in git log.

---
*Phase: 05-service-layer-and-mcp-server*
*Completed: 2026-03-02*
