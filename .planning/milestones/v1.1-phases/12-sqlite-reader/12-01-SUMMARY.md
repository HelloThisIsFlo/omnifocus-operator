---
phase: 12-sqlite-reader
plan: 01
subsystem: database
tags: [sqlite, pydantic, repository, read-only, cf-epoch, plistlib]

requires:
  - phase: 11-datasource-protocol
    provides: Repository protocol with get_all() -> AllEntities
provides:
  - HybridRepository reading all 5 entity types from SQLite cache
  - Row-to-model mapping with two-axis status (urgency + availability)
  - Dual timestamp parsing (CF epoch + ISO 8601)
  - XML note extraction and binary plist perspective parsing
  - Comprehensive test suite with in-memory SQLite fixtures
affects: [12-02-freshness, 13-fallback-integration]

tech-stack:
  added: []
  patterns: [fresh-connection-per-read, asyncio-to-thread-wrapping, cf-epoch-timestamp-parsing]

key-files:
  created:
    - src/omnifocus_operator/repository/hybrid.py
    - tests/test_hybrid_repository.py
  modified:
    - src/omnifocus_operator/repository/__init__.py

key-decisions:
  - "Numeric string detection in _parse_timestamp handles SQLite TEXT column affinity returning floats as strings"
  - "Tag name lookup built before task mapping to populate TagRef objects via join table"
  - "Projects excluded from tasks query via LEFT JOIN + WHERE pi.task IS NULL"

patterns-established:
  - "SQLite row mapping: private module-level functions (_map_*_row) returning dicts for Pydantic model_validate"
  - "Status mapping: lookup tables and priority-ordered conditionals for two-axis derivation"
  - "Test fixture: create_test_db() helper building file-based SQLite with OmniFocus schema"

requirements-completed: [SQLITE-01, SQLITE-02, SQLITE-03, SQLITE-04]

duration: 5min
completed: 2026-03-07
---

# Phase 12 Plan 01: SQLite Reader Summary

**HybridRepository reading 5 entity types from SQLite with two-axis status mapping, dual timestamp parsing, and 41 test cases**

## Performance

- **Duration:** 5 min
- **Started:** 2026-03-07T18:06:42Z
- **Completed:** 2026-03-07T18:12:00Z
- **Tasks:** 2 (1 TDD + 1 wiring)
- **Files modified:** 3

## Accomplishments
- HybridRepository satisfies Repository protocol, reads all 5 entity types from SQLite
- Row-to-model mapping handles all field types: strings, booleans, timestamps (CF epoch + ISO 8601), XML notes, plist blobs, join tables
- Two-axis status (urgency + availability) correctly derived from SQLite columns for tasks, projects, tags, folders
- 41 tests passing with in-memory SQLite fixtures, full suite 277 tests green

## Task Commits

Each task was committed atomically:

1. **Task 1 (RED): Failing tests** - `2109f0b` (test)
2. **Task 1 (GREEN): HybridRepository implementation** - `52adc3c` (feat)
3. **Task 2: Wire into package exports** - `8c99839` (feat)

## Files Created/Modified
- `src/omnifocus_operator/repository/hybrid.py` - HybridRepository with full SQLite reader, row mapping, status derivation
- `tests/test_hybrid_repository.py` - 41 test cases covering all entity types, status mapping, timestamps, notes, perspectives
- `src/omnifocus_operator/repository/__init__.py` - Added HybridRepository export

## Decisions Made
- Numeric string detection added to `_parse_timestamp` -- SQLite TEXT columns return float values as strings, not native floats
- Tag name lookup dict built upfront before task row mapping to efficiently populate TagRef objects via TaskToTag join
- Projects excluded from task query via LEFT JOIN ProjectInfo + WHERE NULL filter

## Deviations from Plan

### Auto-fixed Issues

**1. [Rule 1 - Bug] Fixed CF epoch float parsed as string from TEXT columns**
- **Found during:** Task 1 GREEN phase
- **Issue:** SQLite TEXT column affinity returns stored floats as strings; `isinstance(value, float)` check missed them
- **Fix:** Added `try: float(value)` fallback in `_parse_timestamp` for numeric strings
- **Files modified:** `src/omnifocus_operator/repository/hybrid.py`
- **Verification:** `test_task_dates_cf_epoch` passes
- **Committed in:** `52adc3c` (Task 1 GREEN commit)

---

**Total deviations:** 1 auto-fixed (1 bug)
**Impact on plan:** Essential fix for correctness. No scope creep.

## Issues Encountered
None beyond the auto-fixed deviation above.

## User Setup Required
None - no external service configuration required.

## Next Phase Readiness
- HybridRepository complete and exported, ready for Plan 02 (WAL freshness detection)
- No blockers for Phase 13 wiring (HybridRepository importable from repository package)

---
*Phase: 12-sqlite-reader*
*Completed: 2026-03-07*
