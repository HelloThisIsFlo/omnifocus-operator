# OmniFocus Operator

## What This Is

A Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. Reads via SQLite cache (~46ms), writes via OmniJS bridge. Six MCP tools: `get_all`, `get_task`, `get_project`, `get_tag`, `add_tasks`, `edit_tasks`. Agent-first design with educational warnings, patch semantics, and structured actions for tags/movement/lifecycle.

## Core Value

Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## Current Milestone: v1.2.3 Repetition Rule Write Support

**Goal:** Enable agents to set, modify, and remove repetition rules on tasks via structured fields -- symmetric read/write model, no raw RRULE strings exposed. No new tools.

**Target features:**
- Structured frequency model with type discriminator (8 frequency types)
- Root-level repetition fields: schedule, basedOn, end
- Partial update lifecycle (merge, type-change, clear, create)
- RRULE parser/builder utilities wired to both read paths
- Three-layer validation (structural, type-specific, semantic)
- Read model breaking change: ruleString replaced by structured fields

## Requirements

### Validated

- Three-layer architecture: MCP Server -> Service Layer -> Repository — v1.0
- Bridge interface with pluggable implementations (InMemory, Simulator, Real) — v1.0
- Full database snapshot loaded into memory from bridge dump — v1.0
- File-based IPC with atomic writes (`.tmp` -> rename) — v1.0
- Pydantic models derived from bridge script output shape — v1.0
- Snapshot freshness via `.ofocus` directory mtime check — v1.0
- Deduplication lock preventing parallel dump storms — v1.0
- Mock simulator as standalone Python script for IPC testing — v1.0
- Timeout handling with clear error messages — v1.0
- Error-serving degraded mode (startup errors -> actionable tool responses) — v1.0
- BRIDGE-SPEC alignment: fail-fast enums, per-entity status resolvers — v1.0
- Two-axis status model (Urgency + Availability) replacing single-winner enums — v1.1
- Pydantic model overhaul: deprecated fields removed, shared enums — v1.1
- SQLite cache as primary read path (~46ms full snapshot, OmniFocus not needed) — v1.1
- WAL-based read-after-write freshness detection (50ms poll, 2s timeout) — v1.1
- Repository protocol abstracting read path (HybridRepository, BridgeRepository, InMemoryRepository) — v1.1
- Error-serving degraded mode when SQLite unavailable (manual fallback via env var) — v1.1
- ✓ Unified parent model (`parent: {type, id} | null`), `get_all` renamed from `list_all` — v1.2
- ✓ Get-by-ID tools (`get_task`, `get_project`, `get_tag`) with dedicated SQLite queries — v1.2
- ✓ Write pipeline: MCP → Service → Repository → Bridge → OmniFocus with write-through guarantee — v1.2
- ✓ Task creation (`add_tasks`) with parent/tag resolution, validation, per-item results — v1.2
- ✓ Task editing (`edit_tasks`) with UNSET sentinel patch semantics, actions block (tags/move/lifecycle) — v1.2
- ✓ Diff-based tag computation in Python service layer, bridge receives only addTagIds/removeTagIds — v1.2
- ✓ Task lifecycle (complete/drop) with no-op detection and educational warnings — v1.2
- ✓ Bridge script write commands (add_task, edit_task) with request file payloads — v1.2
- ✓ Write model strictness: `extra="forbid"` catches unknown agent fields at validation time — v1.2.1
- ✓ FastMCP v3 dependency swap: `fastmcp>=3.1.1` replaces `mcp>=1.26.0`, native imports, `ctx.lifespan_context` shorthand — v1.2.2
- ✓ Progress reporting in batch write tools via `ctx.report_progress()` — v1.2.2
- ✓ Test client migration: 10-line `Client(server)` fixture replacing 65-line `_ClientSessionProxy`, `pytest.raises(ToolError)` pattern — v1.2.2
- ✓ ToolLoggingMiddleware: automatic entry/exit/error logging for all tools via FastMCP middleware API — v1.2.2
- ✓ Dual-handler logging: `StreamHandler(stderr)` + 5MB `RotatingFileHandler` with `__name__` convention across all modules — v1.2.2
- ✓ Warning string consolidation into agent_messages/ package with AST integrity tests — v1.2.1
- ✓ Three-layer model taxonomy (Command/RepoPayload/RepoResult/Result) in contracts/ package — v1.2.1
- ✓ Write pipeline unification: symmetric add/edit signatures, BridgeWriteMixin, exclude_unset — v1.2.1
- ✓ Service decomposition: service.py → service/ package (Resolver, DomainLogic, PayloadBuilder, orchestrator) — v1.2.1
- ✓ SimulatorBridge removed from exports, bridge factory eliminated, PYTEST guard in RealBridge — v1.2.1
- ✓ All test doubles relocated from src/ to tests/doubles/ with structural import barrier — v1.2.1
- ✓ Patch[T]/PatchOrClear[T] type aliases make patch semantics self-documenting in annotations — v1.2.1
- ✓ InMemoryRepository deleted; stateful InMemoryBridge exercises real serialization in tests — v1.2.1
- ✓ StubBridge extracted as canned-response double; InMemoryBridge is purely stateful — v1.2.1
- ✓ @pytest.mark.snapshot marker + fixture composition eliminates test boilerplate — v1.2.1
- ✓ Golden master contract testing: 43 scenarios proving InMemoryBridge ≡ RealBridge equivalence — v1.2.1
- ✓ 9 fields graduated from VOLATILE/UNCOMPUTED to verified via ancestor-chain inheritance — v1.2.1

### Active

- [ ] SQL filtering for tasks, projects, tags (v1.3)
- [ ] List/count for all entities (v1.3)
- [ ] Substring search (v1.3)
- [ ] Field selection, task deletion, notes append (v1.4)
- [ ] Fuzzy search (v1.4.1)
- [ ] TaskPaper output format (v1.4.2)
- [ ] Project writes (v1.4.3)
- [ ] Perspectives support, deep links (v1.5)
- [ ] Production hardening — retry, crash recovery, serial execution (v1.6)

### Out of Scope

- Workflow-specific logic (daily review, prioritization) -- server is a general-purpose bridge; workflow lives in the agent
- Custom exception hierarchy -- use standard Python exceptions, refine when real error patterns emerge
- Task reactivation (markIncomplete) — OmniJS API unreliable, deferred
- Tag writes, folder writes, task reordering, undo/dry run — future milestones
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

Shipped v1.2.2 with ~16,384 LOC Python (src + tests), ~215k LOC JS (bridge + deps), ~28k TS (tests).
Tech stack: Python 3.12, uv, Pydantic v2, FastMCP v3 (`fastmcp>=3.1.1`), OmniJS bridge, SQLite3 (stdlib).
708 pytest tests (98% coverage), 26 Vitest tests, UAT passed on all phases.
Real OmniFocus database: ~2,400 tasks, ~363 projects, ~64 tags, ~79 folders.
Read path: SQLite (default, ~46ms). Write path: OmniJS bridge with write-through guarantee.
6 MCP tools: get_all, get_task, get_project, get_tag, add_tasks, edit_tasks.
Architecture: service/ package (Resolver, DomainLogic, PayloadBuilder, orchestrator), contracts/ package (Command, RepoPayload, Result models), tests/doubles/ (InMemoryBridge, StubBridge, SimulatorBridge).
Golden master: 43 scenarios in 7 categories, contract tests verify InMemoryBridge matches RealBridge.
Logging: ToolLoggingMiddleware for automatic tool call logging, dual-handler (stderr + rotating file) under `omnifocus_operator.*` namespace.

## Constraints

- **Language**: Python 3.12+ with async, Pydantic models, MCP SDK
- **Platform**: macOS only -- OmniFocus is a macOS application
- **Runtime deps**: `fastmcp>=3.1.1` only -- zero new deps in v1.1 (stdlib sqlite3)
- **IPC directory**: `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/` (configurable for dev/test)
- **SQLite path**: `~/Library/Group Containers/34YW5A3IGP.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocusDatabase.db`
- **Field naming**: JSON from OmniFocus is camelCase; Pydantic uses snake_case with camelCase aliases for serialization
- **Dev commands**: Run tests: `uv run pytest`. Run Python: `uv run python`. Always use `uv run` — never bare `pytest` or `python`.
- **GOLD-01**: Any phase that adds or modifies bridge operations must re-capture the golden master (`uat/capture_golden_master.py`) and add contract test coverage for the new behavior. Golden master = source of truth for "what OmniFocus actually does."

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Dumb bridge, smart Python | Bridge is a relay, not a brain. ALL validation, resolution, diff computation, and business logic lives in Python. Bridge receives pre-validated payloads and executes without interpretation. OmniJS freezes the UI and has sharp edges — minimize time there | Good -- bridge is ~400 lines of relay; ~14,000 lines of tested Python |
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
| Project-first parent resolution | When resolving a parent ID, try `get_project` before `get_task`. Project takes precedence. In practice IDs don't collide, but the order is intentional and deterministic | ✓ Good — v1.2 |
| Patch semantics via sentinel pattern | Edit models use UNSET sentinel to distinguish "not provided" from "null" (clear) from "value" (set). Pydantic can't distinguish omitted from None natively, sentinel solves the three-way | ✓ Good — clean API, no ambiguity |
| moveTo "key IS the position" design | Task movement expressed as `{"moveTo": {"ending": "parentId"}}` -- the key (beginning/ending/before/after) IS the position, the value IS the reference. Exactly one key allowed. Makes illegal states unrepresentable | ✓ Good — maps directly to OmniJS position API |
| Educational warnings in write responses | Write results include optional `warnings` array for no-ops with hints. Teaches agents patch semantics in-context | ✓ Good — LLMs learn from tool responses |
| Actions block grouping | edit_tasks separates idempotent field setters (top-level) from stateful operations (actions: tags/move/lifecycle). Clean semantic boundary | ✓ Good — extensible design |
| Diff-based tag computation | _compute_tag_diff in Python service, bridge receives only addTagIds/removeTagIds. Replaced 4-branch JS dispatch with ~4 lines | ✓ Good — simpler bridge, logic in Python |
| Lifecycle via Literal type | `lifecycle: Literal["complete", "drop"]` — Pydantic validates, no dedicated enum needed | ✓ Good — minimal surface area |
| Write-through guarantee | `@_ensures_write_through` decorator ensures writes block until SQLite confirms; reads never wait | ✓ Good — consistent read-after-write |
| "Add" verb for creation tools | Tool names use `add_*` (not `create_*`). "Add" is domain-native (OmniJS, task management UX), matches natural voice ("add a task"), and forms coherent verb system (add/edit/delete). Tool descriptions use natural language freely for discoverability. Write-side model names align: `AddTask*`, `EditTask*` | Decision locked pre-publish — rename `CreateTask*` → `AddTask*` pending |
| Service as package with DI | service.py → service/ with Resolver, DomainLogic, PayloadBuilder injected into orchestrator. Each module independently testable | ✓ Good — v1.2.1, enables targeted testing and clear boundaries |
| Method Object pattern for use cases | Every use case gets a `_VerbNounPipeline` class; created, executed, discarded in one call. Mutable self is fine | ✓ Good — v1.2.1, clean pipeline pattern |
| Golden master for contract testing | Capture RealBridge behavior via UAT, commit as fixtures, verify InMemoryBridge matches in CI. Source of truth = OmniFocus actual behavior | ✓ Good — v1.2.1, 43 scenarios, catches drift automatically |
| Structural import barrier for test doubles | Test doubles in tests/doubles/, production code in src/. Structural impossibility of importing test code in production | ✓ Good — v1.2.1, eliminates a class of mistakes |
| Patch[T]/PatchOrClear[T] type aliases | Make three-way semantics (unset/null/value) visible in annotations. Identical JSON schema, pure readability gain | ✓ Good — v1.2.1, self-documenting models |
| FastMCP v3 standalone package | Migrated from `mcp.server.fastmcp` to `fastmcp>=3.1.1` standalone. Native imports, `ctx.lifespan_context` shorthand, `Client(server)` test pattern | ✓ Good — v1.2.2, cleaner API, simpler tests |
| ToolLoggingMiddleware via cross-cutting concern | FastMCP Middleware base class with injected logger. Zero per-tool wiring needed — new tools get logging automatically | ✓ Good — v1.2.2, eliminated 6 manual log_tool_call() sites |
| Dual-handler logging (stderr + rotating file) | StreamHandler(stderr) for Claude Desktop visibility + 5MB RotatingFileHandler for persistent debugging. `__name__` convention across all 10 modules | ✓ Good — v1.2.2, observable in both contexts |
| ToolAnnotations stays at mcp.types | FastMCP doesn't re-export `ToolAnnotations`. Intentional residual `from mcp.types import ToolAnnotations` with TODO | — Pending — revisit when fastmcp re-exports |

---
*Last updated: 2026-03-27 after v1.2.3 milestone start — Repetition Rule Write Support*
