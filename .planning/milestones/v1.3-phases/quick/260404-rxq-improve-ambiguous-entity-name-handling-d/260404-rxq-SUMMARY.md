---
phase: 260404-rxq
plan: 01
subsystem: service
tags: [resolver, warnings, errors, disambiguation, performance]

requires:
  - phase: 37
    provides: list_tags, list_projects, list_folders repo methods
provides:
  - AMBIGUOUS_ENTITY generic error constant with entity_type param
  - FILTER_MULTI_MATCH warning for read-side multi-match disambiguation
  - _match_by_name generalized resolver method ready for project/folder writes
  - Targeted list calls replacing get_all() in resolver and pipelines

affects: [service, agent-messages, future-write-side-resolution]

tech-stack:
  added: []
  patterns:
    - "Per-value multi-match warning loop in _resolve_tags (not aggregate)"
    - "Targeted list calls with all availability values for resolver use"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/agent_messages/warnings.py
    - src/omnifocus_operator/service/resolve.py
    - src/omnifocus_operator/service/service.py
    - tests/test_service_resolve.py
    - tests/test_service.py
    - tests/test_list_pipelines.py

key-decisions:
  - "AMBIGUOUS_ENTITY replaces AMBIGUOUS_TAG -- generic entity_type param for future project/folder writes"
  - "Multi-match warning uses per-value loop in _resolve_tags, not aggregate check"
  - "All availability values passed to list calls for resolution (includes dropped entities)"

patterns-established:
  - "Multi-match warning pattern: check len(resolved) > 1 after resolve_filter, build name_map from entity list"

requirements-completed: [TODO-20, TODO-21]

duration: 6min
completed: 2026-04-04
---

# Quick Task 260404-rxq: Improve Ambiguous Entity Name Handling Summary

**Generic AMBIGUOUS_ENTITY error with "specify by ID" guidance, FILTER_MULTI_MATCH warnings for read-side filters, and get_all() replaced with targeted list calls in resolver and pipelines**

## Performance

- **Duration:** 6 min
- **Started:** 2026-04-04T19:53:14Z
- **Completed:** 2026-04-04T19:58:46Z
- **Tasks:** 2
- **Files modified:** 7

## Accomplishments
- Write-side error generalized: AMBIGUOUS_TAG replaced with AMBIGUOUS_ENTITY, parameterized by entity_type with "specify by ID" guidance
- Read-side multi-match warnings: project, tag, and folder filters emit warnings when multiple entities match, including names and IDs
- Performance optimization: get_all() replaced with targeted list_tags/list_projects/list_folders calls in resolver and both pipelines
- _match_by_name generalized for future project/folder write-side resolution

## Task Commits

Each task was committed atomically:

1. **Task 1: Generalize write-side error and replace get_all() in resolver**
   - `36ad4a8` (test: failing tests for ambiguous entity error guidance)
   - `fd5e01f` (feat: generalize write-side error and replace get_all() in resolver)

2. **Task 2: Add read-side multi-match warnings and replace get_all() in pipelines**
   - `18cd2cf` (test: failing tests for read-side multi-match warnings)
   - `deb03ba` (feat: add read-side multi-match warnings and replace get_all() in pipelines)

## Files Created/Modified
- `src/omnifocus_operator/agent_messages/errors.py` - AMBIGUOUS_TAG -> AMBIGUOUS_ENTITY with entity_type param
- `src/omnifocus_operator/agent_messages/warnings.py` - Added FILTER_MULTI_MATCH constant
- `src/omnifocus_operator/service/resolve.py` - _match_tag -> _match_by_name, resolve_tags uses list_tags
- `src/omnifocus_operator/service/service.py` - Pipelines use targeted list calls, multi-match warning logic
- `tests/test_service_resolve.py` - Updated ambiguous test, added _match_by_name generic test
- `tests/test_service.py` - Updated test_tag_ambiguous with "specify by ID" assertion
- `tests/test_list_pipelines.py` - Added 4 multi-match warning tests

## Decisions Made
- AMBIGUOUS_ENTITY replaces AMBIGUOUS_TAG with entity_type param for future project/folder write-side resolution
- Multi-match warnings use per-value loop in _resolve_tags (Pitfall 3 from research) instead of aggregate check
- All availability values (including DROPPED) passed to list calls for resolution completeness

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed test assertion using .lower() on mixed-case string**
- **Found during:** Task 2 (multi-match warning tests)
- **Issue:** Test checked `"filter by ID" in w.lower()` -- the literal has uppercase "ID" but the whole string was lowered
- **Fix:** Removed `.lower()` call, checking for exact case `"filter by ID"`
- **Files modified:** tests/test_list_pipelines.py
- **Verification:** All 4 multi-match tests pass
- **Committed in:** deb03ba (part of Task 2 commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Trivial test assertion fix. No scope creep.

## Issues Encountered
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- _match_by_name is ready for future project/folder write-side resolution
- Multi-match warning pattern established and reusable

## Self-Check: PASSED

---
*Quick Task: 260404-rxq*
*Completed: 2026-04-04*
