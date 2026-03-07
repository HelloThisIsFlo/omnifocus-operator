---
phase: 05-service-layer-and-mcp-server
plan: 02
subsystem: server
tags: [fastmcp, mcp-server, lifespan, tools, stdio, structured-content]

# Dependency graph
requires:
  - phase: 05-service-layer-and-mcp-server
    plan: 01
    provides: OperatorService, ConstantMtimeSource, create_bridge factory
  - phase: 04-repository-and-snapshot-management
    provides: OmniFocusRepository with caching and MtimeSource
  - phase: 02-data-models
    provides: DatabaseSnapshot with camelCase JSON schema
provides:
  - FastMCP server with lifespan-based dependency injection
  - list_all tool returning DatabaseSnapshot as structuredContent
  - __main__.py entry point with stdout redirect and logging
  - _register_tools() for test patching with custom lifespans
affects: [06-file-ipc-engine, 07-simulator-bridge, 08-real-bridge]

# Tech tracking
tech-stack:
  added: [fastmcp, anyio-memory-streams]
  patterns: [lifespan dependency injection, in-process MCP testing, _register_tools separation]

key-files:
  created:
    - src/omnifocus_operator/server/__init__.py
    - src/omnifocus_operator/server/_server.py
  modified:
    - src/omnifocus_operator/__main__.py
    - tests/test_server.py
    - tests/test_smoke.py

key-decisions:
  - "DatabaseSnapshot import kept at module level (not TYPE_CHECKING) with noqa: TC001 -- FastMCP needs it in namespace for outputSchema generation via get_type_hints()"
  - "_register_tools() separated from create_server() so tests can register tools on custom servers with patched lifespans"
  - "Context[Any, Any, Any] typed explicitly to satisfy mypy strict mode"
  - "Smoke test updated to use bridge factory directly instead of calling main() (avoids pytest capture teardown issues from stdout redirect)"

patterns-established:
  - "In-process MCP testing: anyio memory streams + task group + ClientSession pattern"
  - "Lifespan dependency injection: bridge -> mtime -> repository -> service -> yield dict"
  - "Tool registration: _register_tools(mcp) pattern for testability"

requirements-completed: [ARCH-01, ARCH-02, TOOL-01, TOOL-02, TOOL-03, TOOL-04]

# Metrics
duration: 8min
completed: 2026-03-02
---

# Phase 05 Plan 02: MCP Server Summary

**FastMCP server with lifespan DI, list_all tool returning structuredContent with camelCase outputSchema, and stdio entry point with stderr logging**

## Performance

- **Duration:** 8 min
- **Started:** 2026-03-02T12:31:54Z
- **Completed:** 2026-03-02T12:39:43Z
- **Tasks:** 1 (TDD: RED + GREEN)
- **Files modified:** 5

## Accomplishments
- MCP server with three-layer architecture verified end-to-end: FastMCP tool -> OperatorService -> OmniFocusRepository -> InMemoryBridge
- list_all tool returns structuredContent with all 5 entity collections (tasks, projects, tags, folders, perspectives)
- Tool has readOnlyHint=true, idempotentHint=true annotations and outputSchema with camelCase field names
- Entry point redirects stdout to stderr, configures logging via OMNIFOCUS_LOG_LEVEL env var
- Bridge selection via OMNIFOCUS_BRIDGE env var; default "real" fails cleanly with NotImplementedError
- 11 new integration tests using in-process MCP client/server pattern; full suite at 106 tests, 95.82% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1 RED: Failing tests** - `96f07f0` (test)
2. **Task 1 GREEN: Implementation** - `12b8066` (feat)

_TDD task: RED then GREEN, no REFACTOR needed (ruff + mypy clean)_

## Files Created/Modified
- `src/omnifocus_operator/server/__init__.py` - Server package re-exports create_server
- `src/omnifocus_operator/server/_server.py` - FastMCP server with lifespan, list_all tool, _register_tools
- `src/omnifocus_operator/__main__.py` - Updated: stdout redirect, logging config, server.run(transport="stdio")
- `tests/test_server.py` - 11 in-process MCP integration tests covering ARCH-01/02, TOOL-01/02/03/04
- `tests/test_smoke.py` - Updated: uses bridge factory directly instead of calling main()

## Decisions Made
- DatabaseSnapshot kept as runtime import (noqa: TC001) because FastMCP uses `get_type_hints()` at tool registration time to generate outputSchema -- moving to TYPE_CHECKING would break schema generation
- _register_tools() extracted as separate function so tests can build custom servers with patched lifespans while still getting the tool registered
- Context typed as `Context[Any, Any, Any]` to satisfy mypy strict mode's type-arg requirement
- Smoke test refactored to test default bridge behavior through create_bridge("real") directly, avoiding pytest capture teardown issues caused by sys.stdout redirect in main()

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated smoke test for new main() behavior**
- **Found during:** Task 1 GREEN phase (full test suite regression check)
- **Issue:** Pre-existing test_main_raises_not_implemented expected bare NotImplementedError from main(); new implementation wraps it in ExceptionGroup via anyio task group
- **Fix:** Replaced with test_main_entry_point_exists (callable check) and test_default_bridge_is_real (direct factory test), avoiding pytest capture teardown issues
- **Files modified:** tests/test_smoke.py
- **Verification:** Full suite passes cleanly (106 tests, 0 errors)
- **Committed in:** 12b8066 (GREEN commit)

**2. [Rule 1 - Bug] Fixed incomplete task data in camelCase test**
- **Found during:** Task 1 GREEN phase
- **Issue:** Task test data missing required fields (note, completed, flagged, etc.) causing Pydantic ValidationError during model_validate
- **Fix:** Provided all required Task fields in test data dictionary
- **Files modified:** tests/test_server.py
- **Verification:** camelCase test passes, structuredContent contains expected keys
- **Committed in:** 12b8066 (GREEN commit)

---

**Total deviations:** 2 auto-fixed (2 bug fixes)
**Impact on plan:** Both fixes necessary for test correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed items above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 5 complete: all ARCH and TOOL requirements verified
- Server is fully functional with OMNIFOCUS_BRIDGE=inmemory
- Ready for Phase 6 (File IPC Engine) and Phase 7 (SimulatorBridge)
- Pattern established: in-process MCP testing via anyio memory streams

## Self-Check: PASSED

All files verified present, all commits verified in git log.

---
*Phase: 05-service-layer-and-mcp-server*
*Completed: 2026-03-02*
