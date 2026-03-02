# Phase 4: Repository and Snapshot Management - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

A repository layer that loads and caches a full database snapshot from the bridge, serves reads from memory, and refreshes only when OmniFocus data changes (mtime-based). Concurrent access is serialized with an asyncio.Lock. Cache is pre-warmed at startup. The service layer and MCP server (Phase 5) will consume this repository.

</domain>

<decisions>
## Implementation Decisions

### Refresh error handling
- Fail fast on all errors: bridge failures, parse/validation failures propagate to caller immediately
- No stale data fallback — if refresh fails, the error reaches the caller regardless of whether a cached snapshot exists
- No cooldown or backoff between failed refresh attempts — next read simply tries again (MCP traffic is low-volume, no risk of hammering)

### Startup failure mode
- Abort server startup if pre-warm dump fails — server refuses to start without initial data
- MCP host (Claude Desktop, Claude Code) handles restart/retry — server doesn't need its own retry logic
- Pre-warm naturally fits inside the MCP lifespan context manager — if it raises, server never starts

### Concurrent read behavior
- All reads block while a refresh is in progress — reads wait for fresh data, never return stale
- Single `asyncio.Lock` for everything: prevents duplicate dumps AND serializes reads during refresh
- On first load (no cache), all reads block on the lock since there's no stale data to serve anyway
- After cache is warm, reads that don't trigger a refresh (mtime unchanged) return immediately without contention

### Claude's Discretion
- Error type strategy: whether to wrap BridgeErrors in RepositoryError or let them propagate raw
- Pre-warm location: inside MCP lifespan vs repository's own init — pick what fits cleanest
- Mtime source abstraction: pluggable callable/protocol vs hardcoded path with temp dirs in tests

</decisions>

<specifics>
## Specific Ideas

- "I'd rather have an error I can later fix and diagnose than silently recover" — fail-fast philosophy drives all error decisions
- "For this version we just retry on next read because we're not going to have thousands of calls per minute — it's MCP, so it's one call every 5 seconds, or maybe a few parallel calls"
- Kubernetes analogy: the MCP host is the orchestrator, the server is the pod — crash cleanly, let the host restart

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Bridge` protocol (`bridge/_protocol.py`): async `send_command(operation, params) -> dict` — repository calls this for dumps
- `InMemoryBridge` (`bridge/_in_memory.py`): test double with `call_count` property — ideal for verifying cache-hit behavior (dump called once vs multiple times)
- `DatabaseSnapshot` (`models/_snapshot.py`): Pydantic model the repository caches — aggregates tasks, projects, tags, folders, perspectives
- `BridgeError` hierarchy (`bridge/_errors.py`): `BridgeError`, `BridgeTimeoutError`, `BridgeConnectionError`, `BridgeProtocolError` — repository needs to handle/propagate these

### Established Patterns
- Structural typing via `Protocol` (bridge) — repository should accept any Bridge, not a concrete class
- Pydantic models with `OmniFocusBaseModel` base — snapshot parsing uses this
- `from __future__ import annotations` used consistently across all modules

### Integration Points
- Repository is consumed by the service layer (Phase 5) which sits between MCP tools and the repository
- Pre-warm hooks into MCP server lifespan (`asynccontextmanager` pattern from FastMCP)
- Mtime source in production is the `.ofocus` directory within the OmniFocus 4 sandbox

</code_context>

<deferred>
## Deferred Ideas

- Detect OmniFocus "closed" vs "broken" at startup — return actionable message ("please open OmniFocus") vs generic error — future milestone
- Auto-open OmniFocus via AppleScript if it's just closed — future milestone
- Graceful degradation (serve stale data + warning on refresh failure) — revisit if fail-fast proves too strict in real usage

</deferred>

---

*Phase: 04-repository-and-snapshot-management*
*Context gathered: 2026-03-02*
