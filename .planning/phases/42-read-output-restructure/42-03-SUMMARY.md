---
phase: 42-read-output-restructure
plan: 03
subsystem: repository
tags: [bridge-adapter, filters, test-fixtures, cross-path-equivalence]

requires:
  - phase: 42-01
    provides: "New model types (ParentRef tagged wrapper, ProjectRef, TaskRef, FolderRef, TagRef)"
  - phase: 42-02
    provides: "Hybrid mapper functions producing enriched {id, name} refs"
provides:
  - "Bridge adapter produces tagged ParentRef + ProjectRef on tasks"
  - "Bridge adapter enriches project/tag/folder cross-entity refs from bare IDs to {id, name}"
  - "Bridge_only filters use new field paths (t.project.id, p.folder.id)"
  - "All 1598 tests pass with new model shapes"
  - "Cross-path equivalence verified (bridge and SQLite paths produce identical output)"
affects: [golden-master-recapture]

tech-stack:
  added: []
  patterns:
    - "Cross-entity enrichment in bridge adapter: build name lookup dicts before per-entity adaptation"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/bridge_only/adapter.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/simulator/data.py
    - tests/conftest.py
    - tests/test_adapter.py
    - tests/test_cross_path_equivalence.py
    - tests/test_hybrid_repository.py
    - tests/test_models.py
    - tests/test_server.py
    - tests/test_service.py
    - tests/test_service_domain.py

key-decisions:
  - "Simulator data updated in-place to new model-ready shape (tagged parent, enriched refs) rather than adding adapter pass"

patterns-established:
  - "Bridge adapter enrichment pattern: name lookup dicts built once, passed to _enrich_* helpers"

requirements-completed: [READ-07]

duration: 17min
completed: 2026-04-06
---

# Phase 42 Plan 03: Bridge Adapter & Test Suite Alignment Summary

**Bridge adapter rewritten to produce tagged ParentRef + enriched refs, bridge_only filters fixed for new field paths, all 1598 tests green across both code paths**

## Performance

- **Duration:** 17 min
- **Started:** 2026-04-06T19:36:41Z
- **Completed:** 2026-04-06T19:54:12Z
- **Tasks:** 2
- **Files modified:** 14

## Accomplishments
- Rewrote `_adapt_parent_ref` to produce tagged dict (`{"project": {id,name}}` or `{"task": {id,name}}`) plus required `project` field using SYSTEM_LOCATIONS for inbox
- Added `_enrich_project`, `_enrich_tag`, `_enrich_folder` helpers and cross-entity name lookup in `adapt_snapshot`
- Fixed bridge_only `list_tasks` in_inbox filter (uses `t.project.id == $inbox`) and project_ids filter (uses `t.project.id`)
- Fixed bridge_only `list_projects` folder_ids filter (uses `p.folder.id`)
- Updated all test assertions across 9 test files for new model shapes
- Fixed production code: `domain.py` cycle detection and no-op detection use new ParentRef shape
- Added missing SYSTEM_LOCATIONS import to hybrid.py (Wave 2 gap)
- Updated simulator data to new model-ready shape

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite bridge adapter and fix bridge_only filters** - `b3b56af` (feat)
2. **Task 2: Update test fixtures and cross-path equivalence tests** - `e412838` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/bridge_only/adapter.py` - Rewrote _adapt_parent_ref, added enrichment helpers and lookup dicts
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` - Fixed in_inbox, project_ids, folder_ids filters; added SYSTEM_LOCATIONS import
- `src/omnifocus_operator/repository/hybrid/hybrid.py` - Added missing SYSTEM_LOCATIONS import from Wave 2
- `src/omnifocus_operator/service/domain.py` - Fixed cycle detection and no-op detection for new ParentRef shape
- `src/omnifocus_operator/simulator/data.py` - Updated all entities to new model-ready shape
- `tests/conftest.py` - make_model_task_dict uses tagged parent + project
- `tests/test_adapter.py` - Parent ref tests updated for new tagged shape
- `tests/test_cross_path_equivalence.py` - Assertions updated for .project.id, .folder.id
- `tests/test_hybrid_repository.py` - All parent, folder, tag, next_task assertions updated
- `tests/test_models.py` - ParentRef tests rewritten for tagged wrapper, round-trip tests updated
- `tests/test_server.py` - Server integration tests updated for new output shapes
- `tests/test_service.py` - Move, inbox, and add_task assertions updated
- `tests/test_service_domain.py` - Cycle detection test data updated

## Decisions Made
- Updated simulator data directly to new model-ready shape rather than having the adapter transform it (simulator was already bypassing the adapter since it uses model-format not bridge-format)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Added missing SYSTEM_LOCATIONS import to hybrid.py**
- **Found during:** Task 2 (running cross-path tests)
- **Issue:** Wave 2 added code referencing SYSTEM_LOCATIONS but the import was stripped by the formatter due to `from __future__ import annotations`
- **Fix:** Added `from omnifocus_operator.config import SYSTEM_LOCATIONS` import
- **Files modified:** src/omnifocus_operator/repository/hybrid/hybrid.py
- **Committed in:** e412838

**2. [Rule 3 - Blocking] Fixed domain.py cycle detection for new ParentRef shape**
- **Found during:** Task 2 (running server tests)
- **Issue:** `domain.py` accessed `task.parent.id` and `task.parent.type` which no longer exist on the tagged ParentRef wrapper
- **Fix:** Changed to `task.parent.task.id` for cycle walk and extracted parent ID from whichever branch is set for no-op detection
- **Files modified:** src/omnifocus_operator/service/domain.py
- **Committed in:** e412838

**3. [Rule 3 - Blocking] Updated simulator data to new model-ready shape**
- **Found during:** Task 2 (running simulator integration tests)
- **Issue:** Simulator data used old shape (string parent/project, string folder/nextTask, inInbox field) which the adapter skips (no `status` key)
- **Fix:** Rewrote all task entries with tagged parent + project refs, all project entries with enriched folder/nextTask refs, removed inInbox
- **Files modified:** src/omnifocus_operator/simulator/data.py
- **Committed in:** e412838

---

**Total deviations:** 3 auto-fixed (3 blocking)
**Impact on plan:** All auto-fixes necessary to get the test suite green. No scope creep.

## Issues Encountered
- `from __future__ import annotations` caused ruff formatter to strip runtime-used imports (SYSTEM_LOCATIONS) -- required re-adding imports after formatter ran

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All 1598 tests pass across both SQLite and bridge paths
- Cross-path equivalence verified (78 tests)
- Output schema validation passes (32 tests)
- Golden master re-capture required (human-only per GOLD-01) -- existing golden master snapshots use old field shapes

## Self-Check: PASSED

---
*Phase: 42-read-output-restructure*
*Completed: 2026-04-06*
