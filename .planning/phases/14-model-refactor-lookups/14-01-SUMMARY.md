---
phase: 14-model-refactor-lookups
plan: 01
subsystem: models
tags: [pydantic, refactor, mcp-tools]

# Dependency graph
requires: []
provides:
  - ParentRef model (type/id/name) for unified parent references
  - Task.parent as ParentRef | None (replaces separate project/parent strings)
  - get_all MCP tool (renamed from list_all)
affects: [14-model-refactor-lookups, 15-get-by-id, 16-task-writes]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "ParentRef pattern: type discriminator (project/task) + id + name"
    - "Adapter parent transformation: bridge strings -> ParentRef dict"
    - "SQLite parent mapping: ProjectInfo JOIN for project ID/name, task name lookup for parent tasks"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/common.py
    - src/omnifocus_operator/models/task.py
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/bridge/adapter.py
    - src/omnifocus_operator/repository/hybrid.py
    - src/omnifocus_operator/server.py
    - tests/conftest.py
    - tests/test_models.py
    - tests/test_adapter.py
    - tests/test_hybrid_repository.py
    - tests/test_server.py
    - tests/test_simulator_bridge.py
    - tests/test_simulator_integration.py

key-decisions:
  - "Parent task takes precedence over containing project when both are set (subtask case)"
  - "Bridge adapter uses empty string for name fields since bridge.js does not send parentName/projectName"

patterns-established:
  - "ParentRef: unified parent reference with type discriminator for project vs task"

requirements-completed: [NAME-01, MODL-01, MODL-02]

# Metrics
duration: 5min
completed: 2026-03-07
---

# Phase 14 Plan 01: Model Refactor & Tool Rename Summary

**Unified Task.parent as ParentRef(type/id/name) replacing separate project+parent strings, renamed list_all to get_all**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-07T23:13:44Z
- **Completed:** 2026-03-07T23:19:13Z
- **Tasks:** 2 (Task 1 was TDD: red/green)
- **Files modified:** 13

## Accomplishments
- ParentRef model added to models/common.py with type/id/name fields
- Task model reduced from 27 to 26 fields (project + parent merged into single parent: ParentRef | None)
- Bridge adapter transforms old project/parent strings into ParentRef dict shape
- HybridRepository builds ParentRef via ProjectInfo JOIN and task name lookup from SQLite
- MCP tool renamed from list_all to get_all across server and all tests
- All 322 tests pass

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests for ParentRef** - `68143a3` (test)
2. **Task 1 (GREEN): ParentRef model, unified Task.parent, adapters** - `6683118` (feat)
3. **Task 2: Rename list_all to get_all** - `8d0c793` (feat)

_Note: Task 1 followed TDD (red -> green). No refactor phase needed._

## Files Created/Modified
- `src/omnifocus_operator/models/common.py` - Added ParentRef(type, id, name)
- `src/omnifocus_operator/models/task.py` - Replaced project+parent with parent: ParentRef | None
- `src/omnifocus_operator/models/__init__.py` - Added ParentRef to exports and model_rebuild
- `src/omnifocus_operator/bridge/adapter.py` - Added _adapt_parent_ref for bridge -> ParentRef
- `src/omnifocus_operator/repository/hybrid.py` - Added _build_parent_ref, ProjectInfo JOIN, task name lookup
- `src/omnifocus_operator/server.py` - Renamed list_all to get_all
- `tests/conftest.py` - Updated make_task_dict (27->26 fields, unified parent)
- `tests/test_models.py` - Added ParentRef tests, updated Task tests
- `tests/test_adapter.py` - Added parent ref transformation tests
- `tests/test_hybrid_repository.py` - Rewrote relationship tests for ParentRef
- `tests/test_server.py` - Updated all list_all -> get_all references
- `tests/test_simulator_bridge.py` - Updated list_all -> get_all
- `tests/test_simulator_integration.py` - Updated list_all -> get_all

## Decisions Made
- Parent task takes precedence over containing project (subtask has parent type "task", not "project")
- Bridge adapter uses empty string for name when bridge doesn't send name fields
- Skill file updated to reference get_all (deviation from plan scope, but necessary for correctness)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Updated skill file references from list_all to get_all**
- **Found during:** Task 2 (rename)
- **Issue:** .claude/skills/test-omnifocus-operator/SKILL.md referenced old tool name and MCP tool ID
- **Fix:** Replaced all list_all references with get_all
- **Files modified:** .claude/skills/test-omnifocus-operator/SKILL.md
- **Verification:** grep confirms no remaining list_all references
- **Committed in:** `1c1f1c3`

**2. [Rule 1 - Bug] Fixed test_simulator_integration.py references to list_all**
- **Found during:** Task 2 (rename)
- **Issue:** test_simulator_integration.py also called list_all by name
- **Fix:** Updated all references to get_all
- **Files modified:** tests/test_simulator_integration.py
- **Verification:** Full test suite passes (322 tests)
- **Committed in:** `8d0c793` (part of Task 2 commit)

---

**Total deviations:** 2 auto-fixed (2 bugs)
**Impact on plan:** Both fixes necessary for correctness. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- ParentRef model ready for use by get-by-ID tools (Plan 02)
- get_all tool name established for all future references
- All tests green, model field counts updated

---
*Phase: 14-model-refactor-lookups*
*Completed: 2026-03-07*
