---
phase: 40-resolver-system-location-detection-name-resolution
plan: 01
subsystem: service/resolve
tags: [resolver, cascade, fuzzy, system-locations, name-resolution]
dependency_graph:
  requires: [phase-39-constants]
  provides: [resolve-cascade, resolve-container, resolve-anchor, resolve-tags-substring, lookup-methods, fuzzy-module, name-resolution-errors]
  affects: [service.py, domain.py, all-write-pipelines]
tech_stack:
  added: []
  patterns: [three-step-cascade, entity-type-enum, shared-fuzzy-utility]
key_files:
  created:
    - src/omnifocus_operator/service/fuzzy.py
  modified:
    - src/omnifocus_operator/service/resolve.py
    - src/omnifocus_operator/service/domain.py
    - src/omnifocus_operator/agent_messages/errors.py
    - src/omnifocus_operator/service/service.py
    - tests/test_service_resolve.py
    - tests/test_service.py
    - tests/test_service_domain.py
decisions:
  - System locations only valid when PROJECT in accept list (container context); TASK-only and TAG-only contexts reject $-prefix with reserved error
  - Removed PARENT_NOT_FOUND and AMBIGUOUS_ENTITY error templates (superseded by NAME_NOT_FOUND and AMBIGUOUS_NAME_MATCH)
metrics:
  duration: 540s
  completed: "2026-04-05T18:51:59Z"
  tasks: 2/2
  tests_passed: 1549
  coverage: 98.24%
---

# Phase 40 Plan 01: Resolution Cascade, Fuzzy Module, Lookup Renames Summary

Three-step resolution cascade (_resolve) with $-prefix detection, case-insensitive substring matching, and ID fallback; shared fuzzy module extracted from DomainLogic; four new error templates; lookup_* renames propagated to all callers.

## Task Results

| Task | Name | Commit | Key Changes |
|------|------|--------|-------------|
| 1 | Shared fuzzy module, error templates, _resolve cascade (TDD) | 839ff36, 93e7367 | fuzzy.py created, resolve.py rewritten with _EntityType enum + _resolve cascade, errors.py extended, domain.py delegates to fuzzy module, 48 resolver tests |
| 2 | Full test suite green after resolver rewrite | dcc6b8b | service.py, domain.py, test_service.py, test_service_domain.py updated for renamed methods and new error messages |

## Implementation Details

- **_resolve cascade**: $-prefix -> substring match -> ID fallback -> fuzzy suggestions
- **_EntityType enum**: PROJECT, TASK, TAG -- controls which entities are searched and whether $-prefix is accepted
- **resolve_container**: accepts PROJECT + TASK, supports $inbox
- **resolve_anchor**: accepts TASK only, rejects $-prefix
- **resolve_tags**: pre-fetches tag list once, passes to _resolve for substring matching
- **lookup_task/lookup_project/lookup_tag**: direct ID lookups returning full entity objects (renamed from resolve_*)
- **Shared fuzzy module**: suggest_close_matches + format_suggestions extracted to service/fuzzy.py
- **Error templates**: AMBIGUOUS_NAME_MATCH (id+name pairs), NAME_NOT_FOUND (with fuzzy suggestions), INVALID_SYSTEM_LOCATION, RESERVED_PREFIX

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] System location accepted in anchor context**
- **Found during:** Task 1 GREEN phase
- **Issue:** $inbox was accepted by resolve_anchor because the $-prefix check only rejected TAG-only contexts, not TASK-only
- **Fix:** Changed condition to only accept system locations when PROJECT is in accept list
- **Files modified:** src/omnifocus_operator/service/resolve.py

**2. [Rule 3 - Blocking] Unused error constants failed AST integrity test**
- **Found during:** Task 2
- **Issue:** PARENT_NOT_FOUND and AMBIGUOUS_ENTITY were no longer imported anywhere after the cascade replaced them, causing test_warnings.py AST check to fail
- **Fix:** Removed both constants from errors.py (superseded by NAME_NOT_FOUND and AMBIGUOUS_NAME_MATCH)
- **Files modified:** src/omnifocus_operator/agent_messages/errors.py

**3. [Rule 1 - Bug] Error message assertions in test_service.py**
- **Found during:** Task 2
- **Issue:** Three tests expected old error format ("Parent not found", "Tag not found", "specify by ID") but cascade produces new format
- **Fix:** Updated assertions to match new error templates
- **Files modified:** tests/test_service.py

## Self-Check: PASSED

All files verified present, all acceptance criteria met, all 3 commits found in history.
