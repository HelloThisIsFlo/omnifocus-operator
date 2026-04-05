---
phase: 39-foundation-constants-reference-models
plan: 01
subsystem: models
tags: [pydantic, constants, reference-models]

requires: []
provides:
  - "SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATION_INBOX, INBOX_DISPLAY_NAME constants in config.py"
  - "PROJECT_REF_DOC, TASK_REF_DOC, FOLDER_REF_DOC description strings in descriptions.py"
  - "ProjectRef, TaskRef, FolderRef models in models/common.py"
  - "Re-exports from omnifocus_operator.models"
affects: [40-task-output-project-field, 41-write-inbox-resolution, 42-rich-references, 43-filter-inbox, 44-output-cleanup, 45-patchornone-elimination]

tech-stack:
  added: []
  patterns:
    - "Ref model pattern: OmniFocusBaseModel with __doc__ = CONSTANT, id: str, name: str"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/config.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/models/common.py
    - src/omnifocus_operator/models/__init__.py

key-decisions:
  - "Placed new Ref models after TagRef and before ParentRef in common.py for logical grouping"

patterns-established:
  - "System location constants: $-prefixed string IDs for virtual locations ($inbox)"

requirements-completed: [SLOC-01, MODL-01, MODL-02, MODL-03]

duration: 2min
completed: 2026-04-05
---

# Phase 39 Plan 01: Foundation Constants & Reference Models Summary

**System location constants ($inbox) and three new typed Ref models (ProjectRef, TaskRef, FolderRef) following TagRef pattern**

## Performance

- **Duration:** 2 min
- **Started:** 2026-04-05T16:08:26Z
- **Completed:** 2026-04-05T16:10:17Z
- **Tasks:** 2
- **Files modified:** 4

## Accomplishments
- Three system location constants (SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATION_INBOX, INBOX_DISPLAY_NAME) added to config.py
- Three description string constants (PROJECT_REF_DOC, TASK_REF_DOC, FOLDER_REF_DOC) added to descriptions.py
- Three new Ref models (ProjectRef, TaskRef, FolderRef) in models/common.py following TagRef pattern exactly
- All new models wired into models/__init__.py (imports, _ns dict, __all__)

## Task Commits

Each task was committed atomically:

1. **Task 1: Add system location constants and description strings** - `5c9d911` (feat)
2. **Task 2: Create ProjectRef, TaskRef, FolderRef models and wire exports** - `07f6e95` (feat)

## Files Created/Modified
- `src/omnifocus_operator/config.py` - Added SYSTEM_LOCATION_PREFIX, SYSTEM_LOCATION_INBOX, INBOX_DISPLAY_NAME
- `src/omnifocus_operator/agent_messages/descriptions.py` - Added PROJECT_REF_DOC, TASK_REF_DOC, FOLDER_REF_DOC
- `src/omnifocus_operator/models/common.py` - Added ProjectRef, TaskRef, FolderRef classes
- `src/omnifocus_operator/models/__init__.py` - Wired new model re-exports

## Decisions Made
None - followed plan as specified.

## Deviations from Plan
None - plan executed exactly as written.

## Issues Encountered
None.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All constants and reference models are importable and ready for use by phases 40-45
- ParentRef is unchanged -- pure coexistence confirmed
- All 1528 existing tests pass with zero regressions

## Self-Check: PASSED

All 4 modified files exist. Both task commits (5c9d911, 07f6e95) verified in git log.

---
*Phase: 39-foundation-constants-reference-models*
*Completed: 2026-04-05*
