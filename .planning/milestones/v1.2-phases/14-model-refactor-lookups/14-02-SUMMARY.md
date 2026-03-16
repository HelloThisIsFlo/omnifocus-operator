---
phase: 14-model-refactor-lookups
plan: 02
subsystem: api
tags: [mcp, sqlite, repository, get-by-id, lookup]

# Dependency graph
requires:
  - phase: 14-01
    provides: ParentRef model, unified parent field on Task
provides:
  - get_task, get_project, get_tag MCP tools
  - Repository protocol with single-entity lookup methods
  - Dedicated SQLite single-entity queries in HybridRepository
affects: [15-task-writes, 16-read-tools]

# Tech tracking
tech-stack:
  added: []
  patterns: [single-entity SQLite queries with targeted lookups, ValueError for not-found -> MCP isError]

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/protocol.py
    - src/omnifocus_operator/repository/hybrid.py
    - src/omnifocus_operator/repository/in_memory.py
    - src/omnifocus_operator/repository/bridge.py
    - src/omnifocus_operator/service.py
    - src/omnifocus_operator/server.py
    - tests/test_hybrid_repository.py
    - tests/test_service.py
    - tests/test_server.py

key-decisions:
  - "HybridRepository uses dedicated single-entity SQLite queries (not _read_all filter) for get-by-ID"
  - "Not-found raises ValueError which MCP SDK auto-wraps as isError: true"
  - "BridgeRepository delegates through get_all() then filters (bridge only speaks full snapshots)"

patterns-established:
  - "Single-entity lookup pattern: repository returns None, service passes through, server raises ValueError"
  - "Targeted SQLite reads: build only needed lookups (tags, parent ref) per entity"

requirements-completed: [LOOK-01, LOOK-02, LOOK-03, LOOK-04]

# Metrics
duration: 5min
completed: 2026-03-07
---

# Phase 14 Plan 02: Get-by-ID Tools Summary

**Three MCP lookup tools (get_task, get_project, get_tag) with dedicated SQLite queries and not-found error handling**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-07T23:21:51Z
- **Completed:** 2026-03-07T23:26:27Z
- **Tasks:** 2
- **Files modified:** 9

## Accomplishments
- Repository protocol extended with get_task, get_project, get_tag returning entity | None
- HybridRepository: dedicated single-entity SQLite queries with targeted tag/parent lookups
- Three MCP tools with readOnlyHint + idempotentHint annotations
- Not-found IDs produce isError: true with clear messages
- Full suite: 348 tests (35 new get-by-ID tests)

## Task Commits

Each task was committed atomically (TDD: test then feat):

1. **Task 1: Repository protocol and implementations** - `cfd82c8` (test) + `6bd6c8e` (feat)
2. **Task 2: Service layer, MCP tools, integration tests** - `da3120f` (test) + `6953cb9` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/protocol.py` - Added get_task, get_project, get_tag to Protocol
- `src/omnifocus_operator/repository/hybrid.py` - Dedicated _read_task, _read_project, _read_tag with async wrappers
- `src/omnifocus_operator/repository/in_memory.py` - Filter in-memory snapshot by ID
- `src/omnifocus_operator/repository/bridge.py` - Delegate through get_all() then filter
- `src/omnifocus_operator/service.py` - Three delegation methods
- `src/omnifocus_operator/server.py` - Three MCP tool registrations with ValueError on not-found
- `tests/test_hybrid_repository.py` - TestGetTask (7), TestGetProject (2), TestGetTag (2)
- `tests/test_service.py` - Service delegation tests (6)
- `tests/test_server.py` - MCP integration tests (9): success, not-found, annotations

## Decisions Made
- HybridRepository uses dedicated single-entity SQLite queries (not filtering _read_all output) for efficiency
- Not-found raises ValueError which MCP SDK auto-wraps as isError: true
- BridgeRepository delegates through get_all() since bridge only speaks full snapshots
- Task, Project, Tag are runtime imports in server.py (not TYPE_CHECKING) for FastMCP outputSchema generation

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All get-by-ID tools complete, ready for phase 15 (task writes)
- 348 tests passing, all existing + 35 new

## Self-Check: PASSED

All 9 modified files exist. All 4 commit hashes verified.

---
*Phase: 14-model-refactor-lookups*
*Completed: 2026-03-07*
