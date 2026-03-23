# Domain Pitfalls

**Domain:** Adding SQLite cache reading + two-axis status model to existing MCP server
**Researched:** 2026-03-07
**Scope:** v1.1 milestone -- pitfalls specific to adding SQLite reader, model migration, WAL freshness, and fallback mode to the shipped v1.0 codebase

---

## Critical Pitfalls

Mistakes that cause rewrites, data corruption, or broken consumers.

### Pitfall 1: Opening SQLite with wrong mode causes OmniFocus corruption or SQLITE_BUSY

**What goes wrong:** Opening the OmniFocus database in read-write mode (the default) or with `immutable=1` while OmniFocus is actively writing causes either lock contention (SQLITE_BUSY) or silent read inconsistency.
**Why it happens:** Python's `sqlite3.connect()` defaults to read-write. `immutable=1` skips all locking -- fast but assumes no other writer exists (OmniFocus IS a writer). Both are wrong for this use case.
**Consequences:**
- Read-write mode: potential SQLITE_BUSY errors during OmniFocus checkpoints
- `immutable=1`: reads stale/inconsistent data, possible crashes if OmniFocus checkpoints mid-read
**Prevention:**
- Always open with `sqlite3.connect('file:...?mode=ro', uri=True)` -- read-only WITH proper locking
- Set `timeout=5` (default) to handle brief checkpoint locks gracefully
- Never use `immutable=1` -- OmniFocus writes continuously
**Detection:** SQLITE_BUSY errors in logs; stale data that doesn't match OmniFocus UI
**Phase:** Must be correct from the first SQLite implementation phase

### Pitfall 2: Stale reads from reusing SQLite connections across WAL changes

**What goes wrong:** A long-lived SQLite connection sees a snapshot frozen at its last read transaction start. New data written to the WAL after the connection opened is invisible until a new transaction begins.
**Why it happens:** SQLite WAL provides snapshot isolation per-transaction. A connection that opened before a write will read from the WAL state at its transaction start, not the latest state. The freshness research (TODO #4) confirmed this: `PRAGMA data_version` is connection-scoped, not absolute.
**Consequences:** Cache reports data as "fresh" (WAL mtime changed) but serves stale results because the same connection is reused.
**Prevention:**
- Open a **fresh connection for every read** (46ms query time makes this trivially cheap)
- Or explicitly start a new transaction before each query
- Never pool/reuse connections across freshness boundaries
**Detection:** Data doesn't match OmniFocus after edits despite mtime changing
**Phase:** SQLite reader implementation -- must be baked into the reader protocol

### Pitfall 3: Big-bang model migration breaks all 177+ tests simultaneously

**What goes wrong:** Changing `OmniFocusEntity` (remove `active`, `effective_active`), `ActionableEntity` (remove `completed`, `sequential`, `completed_by_children`, `should_use_floating_time_zone`; add `urgency`, `availability`), `Task` (remove `status: TaskStatus`), and `Project` (remove `status`, `task_status`, `contains_singleton_actions`) in one commit. Every test fixture, every model factory, every assertion breaks at once.
**Why it happens:** Natural instinct is "change models to match target design, then fix everything." With 177+ tests, 27 direct `TaskStatus`/`ProjectStatus` references in test_models.py, and 14 in simulator data, this creates an undebuggable wall of red.
**Consequences:** Multi-day merge confusion; can't tell if failures are from model changes vs SQLite integration vs test fixture issues
**Prevention:**
- Phase 1: Add SQLite reader as new code path alongside existing bridge (models unchanged)
- Phase 2: Add `urgency`/`availability` as NEW fields (computed from old fields), keeping old fields
- Phase 3: Migrate consumers to new fields
- Phase 4: Remove old fields + enums
- Each phase has a green test suite
**Detection:** If you're fixing more than ~20 test failures in one commit, you went too fast
**Phase:** Model migration should be its own phase, separate from SQLite reader

### Pitfall 4: InMemoryBridge test fixtures don't produce two-axis status data

**What goes wrong:** All 177+ tests use `InMemoryBridge` with fixture data shaped like the OmniJS bridge output (single `status` enum, `active` booleans). After model changes, every fixture needs updating -- but the new fields (`urgency`, `availability`) come from SQLite columns that InMemoryBridge doesn't know about.
**Why it happens:** The bridge interface returns `dict[str, Any]` which gets `model_validate`d. InMemoryBridge fixtures are hand-written dicts matching the bridge shape. The new shape is fundamentally different.
**Consequences:**
- Tests pass with wrong data shape (dict keys don't match new model)
- Or tests fail because Pydantic validation rejects missing `urgency`/`availability`
- Simulator data (14 references to old enums) also breaks
**Prevention:**
- Create typed fixture factories (not raw dicts) that enforce the current model shape
- When adding SQLite reader, have it produce the SAME dict shape as the bridge initially (translate SQL columns to expected dict format)
- Alternatively: have the repository layer normalize both sources into the Pydantic model, not the raw dict
**Detection:** `ValidationError` on `urgency` or `availability` fields in tests
**Phase:** Test infrastructure update should precede or accompany model changes

---

## Moderate Pitfalls

### Pitfall 5: WAL file doesn't exist when OmniFocus hasn't been opened recently

**What goes wrong:** The freshness detection strategy assumes `{db_path}-wal` exists for mtime polling. If OmniFocus checkpointed and closed cleanly, the WAL file may not exist (SQLite can delete it after a clean checkpoint).
**Prevention:**
- Handle `FileNotFoundError` on WAL stat gracefully -- treat as "database is current" (main .db IS the latest state)
- Fall back to main `.db` file mtime when WAL is absent
- Don't treat missing WAL as an error condition
**Phase:** SQLite freshness detection implementation

### Pitfall 6: `model_rebuild()` namespace breaks when enums are renamed/deleted

**What goes wrong:** The `__init__.py` model_rebuild chain with `_types_namespace` is fragile. Deleting `TaskStatus`/`ProjectStatus` from enums.py while `_ns` dict still references them (or vice versa) causes `PydanticUserError` at import time -- the entire module fails to load, meaning ALL tools break, not just the changed ones.
**Prevention:**
- Update `_ns` dict, `__all__`, and `model_rebuild()` calls atomically when changing enums
- Add a simple import smoke test: `from omnifocus_operator.models import Task` should be the first test to run
- The rebuild order matters: base classes first, then subclasses
**Phase:** Every model change commit

### Pitfall 7: camelCase alias mismatch between bridge JSON and SQLite column names

**What goes wrong:** Existing models use `alias_generator=to_camel` because the OmniJS bridge returns camelCase JSON (`dueDate`, `effectiveActive`). SQLite column names are different (e.g., `dateDue`, `effectiveDateOfDeferral`). If the SQLite reader produces dicts with SQLite column names, `model_validate` fails or silently drops fields.
**Prevention:**
- Map SQLite column names to the expected model field names in the SQLite reader layer, not in the models
- Keep Pydantic models as the contract; let each data source (bridge, SQLite) translate to that contract
- Write explicit column-to-field mapping tests for every entity type
**Phase:** SQLite reader implementation

### Pitfall 8: Fallback mode accidentally produces `blocked` availability value

**What goes wrong:** In OmniJS fallback mode, `blocked` is not reliably derivable (bridge's single-winner enum masks it). If fallback code accidentally returns `availability=blocked`, downstream agents make wrong decisions about task workability.
**Prevention:**
- Test-assert that OmniJS path NEVER produces `Availability.blocked`
- Explicit validation in the fallback mapper: if source is OmniJS, `blocked` is an error
- Document the reduced availability in fallback mode clearly
**Detection:** Test that iterates all tasks from OmniJS path and asserts `availability != blocked`
**Phase:** Fallback mode implementation

### Pitfall 9: Two freshness signals create confusion during migration

**What goes wrong:** v1.0 uses `FileMtimeSource` on the `.ofocus` directory to invalidate the bridge cache. v1.1 needs WAL mtime for SQLite freshness. If both exist simultaneously during migration, the wrong mtime source gets wired to the wrong reader.
**Prevention:**
- Each reader (bridge, SQLite) owns its own freshness signal -- make this explicit
- The repository constructor should take `reader + its_mtime_source` as a coupled pair
- Don't try to share a single `MtimeSource` between both paths
**Phase:** Repository refactor when adding SQLite reader

### Pitfall 10: SQLite path hardcoded or not validated at startup

**What goes wrong:** The SQLite path (`~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/...`) contains a group container ID that could change across OmniFocus versions. Hardcoding it means silent failure on version changes.
**Prevention:**
- Validate path exists at startup (not first query) -- enter error-serving mode immediately if missing
- Make path configurable via env var (`OMNIFOCUS_SQLITE_PATH`) with the known default
- Log the resolved path at startup for debuggability
**Detection:** Error-serving mode with clear message naming the expected path
**Phase:** SQLite reader initialization

### Pitfall 11: Connection left open blocks OmniFocus WAL checkpointing

**What goes wrong:** An unclosed SQLite connection (from an exception path) holds a shared lock that prevents OmniFocus from truncating the WAL file. Over time, the WAL grows unbounded, degrading OmniFocus performance.
**Prevention:**
- Always use context manager: `with sqlite3.connect(...) as conn:`
- Or explicit `try/finally` with `conn.close()`
- Keep connection lifetime to a single query (open, query, close)
- Fresh-connection-per-read pattern (Pitfall 2 prevention) also solves this
**Phase:** SQLite reader implementation

---

## Minor Pitfalls

### Pitfall 12: `st_mtime_ns` granularity varies by filesystem

**What goes wrong:** APFS (macOS default) has nanosecond mtime precision. But if someone runs on a non-APFS volume, mtime granularity could be 1 second, making rapid writes invisible.
**Prevention:** This is macOS-only software on APFS; document the assumption. Don't over-engineer.
**Phase:** Documentation only

### Pitfall 13: Test safety -- automated tests must never touch the real SQLite cache

**What goes wrong:** A test accidentally reads from `~/Library/Group Containers/...` instead of a test fixture database. Violates SAFE-01 spirit (real data access in automated tests) and makes tests environment-dependent.
**Prevention:**
- SQLite reader accepts path as constructor parameter (DI)
- Test fixtures use in-memory SQLite or temp file with known schema
- Add guard similar to SAFE-01: if `PYTEST_CURRENT_TEST` is set, reject the real database path
**Phase:** SQLite reader design -- bake in testability from day one

### Pitfall 14: Snapshot model loses backward compatibility for MCP consumers

**What goes wrong:** MCP tool output changes shape (fields renamed/removed, enums replaced). AI agents with cached context about the old schema send wrong queries or misinterpret results.
**Prevention:**
- This is a breaking change -- own it. Bump version to v1.1
- Document migration clearly (old field -> new field mapping)
- MCP tool descriptions should describe the output schema so agents adapt
**Phase:** Final integration phase

### Pitfall 15: SQLite reader tested only with happy-path schema

**What goes wrong:** Tests use a perfectly shaped in-memory SQLite database. Real OmniFocus database has NULL values in unexpected columns, empty strings where None is expected, or timestamp formats that differ from what the reader assumes.
**Prevention:**
- Test with edge cases: NULL dates, empty names, zero-length notes, tasks with no project
- If possible, create a sanitized export of the real database schema for integration tests
- Pydantic's fail-fast validation catches most of these, but the error messages need to be actionable
**Phase:** SQLite reader testing

---

## Phase-Specific Warnings

| Phase Topic | Likely Pitfall | Mitigation |
|---|---|---|
| SQLite reader implementation | Connection mode wrong (P1), stale reads (P2), unclosed connections (P11) | Read-only URI mode, fresh connection per read, context managers |
| SQLite reader implementation | Column name mapping (P7), schema edge cases (P15) | Explicit mapping layer, column-to-field tests |
| WAL freshness detection | Missing WAL file (P5), two mtime sources (P9) | Graceful fallback to .db mtime, pair reader+source |
| Model migration | Big-bang breakage (P3), fixture rot (P4) | Incremental multi-phase migration, typed fixture factories |
| Model migration | model_rebuild breakage (P6) | Atomic namespace updates, import smoke test |
| Fallback mode | Blocked leaking through (P8) | Test-assert no `blocked` from OmniJS path |
| Test infrastructure | Real DB in tests (P13) | DI path param, PYTEST_CURRENT_TEST guard |
| Final integration | MCP output shape change (P14) | Version bump, schema in tool descriptions |

---

## Sources

- [SQLite WAL documentation](https://sqlite.org/wal.html) -- WAL mode design guarantees, checkpoint behavior
- [SQLite URI filenames](https://sqlite.org/uri.html) -- `?mode=ro` parameter documentation
- [Python sqlite3 docs](https://docs.python.org/3/library/sqlite3.html) -- URI mode, timeout parameter
- [SQLite file locking](https://sqlite.org/lockingv3.html) -- concurrent access behavior
- [SQLite BUSY in WAL mode](https://sqlite.org/forum/forumpost/c4dbf6ca17) -- edge cases for SQLITE_BUSY
- [SQLite BUSY debugging](https://sqlite.org/forum/info/518620caf1be1bbfc5b12a12114e29da91d07aabbcc85dab8f704f1f3af0b48f) -- checkpoint-related BUSY
- Project: `.research/deep-dives/direct-database-access/RESULTS.md` -- architecture decisions
- Project: `todo4_sqlite_freshness/FINDINGS.md` -- WAL mtime freshness validation, connection scoping
- Project: `todo1_cache_timing/FINDINGS.md` -- propagation delay measurements
- Project: `RESULTS_pydantic-model.md` -- model migration design, field removal rationale
