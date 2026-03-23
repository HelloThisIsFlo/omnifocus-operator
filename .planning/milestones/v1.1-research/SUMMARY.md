# Project Research Summary

**Project:** OmniFocus Operator v1.1
**Domain:** SQLite cache reading + two-axis status model for existing Python MCP server
**Researched:** 2026-03-07
**Confidence:** HIGH

## Executive Summary

v1.1 replaces the OmniJS bridge as the primary read path with direct SQLite cache reading, cutting snapshot latency from 2-5s to ~46ms and eliminating the requirement for OmniFocus to be running. Simultaneously, the single-winner status enum (where "overdue" masks "blocked") is replaced with a two-axis model: `Urgency` (overdue/due_soon/none) and `Availability` (available/blocked/completed/dropped). Zero new runtime dependencies -- Python 3.12 stdlib `sqlite3` covers everything.

The recommended approach is a strict bottom-up build: Pydantic models first (everything imports them), then the DataSource protocol abstraction, then SQLite reader, then bridge fallback wrapper, then server wiring. The model migration is the riskiest phase -- 177+ tests break simultaneously if done as a big bang. Research strongly recommends incremental migration: add new fields alongside old, migrate consumers, then remove old fields.

Key risks: (1) SQLite connection mode must be `mode=ro` from day one or risk corrupting OmniFocus data; (2) reusing SQLite connections across WAL changes serves stale data due to snapshot isolation; (3) big-bang model migration creates an undebuggable wall of test failures. All three have clear prevention strategies documented in PITFALLS.md.

## Key Findings

### Recommended Stack

Zero new dependencies. The existing single-dep architecture (`mcp>=1.26.0`) is preserved.

**Core technologies:**
- `sqlite3` (stdlib): Read-only access to OmniFocus SQLite cache -- `mode=ro` URI connections, WAL-aware, 46ms reads
- `os.stat()` (stdlib): WAL file mtime polling for freshness detection -- nanosecond precision on APFS
- `pathlib.Path` (stdlib): Database path resolution -- handles `~/Library/Group Containers/...` with spaces
- `enum.StrEnum` (existing): New `Urgency` and `Availability` enums -- same pattern as v1.0

**Explicitly rejected:** aiosqlite (no benefit for stdio), SQLAlchemy (overkill for read-only), watchdog (overkill for mtime polling), apsw (unnecessary for simple reads)

### Expected Features

**Must have (table stakes):**
- SQLite cache reader with 46ms snapshots, no OmniFocus process required
- Two-axis status enums (`Urgency` + `Availability`) fixing the single-winner masking bug
- Pydantic model overhaul (6 fields removed, 2 enums replaced, hierarchy restructured)
- WAL-based read-after-write freshness detection
- Error-serving when SQLite unavailable (existing pattern)
- OmniJS bridge fallback via `OMNIFOCUS_BRIDGE=omnijs` env var
- Status mapping in fallback mode with documented limitations (`blocked` never returned)

**Should have (differentiators):**
- `active`/`effective_active` removal from OmniFocusEntity -- cleaner API
- Field removals (`sequential`, `completed_by_children`, etc.) -- leaner surface
- New date fields (`planned_date`, `drop_date`, etc.) -- SQLite-only data
- Repository layer abstraction (DataSource protocol)

**Anti-features (do NOT build):**
- Automatic SQLite-to-OmniJS silent failover -- hides broken state
- SQLite write path -- OmniFocus owns the database
- Caching layer on top of SQLite -- 46ms is fast enough
- Partial/incremental reads -- full snapshot is cheap enough

### Architecture Approach

The existing three-layer architecture (MCP Server -> Service -> Repository) stays intact. The change is below the Repository: Bridge + MtimeSource are unified into a single `DataSource` protocol with two methods (`get_mtime_ns()` and `get_raw_snapshot()`). Three implementations: `SQLiteDataSource` (primary), `BridgeDataSource` (fallback wrapping existing bridge), `InMemoryDataSource` (testing). Repository caching and lock logic are unchanged.

**Major components:**
1. `DataSource` protocol -- unified interface replacing Bridge + MtimeSource; each implementation owns both data fetching and freshness
2. `SQLiteDataSource` -- SQL queries, row-to-model mapping, WAL mtime; fresh connection per read
3. `BridgeDataSource` -- wraps existing Bridge + MtimeSource, maps old single-winner enums to two-axis with reduced Availability
4. `InMemoryDataSource` -- testing replacement for InMemoryBridge, returns fixture data

**Key architectural patterns:**
- Fresh SQLite connection per read (prevents stale WAL reads + connection leaks)
- Read-only URI mode (`mode=ro`) -- engine-level write prevention
- Column-to-field mapping in DataSource, not in models -- each source translates to the Pydantic contract
- No automatic fallback -- error-serving if SQLite unavailable, manual env var switch

### Critical Pitfalls

1. **Wrong SQLite connection mode** -- Must use `mode=ro` URI; default read-write causes SQLITE_BUSY or corruption risk. Non-negotiable from first implementation.
2. **Stale reads from connection reuse** -- WAL snapshot isolation means reused connections miss new writes. Fix: fresh connection per read (46ms makes this free).
3. **Big-bang model migration** -- 177+ tests break simultaneously. Fix: incremental migration -- add new fields alongside old, migrate consumers, remove old fields. Green suite at every step.
4. **InMemoryBridge fixture rot** -- Test fixtures shaped for bridge output don't match new two-axis model. Fix: create typed fixture factories or new InMemoryDataSource that produces the target model shape.
5. **model_rebuild namespace breakage** -- Deleting enums while `_ns` dict still references them crashes the entire module. Fix: atomic updates to `_ns`, `__all__`, and `model_rebuild()` calls together.

## Implications for Roadmap

### Phase 1: Pydantic Model Overhaul
**Rationale:** Everything imports the models -- SQLite reader, fallback mapper, tests. Must land first.
**Delivers:** New `Urgency`/`Availability` enums, field removals, updated `ActionableEntity`/`Task`/`Project`/`Tag`
**Addresses:** Two-axis status enums, field removals, model cleanup
**Avoids:** Big-bang breakage (P3) -- do incrementally: add new alongside old, migrate, remove old. Namespace breakage (P6) -- atomic updates.

### Phase 2: DataSource Protocol + InMemoryDataSource
**Rationale:** Need the abstraction layer and test infrastructure before implementing concrete data sources. Repository refactored to accept DataSource instead of Bridge + MtimeSource.
**Delivers:** `DataSource` protocol, `InMemoryDataSource`, updated `OmniFocusRepository`, all existing tests green with new test infra
**Addresses:** Repository layer abstraction
**Avoids:** Two freshness signals confusion (P9) -- DataSource couples reader + freshness as a pair

### Phase 3: SQLite Cache Reader
**Rationale:** Primary read path. Depends on models (Phase 1) and DataSource protocol (Phase 2).
**Delivers:** `SQLiteDataSource` with SQL queries, row-to-model mapping, WAL freshness, error handling
**Uses:** `sqlite3` stdlib, `os.stat()` for WAL mtime
**Avoids:** Connection mode wrong (P1), stale reads (P2), unclosed connections (P11), column mismatch (P7), schema edge cases (P15), real DB in tests (P13)

### Phase 4: Bridge Fallback + Server Wiring
**Rationale:** Fallback wraps existing bridge with new mapping; server wiring integrates everything. Both depend on all prior phases.
**Delivers:** `BridgeDataSource` with old-to-new enum mapping, `OMNIFOCUS_BRIDGE` env var routing, error-serving when SQLite not found, UAT validation
**Addresses:** OmniJS fallback, error-serving, env var wiring, MCP output schema update
**Avoids:** Blocked leaking through fallback (P8), silent automatic failover (anti-pattern)

### Phase Ordering Rationale

- Models first: imported by every other component; dependency root of the entire milestone
- Protocol + test infra second: need InMemoryDataSource to validate the Repository refactor before adding real implementations
- SQLite reader third: primary path, most complex new code, benefits from stable models and protocol
- Fallback + wiring last: adapts existing code, integration-level concerns, needs everything below to exist
- This order keeps the test suite green at every phase boundary

### Research Flags

Phases likely needing deeper research during planning:
- **Phase 1 (Model Overhaul):** Needs `/gsd:research-phase` -- incremental migration strategy across 177+ tests is nuanced; exact step-by-step order matters to avoid breakage
- **Phase 3 (SQLite Reader):** Needs `/gsd:research-phase` -- column-to-field mapping for every entity type, timestamp format handling, NULL edge cases in real DB

Phases with standard patterns (skip research-phase):
- **Phase 2 (DataSource Protocol):** Standard Protocol + DI refactor; well-documented Python pattern
- **Phase 4 (Fallback + Wiring):** Wrapping existing code + env var routing; straightforward integration

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps; all stdlib, verified locally (SQLite 3.51.0) |
| Features | HIGH | Scope defined in PROJECT.md; field-level contract validated against live DB |
| Architecture | HIGH | All integration points verified against existing codebase; DataSource pattern is a clean evolution |
| Pitfalls | HIGH | Empirical -- WAL timing, connection scoping, mtime behavior all validated in deep-dive research |

**Overall confidence:** HIGH

### Gaps to Address

- **Incremental model migration exact steps:** Research recommends incremental but doesn't prescribe the exact commit-by-commit sequence. Phase 1 planning needs to work this out.
- **SQLite timestamp formats:** Known to differ from bridge JSON, but exact format for every date field not fully documented. Phase 3 planning should include a mapping spike.
- **NULL handling in real DB:** Edge cases (tasks with no project, NULL dates, empty strings) identified as risk but not catalogued. Phase 3 tests should include pessimistic fixtures.
- **macOS App Nap impact:** Carried from v1.0 todos -- less relevant now (SQLite reads don't need OmniFocus running) but still affects write path.

## Sources

### Primary (HIGH confidence)
- `.research/deep-dives/direct-database-access/RESULTS.md` -- benchmarks (46ms), WAL timing, schema stability
- `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md` -- field mapping, enum design, removal rationale
- Python 3.12 `sqlite3` stdlib docs -- URI mode, `mode=ro`, WAL support
- SQLite WAL documentation (sqlite.org/wal.html) -- design guarantees, checkpoint behavior
- SQLite URI filenames (sqlite.org/uri.html) -- `?mode=ro` parameter

### Secondary (MEDIUM confidence)
- `.planning/PROJECT.md` -- milestone scope and requirements
- Existing codebase verification (`src/omnifocus_operator/`) -- all integration points checked
- `todo4_sqlite_freshness/FINDINGS.md` -- WAL mtime freshness validation

### Tertiary (LOW confidence)
- macOS App Nap impact on OmniFocus responsiveness -- not yet investigated for v1.1

---
*Research completed: 2026-03-07*
*Ready for roadmap: yes*
