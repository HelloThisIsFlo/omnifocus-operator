# Phase 13: Fallback and Integration - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Wire HybridRepository as the default read path, add OmniJS bridge fallback via `OMNIFOCUS_REPOSITORY=bridge` env var, and error-serving mode when SQLite is unavailable. No automatic failover -- user must explicitly choose the fallback. Bridge mode is a temporary workaround (days, not permanent), not a first-class mode.

</domain>

<decisions>
## Implementation Decisions

### Error message when SQLite not found
- Human-readable prose (agent reads it naturally and relays to user)
- Content distinguishes **fix** vs **workaround**:
  - Fix: find the correct SQLite path, set `OMNIFOCUS_SQLITE_PATH`
  - Workaround: set `OMNIFOCUS_REPOSITORY=bridge` for temporary degraded fallback
- Show the expected path that was checked
- No reason detection (don't check WHY SQLite is missing -- just report the path and actions)
- Path + fallback instructions only, matching FALL-03 requirements exactly

### Error-serving mode
- When `OMNIFOCUS_REPOSITORY=sqlite` (default) and SQLite DB not found: enter error-serving mode via existing `ErrorOperatorService`
- Server stays alive, returns actionable error on first tool call
- No automatic bridge failover (explicitly out of scope per REQUIREMENTS)
- Consistent with Phase 9 design

### Bridge mode availability limitation
- Bridge maps ambiguous tasks to `available` (most likely value) -- no `blocked` distinction
- **No model pollution** -- no metadata fields, no caveats in response data
- Startup log warning when running in bridge mode (for debugging, agent won't see it)
- **Documentation handles the caveat** -- `configuration.md` explains "degraded mode" means no `blocked` availability
- Error message (SQLite not found) mentions bridge as fallback with note about degraded mode
- Bridge fallback is a temporary workaround (1-2 days), not a permanent mode

### Server lifespan restructuring
- **Repository factory function** in `repository/__init__.py`: `create_repository(repo_type)` reads `OMNIFOCUS_REPOSITORY` env var
- Factory returns `HybridRepository` (default/sqlite) or `BridgeRepository` (bridge fallback)
- Factory encapsulates bridge-repository-specific setup: MtimeSource, ofocus path validation
- Factory raises on SQLite not found -- caught by lifespan's try/except, enters ErrorOperatorService
- Lifespan stays clean: calls factory, creates OperatorService, yields

### IPC orphan sweep scope
- **IPC orphan sweep stays in server lifespan** (bridge-level concern, not bridge-repository-level)
- **Always runs** regardless of `OMNIFOCUS_REPOSITORY` setting -- future-proofs for when HybridRepository uses Bridge for writes
- No-op if no IPC dir exists
- Key distinction: MtimeSource is bridge-*repository* concern (read-side caching), IPC is bridge concern (used by all OmniFocus communication)

### Claude's Discretion
- Repository factory implementation details (error message exact wording)
- How to restructure the existing bridge setup code when extracting to factory
- Test strategy for the new factory and error-serving paths
- Configuration.md updates for degraded mode documentation

</decisions>

<specifics>
## Specific Ideas

- "The fix is to actually find the correct path. A workaround is to use the bridge for fallback" -- error message should make this distinction clear
- "I don't want to pollute the output because the regular mode doesn't have this caveat" -- bridge limitations are documentation-only, not runtime metadata
- "The IPC, which is bridge-related, should stay common. That's a difference between the MtimeSource, which is bridge-repository-related" -- clean separation of bridge vs bridge-repository concerns
- Bridge fallback framed as "maybe one or two days as a quick fix" -- not a permanent operating mode

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `ErrorOperatorService` (`service.py`): already intercepts every method call and returns startup error -- reuse for SQLite not found
- `Repository` protocol (`repository/protocol.py`): `async get_all() -> AllEntities` -- both HybridRepository and BridgeRepository satisfy it
- `create_bridge()` (`bridge/factory.py`): pattern to follow for `create_repository()`
- `BridgeRepository` (`repository/bridge.py`): existing bridge read path with MtimeSource and caching
- `HybridRepository` (`repository/hybrid.py`): SQLite reader, already complete from Phase 12
- `docs/configuration.md`: already documents `OMNIFOCUS_REPOSITORY` as "Coming in Phase 13"

### Established Patterns
- Error-serving degraded mode: server catches startup exceptions, yields ErrorOperatorService
- Factory pattern: `create_bridge(bridge_type)` in `bridge/factory.py`
- Env var configuration: `OMNIFOCUS_BRIDGE`, `OMNIFOCUS_OFOCUS_PATH`, `OMNIFOCUS_SQLITE_PATH`
- Bridge adapter maps old status -> new two-axis model (availability maps to available/completed/dropped)

### Integration Points
- `server.py`: lifespan restructured -- factory call replaces inline bridge setup, IPC sweep stays
- `repository/__init__.py`: add `create_repository` export
- `docs/configuration.md`: update "Coming in Phase 13" -> active documentation, add degraded mode explanation
- Bridge adapter (`bridge/adapter.py`): already handles the reduced availability mapping

</code_context>

<deferred>
## Deferred Ideas

- **Writes through HybridRepository** -- HybridRepository will route writes through Bridge internally in a future milestone. IPC sweep already runs always to future-proof this.
- **Repository rename** -- HybridRepository may be renamed when writes are added. Current name is intentional.

</deferred>

---

*Phase: 13-fallback-and-integration*
*Context gathered: 2026-03-07*
