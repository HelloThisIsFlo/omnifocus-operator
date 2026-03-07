# OmniFocus Operator

## What This Is

A Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Provides a clean, protocol-first interface for querying tasks, projects, tags, and perspectives -- enabling any AI agent to interact with OmniFocus without workflow-specific assumptions.

v1.0 ships a working `list_all` tool that returns the full OmniFocus database as structured Pydantic data, with pluggable bridge implementations (InMemory, Simulator, Real) and robust file-based IPC.

## Core Value

Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## Requirements

### Validated

- Three-layer architecture: MCP Server -> Service Layer -> OmniFocus Repository -- v1.0
- Bridge interface with pluggable implementations (InMemory, Simulator, Real) -- v1.0
- Full database snapshot loaded into memory from bridge dump -- v1.0
- File-based IPC with atomic writes (`.tmp` -> rename) -- v1.0
- `list_all` MCP tool returning full structured database -- v1.0
- Pydantic models derived from bridge script output shape -- v1.0
- Snapshot freshness via `.ofocus` directory mtime check -- v1.0
- Deduplication lock preventing parallel dump storms -- v1.0
- Mock simulator as standalone Python script for IPC testing -- v1.0
- Timeout handling with clear error messages -- v1.0
- Error-serving degraded mode (startup errors -> actionable tool responses) -- v1.0
- BRIDGE-SPEC alignment: fail-fast enums, per-entity status resolvers -- v1.0

### Active

(None -- next milestone not yet scoped)

### Out of Scope

- Workflow-specific logic (daily review, prioritization) -- server is a general-purpose bridge; workflow lives in the agent
- Custom exception hierarchy -- use standard Python exceptions, refine when real error patterns emerge
- Tag writes, folder writes, task reordering, undo/dry run -- future milestones
- Mobile/iOS support -- OmniFocus desktop only (macOS)
- TaskPaper output format -- future milestone
- Production hardening (retry logic, crash recovery, idempotency) -- future milestone
- MCP Prompts -- workflow-specific; server exposes primitives only
- WebSocket/SSE transport -- stdio only, local server
- AppleScript/osascript bridge -- file-based IPC is the differentiator
- Real-time file watching for snapshot -- mtime check on read is sufficient

## Context

Shipped v1.0 with ~5,943 LOC Python, ~215k LOC JS (bridge + node_modules), ~28k LOC TS (tests).
Tech stack: Python 3.12, uv, Pydantic v2, MCP SDK (FastMCP), OmniJS bridge.
177+ pytest tests (~98% coverage), 26 Vitest tests, UAT passed on all phases.
Real OmniFocus database: ~2,400 tasks, ~363 projects, ~64 tags, ~79 folders, ~1.5MB JSON snapshot.
Five milestones planned (Foundation -> Filtering -> Entity Browsing -> Perspectives -> Writes).

## Constraints

- **Language**: Python 3.12+ with async, Pydantic models, MCP SDK
- **Platform**: macOS only -- OmniFocus is a macOS application
- **IPC directory**: `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/` (configurable for dev/test)
- **Schema source**: Bridge script output defines the data shape -- Pydantic models derive from it, not the other way around
- **Field naming**: JSON from OmniFocus is camelCase; Pydantic uses snake_case with camelCase aliases for serialization

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Three-layer architecture (MCP -> Service -> Repository) | Clear separation of concerns; service layer is thin in M1 but reserves space for filtering in M2 | Good -- clean boundaries, easy to test each layer independently |
| File-based IPC via OmniFocus sandbox | Benchmarked as most efficient; works within OmniFocus sandbox constraints | Good -- reliable, debuggable, atomic |
| Full snapshot in memory, no partial invalidation | Database is small (~1.5MB); sub-millisecond filtering; simplicity over complexity | Good -- no performance issues at 2,400 tasks |
| Bridge script as direction, not literal artifact | Proven IPC approach and data shape; implementation improved for readability | Good -- BRIDGE-SPEC alignment validated empirically |
| Workflow-agnostic server | Expose primitives, not opinions; workflow logic belongs in the agent | Good -- keeps server scope minimal |
| Fail-fast on unknown enum values | Pydantic ValidationError with clear listing of valid values; no silent fallback | Good -- caught real data issues during UAT |
| Lazy cache hydration (removed eager startup) | First tool call populates cache; avoids blocking server startup | Good -- faster startup, no wasted work |
| Error-serving degraded mode | MCP servers are headless; crashes are invisible. Serve errors as tool responses | Good -- agent discovers errors on first call with clear message |
| SimulatorBridge inherits RealBridge, overrides trigger only | Minimal code duplication; full IPC pipeline tested without OmniFocus | Good -- single IPC implementation, two behaviors |

---
*Last updated: 2026-03-07 after v1.0 milestone*
