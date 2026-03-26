---
phase: 31-middleware-logging
plan: 01
subsystem: infra
tags: [fastmcp, middleware, logging, cross-cutting]

# Dependency graph
requires:
  - phase: 29-dependency-swap-imports
    provides: FastMCP v3 dependency with Middleware base class
provides:
  - ToolLoggingMiddleware class in middleware.py
  - Automatic entry/exit/error logging for all tool calls
  - Zero-boilerplate logging (no per-tool wiring needed)
affects: [31-02-logging-redesign]

# Tech tracking
tech-stack:
  added: []
  patterns: [middleware-with-injected-logger, cross-cutting-concerns-via-middleware]

key-files:
  created:
    - src/omnifocus_operator/middleware.py
    - tests/test_middleware.py
  modified:
    - src/omnifocus_operator/server.py

key-decisions:
  - "Middleware receives server's logger via injection (D-02) -- all MCP-layer logs under omnifocus_operator namespace"
  - "Response-shape logger.debug() lines preserved in handlers (D-06) -- middleware can't see response content"

patterns-established:
  - "Middleware pattern: cross-cutting concerns via FastMCP Middleware base class with injected logger"

requirements-completed: [MW-01, MW-02, MW-03]

# Metrics
duration: 3min
completed: 2026-03-26
---

# Phase 31 Plan 01: Middleware & Logging Summary

**ToolLoggingMiddleware replaces manual log_tool_call() -- automatic entry/exit/error logging for all 6 tools via FastMCP middleware API**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-26T20:14:38Z
- **Completed:** 2026-03-26T20:17:38Z
- **Tasks:** 2
- **Files modified:** 3

## Accomplishments
- Created ToolLoggingMiddleware with injected logger, timing, and error handling
- Deleted log_tool_call() function and all 6 manual call sites from server.py
- Wired middleware in create_server() -- fires automatically for all current and future tools
- 6 unit tests covering entry/exit/error logging, timing, return value, and exception propagation

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ToolLoggingMiddleware and tests** - `6560703` (test: RED), `1aa30c0` (feat: GREEN)
2. **Task 2: Wire middleware into server, delete log_tool_call** - `e4ab74b` (feat)

_TDD task had separate RED/GREEN commits._

## Files Created/Modified
- `src/omnifocus_operator/middleware.py` - ToolLoggingMiddleware class with injected logger, entry/exit/error logging
- `tests/test_middleware.py` - 6 unit tests for middleware behavior
- `src/omnifocus_operator/server.py` - Deleted log_tool_call, added middleware import and wiring

## Decisions Made
- Middleware receives server's logger via constructor injection (D-02) -- keeps all MCP-layer logs under the same namespace
- Response-shape logger.debug() lines preserved in each handler (D-06) -- middleware only knows timing and success/failure, not response content

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- middleware.py is ready for Plan 02 to import (if needed for logging redesign)
- server.py is clean -- no manual logging boilerplate remains
- Plan 02 (logging redesign) can proceed independently

## Self-Check: PASSED

- All 3 created files exist on disk
- All 3 commit hashes found in git log

---
*Phase: 31-middleware-logging*
*Completed: 2026-03-26*
