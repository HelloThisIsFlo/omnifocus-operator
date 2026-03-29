---
phase: 34-contracts-and-query-foundation
plan: 01
subsystem: contracts
tags: [pydantic, generics, protocols, query-models, list-result]

requires:
  - phase: v1.2.3 (prior milestone)
    provides: CommandModel base, OmniFocusBaseModel with camelCase, Service/Repository protocols, enums

provides:
  - StrictModel/QueryModel hierarchy (shared extra=forbid base)
  - ListTasksQuery, ListProjectsQuery, ListTagsQuery, ListFoldersQuery validated query models
  - ListResult[T] generic response container with camelCase serialization
  - Service and Repository protocol extensions with 5 list method signatures each

affects: [34-02, 35-sql-query-engine, 36-bridge-fallback, 37-service-list-orchestration, 38-mcp-list-tools]

tech-stack:
  added: []
  patterns: [StrictModel as shared base for CommandModel/QueryModel, QueryModel for read-side contracts, Query suffix in contracts/ naming convention]

key-files:
  created:
    - src/omnifocus_operator/contracts/use_cases/list_entities.py
    - tests/test_list_contracts.py
  modified:
    - src/omnifocus_operator/contracts/base.py
    - src/omnifocus_operator/contracts/__init__.py
    - src/omnifocus_operator/contracts/protocols.py
    - tests/test_output_schema.py

key-decisions:
  - "StrictModel extracted from CommandModel as shared base; QueryModel is sibling, not child of CommandModel"
  - "Query suffix added to CONTRACT_SUFFIXES in naming convention test (was WRITE_SUFFIXES)"
  - "ListResult inherits OmniFocusBaseModel (not StrictModel) since it is an output model, not an agent-input contract"

patterns-established:
  - "QueryModel: read-side contract base for all filter/pagination models in contracts/"
  - "Query suffix: recognized naming convention for read-side contracts in contracts/ package"

requirements-completed: [INFRA-04]

duration: 4min
completed: 2026-03-29
---

# Phase 34 Plan 01: List Contracts Summary

**StrictModel/QueryModel hierarchy, 4 validated query models with typed availability defaults, ListResult[T] generic container, and 5 list method signatures on Service/Repository protocols**

## Performance

- **Duration:** 4 min
- **Started:** 2026-03-29T22:39:11Z
- **Completed:** 2026-03-29T22:43:24Z
- **Tasks:** 3
- **Files modified:** 6

## Accomplishments

- Refactored contracts/base.py to introduce StrictModel as shared base, CommandModel and QueryModel as siblings
- Created 4 query models (ListTasksQuery with 9 fields, ListProjectsQuery with 6 fields, ListTagsQuery, ListFoldersQuery) with typed availability enum defaults
- Created ListResult[T] generic container with camelCase serialization (hasMore, items, total)
- Extended Service and Repository protocols with 5 list method signatures each (list_tasks, list_projects, list_tags, list_folders, list_perspectives)
- 29 unit tests covering hierarchy, serialization, defaults, rejection, acceptance, and camelCase aliases

## Task Commits

Each task was committed atomically:

1. **Task 1: Create StrictModel, QueryModel, query models, and ListResult[T]** - `ee9a558` (feat)
2. **Task 2: Extend Repository and Service protocols with list method signatures** - `09d1af7` (feat)
3. **Task 3: Unit tests for query contracts and ListResult serialization** - `c71dac4` (test)

## Files Created/Modified

- `src/omnifocus_operator/contracts/base.py` - StrictModel extracted, QueryModel added as CommandModel sibling
- `src/omnifocus_operator/contracts/use_cases/list_entities.py` - 4 query models + ListResult[T]
- `src/omnifocus_operator/contracts/__init__.py` - Re-exports and model_rebuild() for all new models
- `src/omnifocus_operator/contracts/protocols.py` - 5 list methods on Service and Repository protocols
- `tests/test_list_contracts.py` - 29 unit tests for query contracts
- `tests/test_output_schema.py` - Updated naming convention: CONTRACT_SUFFIXES with Query suffix, StrictModel/QueryModel exempt

## Decisions Made

- StrictModel extracted as shared base for both CommandModel and QueryModel (extra=forbid in one place)
- QueryModel is a sibling to CommandModel, not a child -- read-side vs write-side taxonomy
- ListResult inherits OmniFocusBaseModel (not StrictModel) because it is an output container, not an agent-input contract with extra=forbid
- WRITE_SUFFIXES renamed to CONTRACT_SUFFIXES and expanded with "Query" suffix for read-side contracts
- StrictModel and QueryModel added to CONTRACTS_EXEMPT in naming convention test (base classes, not use-case models)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 3 - Blocking] Updated naming convention test to recognize new model types**
- **Found during:** Task 1 (verification step)
- **Issue:** test_output_schema.py::TestNamingConvention rejected new Query models and base classes (only recognized write-side suffixes)
- **Fix:** Renamed WRITE_SUFFIXES to CONTRACT_SUFFIXES, added "Query" suffix, added StrictModel/QueryModel to CONTRACTS_EXEMPT
- **Files modified:** tests/test_output_schema.py
- **Verification:** All 36 output schema tests pass
- **Committed in:** ee9a558 (Task 1 commit)

---

**Total deviations:** 1 auto-fixed (1 blocking)
**Impact on plan:** Necessary to make existing tests recognize the new read-side contract taxonomy. No scope creep.

## Issues Encountered

None.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness

- All typed contracts ready for downstream phases (35-38) to implement
- Service and Repository protocols declare list methods -- implementations will follow in phases 35-37
- mypy will flag OperatorService, HybridRepository, BridgeRepository as incomplete (intentional -- implementations in later phases)

## Self-Check: PASSED

All 6 files verified present on disk. All 3 task commits verified in git log. No stubs found.

---
*Phase: 34-contracts-and-query-foundation*
*Completed: 2026-03-29*
