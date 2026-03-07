# Phase 12: SQLite Reader - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Implement HybridRepository with read-only SQLite access, row-to-model mapping with two-axis status, and WAL-based freshness detection. Server reads OmniFocus data directly from SQLite cache -- no OmniFocus process required. Writes and fallback mode are Phase 13.

</domain>

<decisions>
## Implementation Decisions

### Repository naming
- **HybridRepository** (not SQLiteRepository) -- named for its future role: reads from SQLite, writes via Bridge, freshness handled internally
- Lives at `repository/hybrid.py`
- When writes arrive in a future phase, may be renamed to something else (e.g., AcceleratedRepository) but HybridRepository communicates the dual-source intent from day one
- No rename needed when writes are added -- the name already anticipates it

### DB path configuration
- Default path: `~/Library/Group Containers/34YW5XSRB7.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/com.omnigroup.OmniFocusModel/OmniFocusDatabase.db`
- Env var override: `OMNIFOCUS_SQLITE_PATH`
- Constructor accepts `db_path: Path | None` parameter -- if provided, uses it; otherwise falls back to env var, then default
- This makes testing trivial (pass a temp file path) and production flexible

### Freshness coordination
- Built in Phase 12 (FRESH-01, FRESH-02 stay in this phase)
- WAL file `st_mtime_ns` polling: every 50ms, 2s timeout (per research)
- When WAL file doesn't exist (clean OmniFocus shutdown): fall back to main `.db` file mtime
- Freshness is internal to HybridRepository -- consumers just call `get_all()` and get fresh data
- `TEMPORARY_simulate_write()` method on **HybridRepository only** (not on the Repository protocol):
  - Marks internal state as stale so next `get_all()` triggers WAL polling
  - Exists solely for testing the freshness mechanism
  - Comment: "Delete this method when real writes are implemented"
  - Tests call it directly on the concrete HybridRepository type

### Repository protocol
- Protocol stays clean: only `get_all() -> AllEntities`
- No temporary or write methods on the protocol
- When real writes arrive (future phase), protocol grows a proper `write()` method

### Test fixture strategy
- In-memory SQLite built in tests via stdlib `sqlite3`
- Shared test factory helper: `create_test_db(tasks=[...], projects=[...])` that builds schema and inserts rows
- Full control over edge cases: NULL dates, both timestamp formats (CF epoch floats and ISO 8601), all status combos, perspective plist blobs
- Read-only UAT script against real OmniFocus SQLite database (lives in `uat/` folder)
- UAT validates: entities parse correctly, status axes populated, timestamp formats handled

### Claude's Discretion
- Row-to-model mapping implementation (raw SQL queries, column name constants, etc.)
- Perspective `valueData` plist parsing approach (stdlib `plistlib`)
- Timestamp format detection and parsing (CF epoch vs ISO 8601)
- Module structure within `repository/` (helpers, query builders, etc.)
- Test factory API design and internal structure
- UAT script structure and validation assertions
- Error handling for corrupt/missing columns (fail-fast pattern established)

</decisions>

<specifics>
## Specific Ideas

- "OmniFocus is extremely, extremely, extremely slow -- keep the bridge as dumb as possible. Any computation, put it in Python" (carried from Phase 10)
- HybridRepository named for future intent: "if later we put the write through the repository and then call the bridge internally, we can potentially rename it" -- but HybridRepository already communicates dual-source
- Freshness as internal implementation detail: "If you know you are in control of all the reads and writes, then the freshness can be an implementation detail inside the repository"
- TEMPORARY_simulate_write() deliberately ugly naming to ensure cleanup: "making clear that this is a temporary method"

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Repository` protocol (`repository/protocol.py`): `async get_all() -> AllEntities` -- HybridRepository must satisfy this
- `AllEntities` model (`models/snapshot.py`): target output shape (tasks, projects, tags, folders, perspectives)
- `OmniFocusBaseModel` with ConfigDict (camelCase aliases, populate_by_name)
- Two-axis enums (`models/enums.py`): `Urgency`, `Availability`, `TagAvailability`, `FolderAvailability`
- All Pydantic models already reflect two-axis status (Phase 10 complete)
- `BridgeRepository` (`repository/bridge.py`): reference for caching/freshness patterns

### Established Patterns
- Fail-fast on unknown enum values at bridge boundary -- maintain for SQLite boundary
- `StrEnum` for all enums
- `TYPE_CHECKING` + `model_rebuild` for ruff TC + Pydantic compat
- Fresh connection per read (research: no stale WAL reads)
- Read-only mode (`?mode=ro`)

### Integration Points
- `repository/__init__.py`: export HybridRepository, update factory
- `server.py`: wire HybridRepository as default (or via env var routing -- may be Phase 13)
- `repository/hybrid.py`: new file, satisfies Repository protocol
- Research field mappings: `.research/deep-dives/direct-database-access/RESULTS_pydantic-model.md`
- Research column corrections: `.research/deep-dives/direct-database-access/4-final-checks/FINDINGS.md`

</code_context>

<deferred>
## Deferred Ideas

- **Writes through Repository** -- HybridRepository will route writes through Bridge internally in a future phase. Freshness mechanism is built now; write path comes later.
- **Repository rename** -- HybridRepository may be renamed (AcceleratedRepository, etc.) when writes are added. Current name is intentional.
- **Server wiring** -- Whether HybridRepository becomes the default in `server.py` is a Phase 13 concern (env var routing: `OMNIFOCUS_REPOSITORY=bridge` vs SQLite default).

</deferred>

---

*Phase: 12-sqlite-reader*
*Context gathered: 2026-03-07*
