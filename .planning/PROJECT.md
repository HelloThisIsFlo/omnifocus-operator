# OmniFocus Operator

## What This Is

A Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads OmniFocus data directly from its SQLite cache for fast (~46ms), reliable access without requiring OmniFocus to be running. Provides a clean, protocol-first interface for querying tasks, projects, tags, and perspectives with a two-axis status model (Urgency + Availability).

## Core Value

Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## Requirements

### Validated

- Three-layer architecture: MCP Server -> Service Layer -> Repository -- v1.0
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
- Two-axis status model (Urgency + Availability) replacing single-winner enums -- v1.1
- Pydantic model overhaul: deprecated fields removed, shared enums -- v1.1
- SQLite cache as primary read path (~46ms full snapshot, OmniFocus not needed) -- v1.1
- WAL-based read-after-write freshness detection (50ms poll, 2s timeout) -- v1.1
- Repository protocol abstracting read path (HybridRepository, BridgeRepository, InMemoryRepository) -- v1.1
- Error-serving degraded mode when SQLite unavailable (manual fallback via env var) -- v1.1

### Active

<!-- Current milestone: v1.2 Writes & Lookups -->

- [ ] Get-by-ID tools: `get_task`, `get_project`, `get_tag` -- single-entity lookup by primary key
- [ ] Write pipeline: MCP -> Service -> Repository -> Bridge -> invalidate snapshot
- [ ] Task creation: `add_tasks` -- create tasks with project/parent/tags/dates/flags
- [ ] Task editing: `edit_tasks` -- patch semantics (omit/null/value), tag modes, task movement
- [ ] Lifecycle changes: complete/drop/reactivate tasks via `edit_tasks`
- [ ] Bridge script: new commands (get_task, get_project, get_tag, add_task, edit_task) with request file payloads

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
- Automatic SQLite-to-OmniJS failover -- silent fallback hides broken state; user must know which path is active
- SQLite write path -- OmniFocus owns the database; writing to its cache corrupts state
- Caching layer on top of SQLite -- 46ms full snapshot is fast enough
- `next` availability value -- not present in SQLite or OmniJS
- Schema migration / version detection -- OmniFocus SQLite schema stable since OF1

## Context

Shipped v1.1 with ~14,144 LOC Python, ~215k LOC JS (bridge + deps), ~28k TS (tests).
Tech stack: Python 3.12, uv, Pydantic v2, MCP SDK (FastMCP), OmniJS bridge, SQLite3 (stdlib).
313 pytest tests (~98% coverage), 26 Vitest tests, UAT passed on all phases.
Real OmniFocus database: ~2,400 tasks, ~363 projects, ~64 tags, ~79 folders.
Two read paths: SQLite (default, ~46ms) and OmniJS bridge (fallback, ~1.5MB JSON snapshot).

## Constraints

- **Language**: Python 3.12+ with async, Pydantic models, MCP SDK
- **Platform**: macOS only -- OmniFocus is a macOS application
- **Runtime deps**: `mcp>=1.26.0` only -- zero new deps in v1.1 (stdlib sqlite3)
- **IPC directory**: `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/` (configurable for dev/test)
- **SQLite path**: `~/Library/Group Containers/34YW5A3IGP.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocusDatabase.db`
- **Field naming**: JSON from OmniFocus is camelCase; Pydantic uses snake_case with camelCase aliases for serialization

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Three-layer architecture (MCP -> Service -> Repository) | Clear separation of concerns; service layer is thin in M1 but reserves space for filtering in M2 | Good -- clean boundaries, easy to test each layer independently |
| File-based IPC via OmniFocus sandbox | Benchmarked as most efficient; works within OmniFocus sandbox constraints | Good -- reliable, debuggable, atomic |
| Full snapshot in memory, no partial invalidation | Database is small (~1.5MB); sub-millisecond filtering; simplicity over complexity | Good -- no performance issues at 2,400 tasks |
| Workflow-agnostic server | Expose primitives, not opinions; workflow logic belongs in the agent | Good -- keeps server scope minimal |
| Fail-fast on unknown enum values | Pydantic ValidationError with clear listing of valid values; no silent fallback | Good -- caught real data issues during UAT |
| Error-serving degraded mode | MCP servers are headless; crashes are invisible. Serve errors as tool responses | Good -- agent discovers errors on first call with clear message |
| Two-axis status model (Urgency + Availability) | Matches OmniFocus internal representation; single-winner enums lost information | Good -- richer status semantics, cleaner model |
| SQLite cache as primary read path | 46ms vs multi-second bridge round-trip; no OmniFocus process needed | Good -- massive perf improvement, simpler architecture |
| Repository protocol (structural typing) | Swappable implementations without inheritance coupling | Good -- HybridRepository, BridgeRepository, InMemoryRepository all interchangeable |
| Dict-based adapter mapping tables | Static mapping = dict lookup, not if/elif; in-place modification for zero-copy | Good -- fast, readable, easily extensible |
| WAL mtime for freshness detection | WAL updates on every write; mtime_ns gives nanosecond precision | Good -- reliable read-after-write consistency |
| Manual bridge fallback via env var | Silent automatic failover hides broken state; user must know which path is active | Good -- explicit is better than implicit |
| Project-first parent resolution | When resolving a parent ID, try `get_project` before `get_task`. Project takes precedence. In practice IDs don't collide, but the order is intentional and deterministic | Decided in Phase 15, documented in Phase 16 |
| Patch semantics via sentinel pattern | Edit models use UNSET sentinel to distinguish "not provided" from "null" (clear) from "value" (set). Pydantic can't distinguish omitted from None natively, sentinel solves the three-way | Phase 16 -- first partial-update API |
| moveTo "key IS the position" design | Task movement expressed as `{"moveTo": {"ending": "parentId"}}` -- the key (beginning/ending/before/after) IS the position, the value IS the reference. Exactly one key allowed. Makes illegal states unrepresentable -- no runtime validation needed for invalid position+reference combos | Phase 16 -- maps directly to OmniJS position API |
| Educational warnings in write responses | Write results include optional `warnings` array for no-ops (e.g., removing a tag not present, moving to same position) with hints like "omit moveTo to skip movement". Teaches agents patch semantics in-context | Phase 16 -- LLMs learn from tool responses |

---
## Current Milestone: v1.2 Writes & Lookups

**Goal:** Enable agents to look up individual entities by ID and create/edit tasks in OmniFocus, validating the write pipeline end-to-end.

**Target features:**
- Get-by-ID tools (get_task, get_project, get_tag)
- Task creation (add_tasks)
- Task editing with patch semantics (edit_tasks)
- Lifecycle changes (complete, drop, reactivate)
- Bridge script write commands with request file payloads

---
*Last updated: 2026-03-07 after v1.2 milestone started*
