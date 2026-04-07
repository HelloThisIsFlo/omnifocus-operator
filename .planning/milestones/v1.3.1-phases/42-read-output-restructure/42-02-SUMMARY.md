---
phase: 42-read-output-restructure
plan: 02
subsystem: database
tags: [sqlite, mapper, enriched-refs, hybrid-repository]

requires:
  - phase: 42-01
    provides: "New model types (ParentRef, ProjectRef, TaskRef, FolderRef, TagRef) with {id, name} shape"
provides:
  - "All HybridRepository mapper functions produce enriched output matching new model shapes"
  - "_build_folder_name_lookup utility for folder name resolution"
  - "Tagged parent dict and project field on task output"
  - "{id, name} refs on project (folder, next_task), tag (parent), folder (parent)"
affects: [42-03, 42-04, 42-05]

tech-stack:
  added: []
  patterns:
    - "Enriched mapper pattern: lookup dicts passed to mapper functions for name resolution"
    - "Targeted single-entity lookups: single-entity reads query only needed names instead of full table scans"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/repository/hybrid/hybrid.py

key-decisions:
  - "Renamed _build_parent_ref to _build_parent_and_project for clarity (returns tuple)"
  - "Targeted queries in single-entity reads (e.g., _read_project queries only the specific folder/next_task names needed)"

patterns-established:
  - "Enriched mapper pattern: all mapper functions accept lookup dicts and produce {id, name} references"

requirements-completed: [READ-01, READ-02, READ-03, READ-04, READ-05, READ-06]

duration: 3min
completed: 2026-04-06
---

# Phase 42 Plan 02: Hybrid Mapper Enrichment Summary

**Rewrote all SQLite mapper functions to produce enriched {id, name} references: tagged parent + project on tasks, folder/next_task refs on projects, parent refs on tags/folders**

## Performance

- **Duration:** 3 min
- **Started:** 2026-04-06T19:31:58Z
- **Completed:** 2026-04-06T19:34:51Z
- **Tasks:** 2
- **Files modified:** 1

## Accomplishments
- Replaced `_build_parent_ref` with `_build_parent_and_project` producing tagged parent dict and project ref (inbox tasks get `$inbox` refs)
- Added `_build_folder_name_lookup` utility for folder name resolution
- All 4 mapper functions (`_map_task_row`, `_map_project_row`, `_map_tag_row`, `_map_folder_row`) now produce enriched output
- All 7 call sites updated: `_read_all`, `_read_project`, `_read_tag`, `_list_tasks_sync`, `_list_projects_sync`, `_list_tags_sync`, `_list_folders_sync`

## Task Commits

Each task was committed atomically:

1. **Task 1: Add _build_folder_name_lookup and rewrite _build_parent_ref** - `427e3c6` (feat)
2. **Task 2: Update all call sites** - `4173842` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/hybrid/hybrid.py` - All mapper functions enriched, new lookup builder, all call sites updated

## Decisions Made
- Renamed `_build_parent_ref` to `_build_parent_and_project` for clarity (now returns a tuple of parent + project dicts)
- Used targeted single-row queries in `_read_project` and `_read_tag` instead of full table scans (matches existing pattern in `_read_task`)

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HybridRepository produces correctly shaped dicts for all entity types
- Ready for Plan 03 (InMemoryBridge adapter) and Plan 04 (test updates) to align bridge path and tests with new shapes
- Golden master re-capture will be needed after all plans complete (GOLD-01)

---
*Phase: 42-read-output-restructure*
*Completed: 2026-04-06*

## Self-Check: PASSED
