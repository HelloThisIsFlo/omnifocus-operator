---
phase: 11-datasource-protocol
plan: 03
subsystem: api
tags: [pydantic, protocol, naming, refactor]

# Dependency graph
requires:
  - phase: 11-01
    provides: Repository protocol with BridgeRepository and InMemoryRepository
  - phase: 11-02
    provides: Consumer migration to Repository protocol
provides:
  - AllEntities model class (renamed from DatabaseSnapshot)
  - get_all() protocol method (renamed from get_snapshot())
  - Clean naming convention for protocol boundary
affects: [12-sqlite-reader, 13-fallback-integration]

# Tech tracking
tech-stack:
  added: []
  patterns:
    - "get_*() for structured multi-type containers, list_*() for flat filtered collections"

key-files:
  created: []
  modified:
    - src/omnifocus_operator/models/snapshot.py
    - src/omnifocus_operator/models/__init__.py
    - src/omnifocus_operator/repository/protocol.py
    - src/omnifocus_operator/repository/bridge.py
    - src/omnifocus_operator/repository/in_memory.py
    - src/omnifocus_operator/service.py
    - src/omnifocus_operator/server.py
    - tests/conftest.py
    - tests/test_models.py
    - tests/test_repository.py
    - tests/test_service.py
    - uat/README.md
    - uat/test_read_only.py
    - uat/test_model_overhaul.py
    - docs/architecture.md

key-decisions:
  - "Tasks 1+2 committed together to keep mypy green (DatabaseSnapshot removal breaks all consumers)"
  - "Renamed BridgeRepository internal _snapshot field to _cached for semantic clarity"
  - "Kept make_snapshot/make_snapshot_dict helper names in conftest (they build AllEntities instances)"

patterns-established:
  - "get_*() = heterogeneous structured return; list_*() = homogeneous filtered collection"
  - "AllEntities as protocol-level return type (no snapshot/cache semantics)"

requirements-completed: [ARCH-01, ARCH-02, ARCH-03]

# Metrics
duration: 3min
completed: 2026-03-07
---

# Phase 11 Plan 03: Naming Convention Summary

**Renamed DatabaseSnapshot->AllEntities and get_snapshot()->get_all() across entire codebase with zero test breakage**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-07T17:24:40Z
- **Completed:** 2026-03-07T17:28:05Z
- **Tasks:** 2
- **Files modified:** 15

## Accomplishments
- Renamed DatabaseSnapshot class to AllEntities (removes snapshot metaphor from protocol boundary)
- Renamed get_snapshot() to get_all() on Repository protocol and all implementations
- Zero leftover references to old names in src/, tests/, docs/
- All 236 tests pass with 98.4% coverage

## Task Commits

Tasks 1 and 2 committed together (mypy requires all references updated atomically):

1. **Tasks 1+2: Rename model class and update all references** - `b32b1af` (feat)

## Files Created/Modified
- `src/omnifocus_operator/models/snapshot.py` - AllEntities class (was DatabaseSnapshot)
- `src/omnifocus_operator/models/__init__.py` - Updated import, model_rebuild, __all__
- `src/omnifocus_operator/repository/protocol.py` - get_all() method (was get_snapshot())
- `src/omnifocus_operator/repository/bridge.py` - get_all(), _cached field, AllEntities refs
- `src/omnifocus_operator/repository/in_memory.py` - get_all(), AllEntities refs
- `src/omnifocus_operator/service.py` - get_all() call, AllEntities return type
- `src/omnifocus_operator/server.py` - AllEntities runtime import for FastMCP
- `tests/conftest.py` - AllEntities import, updated factory docstrings
- `tests/test_models.py` - TestAllEntities class, AllEntities refs
- `tests/test_repository.py` - get_all() calls throughout
- `tests/test_service.py` - get_all() mock references
- `uat/README.md` - AllEntities in documentation
- `uat/test_read_only.py` - AllEntities import and validation
- `uat/test_model_overhaul.py` - AllEntities import and validation
- `docs/architecture.md` - Updated naming reference

## Decisions Made
- Tasks 1+2 committed together because mypy checks all files and renaming the class without updating consumers fails type checking
- Renamed internal `_snapshot` field to `_cached` in BridgeRepository for semantic clarity
- Kept `make_snapshot`/`make_snapshot_dict` helper names in conftest -- they're test utilities and "snapshot" is fine as a test concept

## Deviations from Plan

None - plan executed exactly as written.

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Phase 11 (DataSource Protocol) fully complete
- Repository protocol established with clean naming convention
- Ready for Phase 12 (SQLite Reader) which will add SQLiteRepository implementing get_all()

---
*Phase: 11-datasource-protocol*
*Completed: 2026-03-07*
