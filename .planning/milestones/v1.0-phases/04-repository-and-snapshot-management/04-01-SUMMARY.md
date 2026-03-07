---
phase: 04-repository-and-snapshot-management
plan: 01
subsystem: repository
tags: [asyncio, caching, protocol, mtime, pydantic]

# Dependency graph
requires:
  - phase: 03-bridge-protocol-and-inmemorybridge
    provides: Bridge protocol, InMemoryBridge test double, BridgeError hierarchy
  - phase: 02-data-models
    provides: DatabaseSnapshot model with model_validate() parsing
provides:
  - OmniFocusRepository caching layer with mtime-gated refresh
  - MtimeSource protocol for pluggable freshness detection
  - FileMtimeSource production implementation (st_mtime_ns via asyncio.to_thread)
  - FakeMtimeSource test double pattern (in test file)
affects: [05-service-layer, 07-simulator-bridge]

# Tech tracking
tech-stack:
  added: []
  patterns: [mtime-gated cache refresh, asyncio.Lock for concurrency, constructor injection of Protocol types]

key-files:
  created:
    - src/omnifocus_operator/repository/__init__.py
    - src/omnifocus_operator/repository/_mtime.py
    - src/omnifocus_operator/repository/_repository.py
    - tests/test_repository.py
  modified: []

key-decisions:
  - "Fail-fast error propagation: bridge/validation/mtime errors propagate raw, no stale fallback"
  - "Entire get_snapshot() flow under asyncio.Lock: mtime check + conditional refresh are atomic"
  - "DatabaseSnapshot kept as runtime import (used by model_validate), Bridge/MtimeSource in TYPE_CHECKING"

patterns-established:
  - "MtimeSource protocol: pluggable freshness detection via async get_mtime_ns() -> int"
  - "FakeMtimeSource: test double with set_mtime_ns() for deterministic cache invalidation in tests"
  - "Repository caching: single lock, mtime comparison, conditional refresh via bridge"

requirements-completed: [SNAP-01, SNAP-02, SNAP-03, SNAP-04, SNAP-05, SNAP-06]

# Metrics
duration: 3min
completed: 2026-03-02
---

# Phase 4 Plan 1: OmniFocusRepository with MtimeSource Summary

**Caching repository with mtime-gated refresh, asyncio.Lock concurrency control, and fail-fast error propagation via MtimeSource protocol**

## Performance

- **Duration:** 3 min
- **Started:** 2026-03-02T01:38:15Z
- **Completed:** 2026-03-02T01:41:49Z
- **Tasks:** 1 (TDD: RED + GREEN + REFACTOR)
- **Files created:** 4

## Accomplishments
- OmniFocusRepository with get_snapshot() and initialize() for cache pre-warming
- MtimeSource protocol + FileMtimeSource production implementation using asyncio.to_thread(os.stat)
- 21 tests covering all 6 SNAP requirements, error propagation, and concurrency
- 100% coverage on repository module, 99.13% total project coverage

## Task Commits

Each task was committed atomically:

1. **TDD RED: failing tests** - `03afb4b` (test)
2. **TDD GREEN+REFACTOR: implementation + lint fixes** - `2bc1dfe` (feat)

_TDD plan: tests written first against stubs, then implementation + refactor in single commit._

## Files Created/Modified
- `src/omnifocus_operator/repository/__init__.py` - Public API re-exports (OmniFocusRepository, MtimeSource, FileMtimeSource)
- `src/omnifocus_operator/repository/_mtime.py` - MtimeSource protocol + FileMtimeSource (os.stat via asyncio.to_thread)
- `src/omnifocus_operator/repository/_repository.py` - OmniFocusRepository with cache, lock, mtime-gated refresh
- `tests/test_repository.py` - 21 tests: SNAP-01..06, error propagation, concurrency, FileMtimeSource integration

## Decisions Made
- Fail-fast error propagation: all errors (BridgeError, ValidationError, OSError) propagate raw to caller
- Entire get_snapshot() under asyncio.Lock so mtime check + conditional refresh are atomic
- DatabaseSnapshot is a runtime import (model_validate), Bridge/MtimeSource in TYPE_CHECKING block
- FakeMtimeSource lives in test file (not production code), matching plan specification

## Deviations from Plan

None - plan executed exactly as written.

## Issues Encountered
- conftest import required relative syntax (`from .conftest import ...`) matching project convention
- Ruff TC001 required Bridge and MtimeSource in TYPE_CHECKING block; DatabaseSnapshot stays runtime (used by model_validate)

## User Setup Required

None - no external service configuration required.

## Next Phase Readiness
- Repository module complete and fully tested
- Ready for Phase 5 (service layer) which will inject OmniFocusRepository
- MtimeSource protocol enables future SimulatorBridge integration (Phase 7)

## Self-Check: PASSED

- All 4 source/test files exist
- All 2 task commits verified (03afb4b, 2bc1dfe)

---
*Phase: 04-repository-and-snapshot-management*
*Completed: 2026-03-02*
