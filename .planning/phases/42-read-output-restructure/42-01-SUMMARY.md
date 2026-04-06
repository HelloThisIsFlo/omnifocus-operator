---
phase: 42-read-output-restructure
plan: 01
subsystem: models
tags: [pydantic, models, descriptions, parentref, references]

# Dependency graph
requires:
  - phase: 39-foundation-constants-reference-models
    provides: "ProjectRef, TaskRef, FolderRef, TagRef in models/common.py"
  - phase: 41-write-pipeline-inbox-in-add-edit
    provides: "$inbox system location, PatchOrNone elimination"
provides:
  - "Tagged ParentRef wrapper with exactly-one validator (project | task)"
  - "Task.project: ProjectRef (containing project at any depth)"
  - "Task.parent: ParentRef (required, never null)"
  - "Task.in_inbox removed from model"
  - "Project.folder: FolderRef | None, Project.next_task: TaskRef | None"
  - "Tag.parent: TagRef | None, Folder.parent: FolderRef | None"
  - "All 7 tool description constants updated with {id, name} notation"
  - "New field-level description constants (D-19 through D-26)"
affects: [42-02 (mapper rewrites), 42-03 (adapter rewrites), 42-04 (filter updates), 42-05 (test updates)]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "Tagged wrapper pattern for ParentRef (same as MoveAction exactly-one validator)"

key-files:
  created: []
  modified:
    - "src/omnifocus_operator/agent_messages/descriptions.py"
    - "src/omnifocus_operator/models/common.py"
    - "src/omnifocus_operator/models/task.py"
    - "src/omnifocus_operator/models/project.py"
    - "src/omnifocus_operator/models/tag.py"
    - "src/omnifocus_operator/models/folder.py"

key-decisions:
  - "Reused ParentRef name for new tagged wrapper -- old class deleted, new one in same file"
  - "models/__init__.py required zero changes -- existing wiring handled the new ParentRef transparently"

patterns-established:
  - "Tagged wrapper with exactly-one model_validator: ParentRef follows MoveAction pattern"

requirements-completed: [MODL-04, MODL-05, MODL-06, MODL-07, MODL-08, DESC-01, DESC-02]

# Metrics
duration: 4min
completed: 2026-04-06
---

# Phase 42 Plan 01: Models & Descriptions Summary

**Tagged ParentRef wrapper (project | task) with exactly-one validator, enriched Ref types on all entity cross-references, and 7 tool descriptions rewritten with {id, name} notation**

## Performance

- **Duration:** 4 min
- **Started:** 2026-04-06T19:26:10Z
- **Completed:** 2026-04-06T19:30:08Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments
- Replaced old `ParentRef(type, id, name)` with tagged wrapper `ParentRef(project: ProjectRef | None, task: TaskRef | None)` using exactly-one model_validator
- Updated all entity models: Task gains required `parent` and `project` fields (no `in_inbox`), Project/Tag/Folder use enriched Ref types
- Rewrote all 7 tool description constants with new format: `{id, name}` notation, no `camelCase` references
- Added 7 new field-level description constants (D-19 through D-26)

## Task Commits

Each task was committed atomically:

1. **Task 1: Rewrite descriptions -- field-level and tool-level constants** - `cb4b46e` (feat)
2. **Task 2: Rewrite models -- ParentRef, Task, Project, Tag, Folder** - `60eba9c` (feat)
3. **Task 3: Update models/__init__.py wiring** - No commit needed (verified existing wiring is correct, zero changes required)

## Files Created/Modified
- `src/omnifocus_operator/agent_messages/descriptions.py` - Updated PARENT_REF_DOC, NEXT_TASK, FOLDER_PARENT_DESC; added PROJECT_FOLDER_DESC, TAG_PARENT_DESC, TASK_PROJECT_DESC, PARENT_REF_PROJECT_FIELD, PARENT_REF_TASK_FIELD; replaced all 7 tool description constants
- `src/omnifocus_operator/models/common.py` - Deleted old ParentRef(type, id, name), created new tagged wrapper with exactly-one validator, added model_validator and description imports
- `src/omnifocus_operator/models/task.py` - Removed in_inbox, changed parent to required ParentRef, added required project: ProjectRef
- `src/omnifocus_operator/models/project.py` - Changed next_task to TaskRef | None, folder to FolderRef | None
- `src/omnifocus_operator/models/tag.py` - Changed parent to TagRef | None
- `src/omnifocus_operator/models/folder.py` - Changed parent to FolderRef | None

## Decisions Made
- Reused `ParentRef` name for the new tagged wrapper model -- seamless swap, no consumer import changes needed
- `models/__init__.py` required zero changes since the name `ParentRef` was reused and all referenced types were already in the `_ns` namespace dict

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered

- Formatter (ruff) auto-removed `model_validator` and description constant imports from `common.py` because `from __future__ import annotations` makes type annotations lazy. However, `Field(description=...)` arguments and `@model_validator` decorator are evaluated at class definition time. Fixed by ensuring the edit included the actual usage so the formatter recognized them as used.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- All entity models reflect new field types and are importable
- JSON schemas are correct (Task has required parent/project, no inInbox)
- Full test suite will NOT pass yet -- mappers (Plan 02) and adapters (Plan 03) still produce old shapes
- Golden master re-capture required after mapper/adapter rewrites (human-only per GOLD-01)

---
*Phase: 42-read-output-restructure*
*Completed: 2026-04-06*
