# Project Research Summary

**Project:** OmniFocus Operator
**Domain:** Python MCP server with file-based IPC to macOS sandboxed application
**Researched:** 2026-03-01
**Confidence:** HIGH

## Executive Summary

OmniFocus Operator is a local MCP server that exposes OmniFocus as structured task infrastructure for AI agents. The core architectural bet — file-based IPC via OmniJS URL scheme, in-memory snapshot with mtime-based freshness, and a pluggable bridge interface — differentiates it from every existing competitor (all of which use synchronous AppleScript or JXA). The MCP ecosystem is well-documented (official Python SDK, stable spec), and the OmniFocus automation path is proven (URL scheme, OmniJS, sandbox file access). The risk is not in understanding the technologies but in the integration mechanics: atomic file writes, asyncio event loop discipline, and the fire-and-forget nature of the URL scheme trigger.

The recommended approach is to build bottom-up in a single foundation milestone: Pydantic models first (schema from bridge script), then bridge interface + InMemoryBridge, then repository with snapshot management, then thin service layer, then the MCP server with a single `list_all` tool, and finally the file IPC bridges (SimulatorBridge then RealBridge). This order means the architecture is validated end-to-end with InMemoryBridge before the most complex part (file IPC) is introduced. The stack is minimal: only the `mcp` package is needed at runtime — it brings Pydantic, anyio, and all async primitives as transitive dependencies.

The dominant risks are all in Milestone 1 and are well-understood: non-atomic file renames can corrupt IPC, blocking file I/O in async context can freeze the server, and the macOS URL scheme provides no delivery confirmation. All six critical pitfalls identified in research map to M1 and have concrete, low-effort preventions. There are no fundamental unknowns. The project can proceed to roadmap definition with high confidence.

## Key Findings

### Recommended Stack

The stack is deliberately minimal. The single runtime dependency is `mcp>=1.26.0` (the official Model Context Protocol Python SDK), which transitively provides Pydantic v2, pydantic-settings, and anyio. No additional runtime libraries are needed: use `anyio.open_file()` and `anyio.Path` for async file I/O instead of adding aiofiles. The project manager is `uv` — it replaces pip, poetry, pyenv, and virtualenv and is the community standard for Python in 2025/2026. Python 3.12 is the target (sweet spot of stability and compatibility).

**Core technologies:**
- `mcp>=1.26.0` (official SDK): MCP server framework via `FastMCP` — use `from mcp.server.fastmcp import FastMCP`, not the standalone `fastmcp` package
- Python 3.12: Runtime — sweet spot for stability; 3.11+ required, 3.12 has widest library compatibility
- Pydantic v2 (via mcp): Data models and validation — `alias_generator=to_camel` bridges camelCase bridge JSON to snake_case Python
- anyio (via mcp): Async primitives — use `anyio.open_file()` and `anyio.Path` for all file I/O
- `uv>=0.10`: Project manager — replaces the entire pip/poetry/pyenv toolchain

**Dev tools:** ruff (linter + formatter, replaces flake8/black/isort), mypy with pydantic plugin (strict mode), pytest + pytest-asyncio (asyncio_mode="auto") + pytest-timeout (10s global limit).

**What NOT to use:** standalone `fastmcp` package (v3.0), Poetry, Pydantic v1, flake8/black/isort separately, aiofiles (anyio covers this), watchdog (use watchfiles for simulator only), AppleScript/subprocess for OmniFocus triggering.

### Expected Features

The project has a clear five-milestone feature progression. The foundation (M1) proves the full pipeline with a single tool. See `FEATURES.md` for the full prioritization matrix.

**Must have (M1 table stakes — all P1):**
- `list_all` MCP tool returning full structured database — proves the entire pipeline end-to-end
- Three-layer architecture (MCP server / Service / Repository) — separation of concerns required before M2 filtering
- Bridge interface with pluggable implementations (InMemoryBridge, SimulatorBridge, RealBridge) — dependency injection is the testability mechanism
- Pydantic models derived from bridge script output shape — typed data contracts, schema source of truth is `operatorBridgeScript.js`
- Database snapshot with mtime-based freshness (`st_mtime_ns`) — load once, serve from memory, re-load only on change
- File-based IPC with atomic writes (`.tmp` then `os.replace()`) — the production OmniFocus communication path
- Mock simulator as standalone script — validates IPC mechanics without OmniFocus running
- RealBridge with URL scheme trigger (`omnifocus:///omnijs-run?...`) — actual production bridge
- Deduplication lock (`asyncio.Lock`) — prevents parallel dump storms
- Timeout handling (10s, actionable error message) — graceful failure when OmniFocus is unavailable
- Startup IPC directory cleanup — sweep orphaned request/response files on launch

**Should have (M1 polish / early M2):**
- Tool annotations (`readOnlyHint`, `idempotentHint`) — MCP spec metadata for client trust decisions
- Structured output schema on `list_all` — Pydantic-to-outputSchema integration
- Structured logging to stderr — required by MCP spec (never stdout)
- Cache pre-warming at startup — first request hits warm cache

**Defer (M2+):**
- Filtering and search (M2) — service layer intelligence, in-memory filtering
- Entity browsing / multiple read tools (M3) — `list_tasks`, `get_task`, etc.
- Perspective switching / field selection (M4) — UI interaction tools
- Write operations (M5) — task/project creation and editing
- MCP Resources — if agent context loading patterns emerge

**Never build:** MCP Prompts (workflow lives in the agent), WebSocket/SSE transport (stdio only, local server), AppleScript bridge (IPC is the differentiator), real-time file watching (mtime check on read is sufficient).

**Key differentiators vs 3 existing OmniFocus MCP servers:** All competitors (TypeScript/AppleScript or Rust/JXA) query OmniFocus on every tool call, have no documented testability, and use synchronous blocking bridges. This project's snapshot architecture, pluggable bridge, and async file IPC are genuine architectural advantages.

### Architecture Approach

The architecture is a strict four-layer stack: MCP Server (tool registration only, zero logic) → Service Layer (business logic, filtering; thin passthrough in M1) → Repository (snapshot ownership, freshness check, dedup lock) → Bridge Interface (pluggable: InMemory / Simulator / Real). The bridge is a Python `Protocol` class with a single method: `send_command(operation, params) -> response`. Dependency injection flows through FastMCP's lifespan context manager — no global singletons. The OmniJS bridge script running inside OmniFocus is the schema source of truth; models must match its output exactly.

**Major components:**
1. **MCP Server** (`server.py`) — `@mcp.tool()` decorators, lifespan context wiring, stdio transport. No business logic.
2. **Service Layer** (`service.py`) — Thin passthrough in M1. Will grow in M2 (filtering), M3 (entity browsing), M4 (UI ops). M4+ UI operations bypass the repository and call the bridge directly.
3. **Repository** (`repository.py`) — Owns `DatabaseSnapshot`. Manages mtime freshness check (`st_mtime_ns`), `asyncio.Lock` deduplication, and bridge invocation. Replaces snapshot atomically on cache miss.
4. **Bridge Interface** (`bridge/protocol.py`) — `typing.Protocol` with `send_command()`. Implemented by InMemoryBridge (tests), SimulatorBridge (IPC without URL trigger), and RealBridge (IPC + `open -g "omnifocus:///omnijs-run?..."` trigger).
5. **Pydantic Models** (`models/`) — Task, Project, Tag, Folder, Perspective, DatabaseSnapshot. `OmniFocusBaseModel` with `alias_generator=to_camel` and `populate_by_name=True`. Always serialize with `by_alias=True`.
6. **Mock Simulator** (`scripts/mock_simulator.py`) — Standalone process. Watches `requests/` directory, writes responses. Proves IPC without OmniFocus.
7. **OmniJS Bridge Script** (`bridge/operatorBridgeScript.js`) — Runs inside OmniFocus. Schema source of truth. Atomic file writes on the JS side.

**IPC dispatch protocol:** `<request_id>::::<operation>` (read ops) or `<request_id>::::<operation>::::<param>` (parameterized). Request ID must be UUID4 — validate before constructing dispatch string to prevent injection via `::::`.

**Key patterns:** FastMCP lifespan for DI, `asyncio.Lock` for dedup (double-check after acquiring), atomic rename via `os.replace()` (not `os.rename()`), polling at 200ms interval with `await asyncio.sleep()`.

### Critical Pitfalls

Full details in `PITFALLS.md`. All six critical pitfalls surface in M1.

1. **`os.rename()` instead of `os.replace()` for atomic writes** — `rename(2)` on macOS is not guaranteed atomic for overwrites. Use `os.replace()` everywhere. Grep for `os.rename` — must return zero results.
2. **Blocking asyncio event loop with synchronous file I/O** — `Path.exists()`, `Path.stat()`, `open()` in async context block the event loop and cause MCP protocol timeouts. Wrap all file ops in `asyncio.to_thread()`. Enable asyncio debug mode in tests.
3. **URL scheme trigger is fire-and-forget** — `open "omnifocus:///..."` returns exit 0 regardless of OmniFocus state. Write request file BEFORE firing the URL trigger. 10s timeout is the only detection mechanism. Error message must name OmniFocus explicitly.
4. **mtime sub-second precision misses rapid changes** — Use `st_mtime_ns` (integer nanoseconds, not float seconds). Accept same-second misses as a known limitation; document it. Add a force-refresh escape hatch if needed.
5. **Orphaned IPC artifacts after crashes** — On startup, sweep `requests/` and `responses/` directories. Delete all files. The server owns this directory; any files at startup are orphans.
6. **Bridge script performance freezes OmniFocus UI** — OmniJS runs on the main thread. For ~2,400 tasks, the dump takes measurable time. Log dump time; acceptable threshold is under 3 seconds. Keep the bridge script minimal — no filtering, no transformation, no date math in JS.

**Additional integration gotchas:** IPC directory must be created by the Python server at startup (subdirs `requests/` and `responses/`); must check that the directory exists (OmniFocus 3 uses a different bundle ID than OmniFocus 4); Pydantic `by_alias=True` is required on every `model_dump()` call for MCP output.

## Implications for Roadmap

Based on the combined research, the project maps naturally to five milestones. The existing discovery research (`.research/MILESTONE-1.md`) aligns with these implications. The build order within M1 is dictated by the dependency graph in `ARCHITECTURE.md`.

### Phase 1: Foundation — Full Pipeline with Single Tool

**Rationale:** All M2+ features depend on a working, testable pipeline. The architecture must be proven before filtering, browsing, or writes are added. IPC is the riskiest element; validate it end-to-end in M1. The build order within this phase is: Pydantic models → Bridge interface + InMemoryBridge → Repository → Service → MCP server → File IPC (SimulatorBridge + simulator script) → RealBridge.

**Delivers:** A working MCP server with `list_all` tool, connected to real OmniFocus, with full test coverage via InMemoryBridge. Snapshot caching operational. All six critical pitfalls addressed.

**Addresses:** All P1 features from `FEATURES.md` (13 features). Must-have: atomic IPC, dedup lock, mtime freshness, pluggable bridge, Pydantic models, startup cleanup, actionable timeout errors.

**Avoids:** All six critical pitfalls from `PITFALLS.md`. Use `os.replace()`, `asyncio.to_thread()` for file ops, `st_mtime_ns`, UUID4 validation, startup sweep, dump time logging.

**Research flag:** Standard patterns for FastMCP, Pydantic, asyncio. IPC mechanics are well-specified in project brief. No additional research phase needed for M1.

---

### Phase 2: Filtering and Search — Service Layer Intelligence

**Rationale:** The `list_all` output (~1.5MB JSON) will overwhelm LLM context windows in production use. Filtering is the primary UX improvement and the natural next layer once the pipeline is proven. The service layer exists as a passthrough in M1; M2 is when it becomes substantive.

**Delivers:** `list_tasks` tool with filter parameters (project, flagged, status, due range, tags). In-memory filtering against the snapshot — no new bridge operations needed.

**Uses:** Pydantic models and snapshot infrastructure from M1. Flat argument signature (Literal types, not dicts) per MCP best practices.

**Avoids:** Token overflow from large `list_all` output (flagged as M2 concern in `PITFALLS.md`).

**Research flag:** Standard Python filtering patterns. May need light research on MCP tool argument schema best practices if Literal types need refinement.

---

### Phase 3: Entity Browsing — Multiple Read Tools

**Rationale:** Once filtering works, agents need to navigate the entity graph: get a specific task by ID, list projects, browse tags, look up folders. These are additional read tools that use the same snapshot infrastructure.

**Delivers:** `get_task`, `list_projects`, `list_tags`, `list_folders` tools. Potentially `list_tasks_in_project`. All read-only, all from the in-memory snapshot.

**Research flag:** Standard patterns. No research phase needed.

---

### Phase 4: Perspective Operations — UI Interaction

**Rationale:** Switching perspectives in OmniFocus requires the bridge to send a different operation (not a data dump). This is the first time the Service layer calls the bridge directly, bypassing the repository. Architecture supports this (M4+ UI ops path documented in `ARCHITECTURE.md`).

**Delivers:** `show_perspective`, `list_perspectives`, `read_view` (current perspective tasks) tools.

**Uses:** Existing RealBridge with new operation types (`set_perspective`, `read_view`). Bridge script additions required.

**Research flag:** Needs research into available OmniJS APIs for perspective switching and view reading. The bridge script will need new operation handlers.

---

### Phase 5: Write Operations — Task and Project Management

**Rationale:** Writes are the most complex milestone: patch semantics, validation, bridge write commands, security review of request file payloads, confirmation patterns for destructive actions. Deferred last because M1-M4 validates the full read pipeline, and write requirements will be clearer after using the read-only server.

**Delivers:** `add_task`, `edit_task`, `complete_task`, `add_project` tools. Potentially batch operations.

**Avoids:** Request file content injection (validate all write payloads against strict schema; tag name vs ID fragility must be resolved before writes).

**Research flag:** Needs research on OmniJS write APIs (`flattenedTasks` modification, project creation), validation patterns for MCP write tools, and confirmation strategies for destructive actions.

---

### Phase Ordering Rationale

- M1 first because all subsequent phases depend on a working pipeline and testable infrastructure. There is no shortcut.
- M2 second because the primary UX problem (context overflow) surfaces immediately after M1 is used in real workflows.
- M3 third because entity browsing extends the read toolset without architectural changes.
- M4 fourth because UI interaction requires new bridge operations but no write semantics.
- M5 last because writes introduce new risk surface (validation, security, atomicity of OmniFocus edits) and should be built on a fully proven read foundation.

### Research Flags

**Needs research during planning:**
- **Phase 4 (Perspective Operations):** OmniJS APIs for perspective switching and reading the current view are not fully specified in the existing project brief. Research needed before implementation planning.
- **Phase 5 (Write Operations):** OmniJS write APIs, validation patterns, and confirmation UX for destructive actions need research. This is the only phase with genuine unknowns.

**Standard patterns (skip research phase):**
- **Phase 1 (Foundation):** All technologies well-documented. IPC mechanics fully specified in project brief. Build order derived from dependency graph.
- **Phase 2 (Filtering):** Standard Python filtering against Pydantic models. MCP tool argument patterns established.
- **Phase 3 (Entity Browsing):** Extension of Phase 2 patterns. No new infrastructure.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | All dependencies verified against official PyPI and GitHub sources with exact versions. Final dependency decision (anyio over aiofiles) is well-reasoned and correct. |
| Features | HIGH | Feature set derived from official MCP spec, competitor analysis (3 existing servers), and project brief. Competitor data is MEDIUM confidence (public repos) but the table-stakes features are independently derivable from the architecture. |
| Architecture | HIGH | Core patterns (FastMCP lifespan, Protocol bridge, snapshot/mtime, asyncio.Lock dedup) verified against official SDK examples and Omni Automation docs. Build order derived from dependency graph — no guesswork. |
| Pitfalls | HIGH | Six critical pitfalls each verified from at least two independent sources (CPython issue tracker, Omni forums, Python docs, academic references). Prevention strategies are concrete and testable. |

**Overall confidence: HIGH**

### Gaps to Address

- **`orjson` for large JSON parsing:** PITFALLS.md flags `orjson` as a performance optimization for JSON parsing at scale. Not needed for M1 (standard `json` module is fine), but worth tracking for M2+ if dump sizes exceed 5MB.
- **OmniJS perspective APIs (Phase 4):** The IPC dispatch protocol handles `set_perspective` and `read_view` at the protocol level, but the OmniJS implementation of these operations in the bridge script is not fully researched. Flag for Phase 4 planning.
- **OmniJS 3 vs OmniFocus 4 sandbox path:** The project brief targets OmniFocus 4. The IPC directory path (`com.omnigroup.OmniFocus4`) will not exist for OmniFocus 3 users. The server must fail gracefully with a clear error. This is an M1 implementation concern, not a gap in research.
- **Poll interval tuning:** Research recommends 200ms poll interval (not the 50ms in some code examples). The 200ms recommendation should be validated during M1 integration testing.

## Sources

### Primary (HIGH confidence)
- [MCP Python SDK (GitHub)](https://github.com/modelcontextprotocol/python-sdk) — FastMCP API, lifespan pattern, transitive dependencies
- [MCP Specification 2025-11-25](https://modelcontextprotocol.io/specification/2025-11-25) — tool capabilities, outputSchema, error handling, transport
- [MCP SDK pyproject.toml](https://raw.githubusercontent.com/modelcontextprotocol/python-sdk/main/pyproject.toml) — exact dependency pins (pydantic>=2.12.0, anyio>=4.5)
- [Omni Automation Script URLs](https://omni-automation.com/script-url/index.html) — `omnijs-run` URL scheme format
- [Pydantic ConfigDict (official)](https://docs.pydantic.dev/latest/api/config/) — alias_generator, populate_by_name
- [asyncio.Lock documentation](https://docs.python.org/3/library/asyncio-sync.html) — lock patterns, context manager requirement
- [Atomic writes: `os.replace` vs `os.rename`](https://github.com/python/cpython/issues/143909) — macOS atomic rename behavior
- [mtime comparison considered harmful](https://apenwarr.ca/log/20181113) — authoritative analysis of mtime pitfalls
- [OmniFocus batch task reading performance](https://discourse.omnigroup.com/t/reading-a-batch-of-tasks-taking-way-too-long/36691) — OmniJS performance characteristics
- [uv (GitHub)](https://github.com/astral-sh/uv) — version 0.10.7, project manager

### Secondary (MEDIUM confidence)
- [themotionmachine/OmniFocus-MCP](https://github.com/themotionmachine/OmniFocus-MCP) — competitor analysis (11 tools, AppleScript)
- [jqlts1/omnifocus-mcp-enhanced](https://github.com/jqlts1/omnifocus-mcp-enhanced) — competitor analysis (17 tools, AppleScript)
- [vitalyrodnenko/OmnifocusMCP](https://github.com/vitalyrodnenko/OmnifocusMCP) — competitor analysis (45 tools, JXA)
- [MCP Best Practices by Philipp Schmid](https://www.philschmid.de/mcp-best-practices) — flat tool arguments, naming conventions
- [FastMCP Dependencies](https://gofastmcp.com/python-sdk/fastmcp-server-dependencies) — DI pattern with Context
- [OmniFocus MCP Server discussion](https://discourse.omnigroup.com/t/omnifocus-mcp-server/71214) — community reports on bridge approaches

### Tertiary (LOW confidence)
- [MCP Server Best Practices 2026](https://www.cdata.com/blog/mcp-server-best-practices-2026) — general MCP guidance, validate during implementation
- [`rename(2)` non-atomic on macOS](http://www.weirdnet.nl/apple/rename.html) — older source, corroborated by CPython issue tracker

---
*Research completed: 2026-03-01*
*Ready for roadmap: yes*
