---
phase: 29-dependency-swap-imports
plan: 01
subsystem: infra
tags: [fastmcp, dependency-management, import-migration, uv]

# Dependency graph
requires: []
provides:
  - "fastmcp>=3.1.1 as sole runtime dependency (replacing mcp>=1.26.0)"
  - "Native FastMCP v3 import patterns in src/"
  - "ctx.lifespan_context shorthand in all tool handlers"
  - "Test infrastructure compatible with FastMCP v3 lifespan protocol"
affects: [30-test-client-middleware, 31-logging-docs-progress]

# Tech tracking
tech-stack:
  added: [fastmcp>=3.1.1]
  patterns: [fastmcp-v3-imports, lifespan-shorthand, lifespan-manager-in-tests]

key-files:
  modified:
    - pyproject.toml
    - src/omnifocus_operator/server.py
    - src/omnifocus_operator/__main__.py
    - tests/conftest.py
    - tests/test_server.py
    - tests/test_simulator_bridge.py
    - tests/test_simulator_integration.py

key-decisions:
  - "ToolAnnotations stays at mcp.types -- fastmcp does not re-export it"
  - "Test infrastructure fixed inline (Rule 3) -- _lifespan_manager() must be entered before _mcp_server.run() in FastMCP v3"
  - "Output schema test adapted for FastMCP v3 inlined schemas (no $defs)"

patterns-established:
  - "from fastmcp import FastMCP, Context -- all src/ imports use standalone fastmcp package"
  - "ctx.lifespan_context shorthand -- no more ctx.request_context.lifespan_context"
  - "Test server helpers enter server._lifespan_manager() before _mcp_server.run()"

requirements-completed: [DEP-01, DEP-02, DEP-03, DEP-04]

# Metrics
duration: 10min
completed: 2026-03-26
---

# Phase 29 Plan 01: Dependency Swap & Import Migration Summary

**Swapped mcp>=1.26.0 for fastmcp>=3.1.1, migrated all src/ imports to native FastMCP v3 patterns, fixed test infrastructure for lifespan compatibility**

## Performance

- **Duration:** 10 min
- **Started:** 2026-03-26T11:47:32Z
- **Completed:** 2026-03-26T11:57:37Z
- **Tasks:** 2
- **Files modified:** 8 (2 src + 1 config + 1 lockfile + 4 test)

## Accomplishments
- Runtime dependency swapped from mcp>=1.26.0 to fastmcp>=3.1.1 (mcp remains as transitive dep)
- All src/ imports migrated to native FastMCP v3 patterns (from fastmcp import FastMCP, Context)
- 6 Context[Any, Any, Any] annotations simplified to plain Context
- 6 ctx.request_context.lifespan_context calls shortened to ctx.lifespan_context
- Spike dependency group deleted from pyproject.toml
- TODO comments mark Phase 30 (ToolAnnotations) and Phase 31 (logging redesign) deferred work
- All 697 tests pass, 98% coverage

## Task Commits

Each task was committed atomically:

1. **Task 1: Dependency swap and uv sync** - `fc8cdff` (chore)
2. **Task 2: Migrate server.py imports, Context types, and lifespan shorthand** - `f364645` (feat)

## Files Created/Modified
- `pyproject.toml` - Replaced mcp>=1.26.0 with fastmcp>=3.1.1, deleted spike group
- `uv.lock` - Resolved new dependency tree
- `src/omnifocus_operator/server.py` - Import migration, Context simplification, lifespan shorthand, TODO comment
- `src/omnifocus_operator/__main__.py` - TODO(Phase 31) comment replacing misleading logging comment
- `tests/conftest.py` - Fixed server fixture to use fastmcp.FastMCP, added _lifespan_manager() entry
- `tests/test_server.py` - Fixed run_with_client, _build_patched_server, degraded mode tests, output schema test
- `tests/test_simulator_bridge.py` - Fixed _run_with_client, replaced direct FastMCP() with create_server()
- `tests/test_simulator_integration.py` - Fixed _run_with_client for lifespan manager

## Decisions Made
- ToolAnnotations stays at `from mcp.types import ToolAnnotations` -- fastmcp does not re-export it (confirmed by research)
- `Any` import kept in server.py -- still needed for `dict[str, Any]` in tool parameter types
- Test infrastructure fixed as part of this plan (Rule 3: blocking) rather than deferring to Phase 30

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] FastMCP v3 lifespan protocol requires _lifespan_manager() in tests**
- **Found during:** Task 2 (running test suite after import migration)
- **Issue:** FastMCP v3 wraps the user lifespan with `_lifespan_proxy` that checks `_lifespan_result_set`. Tests calling `_mcp_server.run()` directly bypass this, causing RuntimeError.
- **Fix:** Updated all `_run_server`/`_run_with_client` helpers to enter `server._lifespan_manager()` before `_mcp_server.run()`. Used `hasattr` guard for backward compat with old mcp.server.fastmcp.FastMCP.
- **Files modified:** tests/test_server.py, tests/conftest.py, tests/test_simulator_bridge.py, tests/test_simulator_integration.py
- **Verification:** All 697 tests pass
- **Committed in:** f364645

**2. [Rule 3 - Blocking] Tests creating FastMCP from mcp.server.fastmcp get wrong Context type**
- **Found during:** Task 2 (test_get_all_structured_content_is_camelcase failure)
- **Issue:** `mcp.server.fastmcp.FastMCP` and `fastmcp.FastMCP` are different classes. Tests using old FastMCP couldn't inject the new `fastmcp.Context` type for tool handlers. Tool calls returned "ctx field required" validation errors.
- **Fix:** Updated `_build_patched_server` to use `from fastmcp import FastMCP`, updated conftest `server` fixture to import from `fastmcp`, replaced 5 direct `FastMCP(...)` calls with `create_server()`.
- **Files modified:** tests/test_server.py, tests/conftest.py, tests/test_simulator_bridge.py
- **Verification:** All 697 tests pass
- **Committed in:** f364645

**3. [Rule 1 - Bug] Output schema test assumed $defs structure**
- **Found during:** Task 2 (test_output_schema_uses_camelcase failure)
- **Issue:** FastMCP v3 generates inlined JSON schemas rather than using `$defs` references. Test asserted `"Task" in schema["$defs"]` which no longer exists.
- **Fix:** Updated test to check `tasks.items.properties` directly (where FastMCP v3 inlines the Task schema). CamelCase verification still intact.
- **Files modified:** tests/test_server.py
- **Verification:** Test passes, still verifies camelCase field names
- **Committed in:** f364645

---

**Total deviations:** 3 auto-fixed (1 bug, 2 blocking)
**Impact on plan:** All auto-fixes necessary for tests to pass after the import migration. No scope creep -- these are direct consequences of swapping the dependency.

## Issues Encountered
None beyond the auto-fixed deviations above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- Server runs on fastmcp>=3.1.1 with all 6 tools functional
- Test infrastructure compatible with FastMCP v3 lifespan protocol
- Ready for Phase 29 Plan 02 (progress reporting and documentation updates)
- Ready for Phase 30 (test client migration to Client(server) pattern)

---
*Phase: 29-dependency-swap-imports*
*Completed: 2026-03-26*
