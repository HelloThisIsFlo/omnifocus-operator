---
phase: 30-test-client-migration
plan: 02
subsystem: testing
tags: [fastmcp, client, pytest, test-migration, snake-case, cleanup]

# Dependency graph
requires:
  - phase: 30-test-client-migration
    plan: 01
    provides: "Client fixture, fixture-based test migration"
provides:
  - "All run_with_client / _run_with_client helpers deleted from all 3 test files"
  - "All 18 callback-indirection callers migrated to inline Client(server) pattern"
  - "Dead imports cleaned: anyio, ClientSession, SessionMessage, mcp.server.fastmcp"
  - "_build_patched_server cleaned: FastMCPv3 alias removed, clean fastmcp import"
affects: []

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Inline Client(server): async with Client(server) as client for monkeypatched server tests"
    - "Degraded mode + ToolError: pytest.raises(ToolError) inside async with Client(server)"
    - "Caplog + ToolError: catch ToolError with pytest.raises inside caplog context"

key-files:
  created: []
  modified:
    - "tests/test_server.py"
    - "tests/test_simulator_bridge.py"
    - "tests/test_simulator_integration.py"

key-decisions:
  - "Remove repo param from _build_patched_server -- only service needed for lifespan injection"
  - "Preserve structuredContent in class docstrings -- describes JSON key verification, not Python attribute access"

patterns-established:
  - "Inline Client pattern for custom-server tests: create_server() + async with Client(server)"
  - "Sweep tests use _client naming convention for unused client variable"

requirements-completed: [TEST-02, TEST-03, TEST-05]

# Metrics
duration: 5min
completed: 2026-03-26
---

# Phase 30 Plan 02: run_with_client Migration + Dead Import Cleanup Summary

**Deleted all run_with_client helpers (~120 lines of anyio/stream plumbing), migrated 18 callers to inline Client(server), cleaned all dead mcp.* imports across 3 test files**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-26T17:55:35Z
- **Completed:** 2026-03-26T18:01:30Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Deleted run_with_client from test_server.py (40 lines) and _run_with_client from 2 simulator test files (~40 lines each)
- Converted 14 callback-indirection callers in test_server.py to inline Client(server)
- Converted 3 callers in test_simulator_bridge.py and 1 in test_simulator_integration.py
- Fixed _build_patched_server: removed FastMCPv3 alias, Phase 29 TODO comment, unused repo param
- Cleaned all dead imports: anyio, ClientSession, SessionMessage, mcp.server.fastmcp.FastMCP
- Added from fastmcp import Client to all 3 files
- Converted 3 degraded mode tests to pytest.raises(ToolError) pattern
- Updated field accessors: structuredContent -> structured_content, tools_result.tools -> tools
- All 697 tests pass with zero regressions

## Task Commits

Each task was committed atomically:

1. **Task 1: Migrate run_with_client callers and clean up test_server.py** - `6f6bdc0` (feat)
2. **Task 2: Migrate simulator test files and final verification** - `d91f97c` (feat)

## Files Created/Modified
- `tests/test_server.py` - Deleted run_with_client, migrated 14 callers, cleaned imports, fixed _build_patched_server
- `tests/test_simulator_bridge.py` - Deleted _run_with_client, migrated 3 callers, cleaned imports
- `tests/test_simulator_integration.py` - Deleted _run_with_client, migrated 1 caller, cleaned imports

## Decisions Made
- Removed `repo` param from `_build_patched_server` -- only `service` is needed for lifespan injection; `repo` was unused inside the function
- Preserved `structuredContent` in 2 class docstrings -- they describe JSON key format, not Python attribute access (consistent with Plan 01 decision)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Phase 30 (test-client-migration) is complete
- All test files fully migrated to FastMCP Client pattern
- No manual MCP plumbing remains in any test file
- Zero imports of anyio, ClientSession, or SessionMessage in test code

## Self-Check: PASSED

- All 3 modified files exist
- Both task commits verified (6f6bdc0, d91f97c)
- 697 tests passing

---
*Phase: 30-test-client-migration*
*Completed: 2026-03-26*
