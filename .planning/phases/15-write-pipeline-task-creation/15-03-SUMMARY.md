---
phase: 15-write-pipeline-task-creation
plan: 03
subsystem: server, mcp-tools
tags: [mcp, fastmcp, tool-registration, integration-testing, write-pipeline]

# Dependency graph
requires:
  - phase: 15-write-pipeline-task-creation
    plan: 02
    provides: Service.add_task with validation, Repository.add_task protocol
provides:
  - add_tasks MCP tool callable by agents via MCP protocol
  - End-to-end integration tests through full MCP stack
affects: [phase-16, uat]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Write tool uses list[dict] input with model_validate for camelCase support"
    - "FastMCP wraps list returns in {result: [...]} structuredContent"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/server.py
    - tests/test_server.py

key-decisions:
  - "items parameter is list[dict[str, Any]] not list[TaskCreateSpec] -- MCP clients send raw JSON, model_validate handles camelCase alias resolution"
  - "FastMCP wraps list return types in {result: [...]} structuredContent dict"

patterns-established:
  - "Write tools: readOnlyHint=False, destructiveHint=False, idempotentHint=False"
  - "Single-item constraint with ValueError for clear error messaging"

requirements-completed: [CREA-01, CREA-02, CREA-03, CREA-04, CREA-05, CREA-06, CREA-07, CREA-08]

# Metrics
duration: 3min
completed: 2026-03-08
---

# Phase 15 Plan 03: MCP Tool Registration & Integration Tests Summary

**add_tasks MCP tool with single-item constraint, camelCase input via model_validate, and 12 end-to-end integration tests through full MCP protocol stack**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-08T00:29:36Z
- **Completed:** 2026-03-08T00:32:19Z
- **Tasks:** 2
- **Files modified:** 2

## Accomplishments
- add_tasks MCP tool registered with write annotations (readOnlyHint=False)
- Single-item constraint enforced with clear ValueError message
- 12 integration tests covering registration, annotations, happy path, constraints, validation errors, and post-write freshness
- Full MCP protocol path verified: client -> server -> service -> repository

## Task Commits

Each task was committed atomically (TDD: RED then GREEN):

1. **Task 1: Register add_tasks MCP tool** - `173508b` (test), `4729e60` (feat)
2. **Task 2: End-to-end integration tests** - included in Task 1 commits (TDD tests written first)

## Files Created/Modified
- `src/omnifocus_operator/server.py` - add_tasks tool registration with write annotations and single-item constraint
- `tests/test_server.py` - TestAddTasks class with 12 integration tests

## Decisions Made
- items parameter typed as `list[dict[str, Any]]` (not `list[TaskCreateSpec]`) because MCP clients send raw JSON dicts; `TaskCreateSpec.model_validate()` handles camelCase alias resolution
- Discovered FastMCP wraps list return types in `{"result": [...]}` structuredContent -- tests adjusted accordingly

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] FastMCP list return wrapping**
- **Found during:** Task 1 (GREEN phase)
- **Issue:** Tests expected `structuredContent` to be a list directly, but FastMCP wraps list returns in `{"result": [...]}`
- **Fix:** Updated test assertions to access `result.structuredContent["result"]` for list results
- **Files modified:** tests/test_server.py
- **Verification:** All 12 tests pass
- **Committed in:** 4729e60 (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Test assertion fix only. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- add_tasks tool fully wired and tested end-to-end
- All 391 tests passing (12 new integration tests)
- Ready for UAT verification against live OmniFocus
- Phase 15 complete -- all 3 plans executed

---
*Phase: 15-write-pipeline-task-creation*
*Completed: 2026-03-08*

## Self-Check: PASSED
