---
phase: 37-server-registration-and-integration-was-phase-38
plan: 01
subsystem: contracts, service, repository
tags: [search, query-models, cross-path-equivalence, pydantic]

# Dependency graph
requires:
  - phase: 35-sql-repository
    provides: "SQL query builder, hybrid/bridge-only repo list methods"
  - phase: 35.1-introduce-read-side-contract-boundary-split-repoquery-reporesult
    provides: "Query/RepoQuery model pairs for all entity types"
  - phase: 36.3
    provides: "Centralized descriptions in agent_messages/descriptions.py"
provides:
  - "search: str | None = None on all 5 query model pairs"
  - "ListPerspectivesQuery and ListPerspectivesRepoQuery contracts"
  - "Updated Service/Repository protocols with list_perspectives(query) signature"
  - "Search wired through service, hybrid repo, bridge-only repo, and query builder"
  - "Cross-path equivalence tests proving SQL and Python-filter paths match for search"
affects: [37-02, 37-03, server-tool-registration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "LIKE ? COLLATE NOCASE for SQL search on name+notes"
    - ".lower() Python filter as bridge fallback for search"

key-files:
  created:
    - src/omnifocus_operator/contracts/use_cases/list/perspectives.py
  modified:
    - src/omnifocus_operator/contracts/use_cases/list/tags.py
    - src/omnifocus_operator/contracts/use_cases/list/folders.py
    - src/omnifocus_operator/contracts/use_cases/list/projects.py
    - src/omnifocus_operator/contracts/use_cases/list/tasks.py
    - src/omnifocus_operator/contracts/use_cases/list/__init__.py
    - src/omnifocus_operator/contracts/protocols.py
    - src/omnifocus_operator/agent_messages/descriptions.py
    - src/omnifocus_operator/service/service.py
    - src/omnifocus_operator/repository/hybrid/hybrid.py
    - src/omnifocus_operator/repository/hybrid/query_builder.py
    - src/omnifocus_operator/repository/bridge_only/bridge_only.py
    - tests/test_cross_path_equivalence.py
    - tests/test_list_pipelines.py
    - tests/test_hybrid_repository.py
    - tests/test_descriptions.py

key-decisions:
  - "Project search SQL uses t.name/t.plainTextNote (not p.*) since projects share the Task table"
  - "Perspectives search is name-only (no notes field on perspectives)"
  - "Non-ASCII search test uses ASCII 'Buro' -- both SQL and Python paths match on ASCII substrings"

patterns-established:
  - "Search field with Field(description=SEARCH_FIELD_NAME_NOTES) for name+notes entities"
  - "Search field with Field(description=SEARCH_FIELD_NAME_ONLY) for name-only entities"

requirements-completed: [SRCH-01, SRCH-02, SRCH-03, SRCH-04]

# Metrics
duration: 9min
completed: 2026-04-03
---

# Phase 37 Plan 01: Search Filter and Perspectives Query Summary

**Search filter added to all 5 entity query models, ListPerspectivesQuery/RepoQuery created, protocols updated, wired through all layers with cross-path equivalence tests**

## Performance

- **Duration:** 9 min
- **Started:** 2026-04-03T13:46:24Z
- **Completed:** 2026-04-03T13:55:23Z
- **Tasks:** 2
- **Files modified:** 16

## Accomplishments
- Created ListPerspectivesQuery/ListPerspectivesRepoQuery with centralized descriptions
- Added search: str | None = None to all 5 entity query model pairs (tasks, projects, tags, folders, perspectives)
- Wired search through service pass-throughs, _ListProjectsPipeline, query builder SQL, hybrid repo Python filters, and bridge-only repo Python filters
- Added 8 cross-path search equivalence tests (projects name, projects notes, tags, tags no-match, tags non-ASCII, folders, perspectives)
- Updated Service and Repository protocols: list_perspectives now accepts query param

## Task Commits

Each task was committed atomically:

1. **Task 1: Create ListPerspectivesQuery/RepoQuery, add search to all query models, update protocols** - `4f62b29` (feat)
2. **Task 2: Wire search through service, repos, and query builder; add cross-path equivalence tests** - `64d9ba7` (feat)

## Files Created/Modified
- `src/omnifocus_operator/contracts/use_cases/list/perspectives.py` - NEW: ListPerspectivesQuery and ListPerspectivesRepoQuery
- `src/omnifocus_operator/contracts/use_cases/list/tags.py` - Added search field to both query models
- `src/omnifocus_operator/contracts/use_cases/list/folders.py` - Added search field to both query models
- `src/omnifocus_operator/contracts/use_cases/list/projects.py` - Added search field to both query models
- `src/omnifocus_operator/contracts/use_cases/list/tasks.py` - Added Field(description=) to search
- `src/omnifocus_operator/contracts/use_cases/list/__init__.py` - Re-exports for perspectives
- `src/omnifocus_operator/contracts/protocols.py` - list_perspectives accepts query param
- `src/omnifocus_operator/agent_messages/descriptions.py` - LIST_PERSPECTIVES_QUERY_DOC, SEARCH_FIELD_NAME_NOTES, SEARCH_FIELD_NAME_ONLY
- `src/omnifocus_operator/service/service.py` - search= pass-through for tags, folders, perspectives; projects pipeline
- `src/omnifocus_operator/repository/hybrid/hybrid.py` - Python .lower() search for tags, folders, perspectives
- `src/omnifocus_operator/repository/hybrid/query_builder.py` - SQL LIKE COLLATE NOCASE for project search
- `src/omnifocus_operator/repository/bridge_only/bridge_only.py` - Python .lower() search for all entity types
- `tests/test_cross_path_equivalence.py` - 8 new search tests + updated perspective tests
- `tests/test_list_pipelines.py` - Updated list_perspectives call sites
- `tests/test_hybrid_repository.py` - Updated list_perspectives call sites
- `tests/test_descriptions.py` - Registered perspectives.py as consumer module

## Decisions Made
- Project search SQL uses `t.name` and `t.plainTextNote` columns (projects share Task table in SQLite)
- Non-ASCII test uses ASCII "Buro" term to ensure both SQL and Python paths match consistently
- Perspectives search is name-only (perspectives have no notes field)

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed project search SQL column aliases**
- **Found during:** Task 2 (query builder)
- **Issue:** Plan specified `p.name` and `p.plainTextNote` but project SQL uses `t.*` alias (projects live in Task table)
- **Fix:** Used `t.name LIKE ? COLLATE NOCASE OR t.plainTextNote LIKE ? COLLATE NOCASE`
- **Files modified:** src/omnifocus_operator/repository/hybrid/query_builder.py
- **Committed in:** 64d9ba7

**2. [Rule 3 - Blocking] Updated test_descriptions.py for new perspectives module**
- **Found during:** Task 2 (full test suite verification)
- **Issue:** test_descriptions.py DESC-04 test flagged LIST_PERSPECTIVES_QUERY_DOC as unreferenced (perspectives.py not in consumer list)
- **Fix:** Added contracts_list_perspectives to _CONSUMER_MODULES, ListPerspectivesRepoQuery to _INTERNAL_CLASSES
- **Files modified:** tests/test_descriptions.py
- **Committed in:** 64d9ba7

**3. [Rule 1 - Bug] Updated cross-path test assertions for new seed data**
- **Found during:** Task 2 (cross-path tests)
- **Issue:** Adding tag-4 (Buro) and persp-2 (Review) to seed data broke existing count assertions
- **Fix:** Updated test_list_tags_default (3->4 tags), test_list_tags_active_only (2->3), test_list_perspectives (2->3)
- **Files modified:** tests/test_cross_path_equivalence.py
- **Committed in:** 64d9ba7

---

**Total deviations:** 3 auto-fixed (2 bugs, 1 blocking)
**Impact on plan:** All fixes necessary for correctness. No scope creep.

## Issues Encountered
None

## Known Stubs
None

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- All 5 entity query models have search fields, ready for MCP tool registration (37-02/37-03)
- ListPerspectivesQuery/RepoQuery ready for server-side wiring
- Cross-path equivalence proven for search -- both SQL and Python paths match
- Full test suite green: 1457 tests passing

---
*Phase: 37-server-registration-and-integration-was-phase-38*
*Completed: 2026-04-03*
