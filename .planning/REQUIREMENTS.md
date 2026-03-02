# Requirements: OmniFocus Operator

**Defined:** 2026-03-01
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

## v1 Requirements

Requirements for Milestone 1 — Foundation. Each maps to roadmap phases.

### Safety

- [x] **SAFE-01**: No automated test, CI pipeline, or agent execution touches the RealBridge — all automated testing uses InMemoryBridge or SimulatorBridge exclusively
- [ ] **SAFE-02**: RealBridge interaction is manual UAT only, performed by the user against their live OmniFocus database

### Architecture

- [x] **ARCH-01**: Server uses three-layer architecture (MCP Server → Service Layer → Repository) with clear separation of concerns
- [x] **ARCH-02**: Bridge implementation is injected at startup — no code changes in MCP or service layer to switch between InMemoryBridge and RealBridge
- [x] **ARCH-03**: Project uses `uv` with `src/` layout and Python 3.12

### Data Models

- [x] **MODL-01**: Task model includes all fields from bridge script dump with snake_case names and camelCase aliases
- [x] **MODL-02**: Project model includes all fields from bridge script dump
- [x] **MODL-03**: Tag model includes all fields from bridge script dump
- [x] **MODL-04**: Folder model includes all fields from bridge script dump
- [x] **MODL-05**: Perspective model includes id, name, and builtin flag
- [x] **MODL-06**: DatabaseSnapshot model aggregates all entity collections
- [x] **MODL-07**: All models share a base config with camelCase alias generation and `populate_by_name`

### Bridge

- [x] **BRDG-01**: Bridge protocol defines `send_command(operation, params) → response`
- [x] **BRDG-02**: InMemoryBridge returns test data from memory for unit testing
- [x] **BRDG-03**: SimulatorBridge uses file-based IPC without URL scheme trigger
- [x] **BRDG-04**: RealBridge uses file-based IPC with `omnifocus:///omnijs-run` URL scheme trigger

### Snapshot

- [x] **SNAP-01**: Repository loads full database snapshot from bridge dump into memory
- [x] **SNAP-02**: Subsequent reads serve from in-memory snapshot without calling the bridge again
- [x] **SNAP-03**: Repository checks `.ofocus` directory mtime (`st_mtime_ns`) on each read — unchanged mtime serves cached data
- [x] **SNAP-04**: Changed mtime triggers fresh dump replacing the entire snapshot atomically
- [x] **SNAP-05**: `asyncio.Lock` prevents parallel MCP calls from each triggering separate dumps
- [x] **SNAP-06**: Cache is pre-warmed at startup so the first request hits warm data

### File IPC

- [x] **IPC-01**: File writes use atomic pattern (write `.tmp`, then `os.replace()` to final path)
- [x] **IPC-02**: All file I/O in async context is non-blocking (via `asyncio.to_thread()` or anyio)
- [x] **IPC-03**: Dispatch protocol uses `<uuid>::::<operation>` format with UUID4 validation
- [x] **IPC-04**: IPC base directory defaults to OmniFocus 4 sandbox path but is configurable for dev/test
- [x] **IPC-05**: Response timeout at 10 seconds with actionable error message naming OmniFocus
- [x] **IPC-06**: Server sweeps orphaned request/response files from IPC directory on startup

### MCP Tool

- [x] **TOOL-01**: `list_all` tool returns full structured database as typed Pydantic data
- [x] **TOOL-02**: Tool includes MCP annotations (`readOnlyHint`, `idempotentHint`)
- [x] **TOOL-03**: Tool exposes structured output schema from Pydantic models
- [x] **TOOL-04**: Server logs to stderr only (MCP spec requirement — never stdout)

### Testing & Dev

- [x] **TEST-01**: Mock simulator is a standalone Python script that watches for requests and writes test responses
- [ ] **TEST-02**: Full pipeline is testable via InMemoryBridge with no OmniFocus dependency
- [ ] **TEST-03**: pytest + pytest-asyncio test suite with tests for each layer

## v2 Requirements

Deferred to future milestones. Tracked but not in current roadmap.

### Filtering & Search (Milestone 2)

- **FILT-01**: `list_tasks` tool with field-level filters (inbox, flagged, project, tags, dates)
- **FILT-02**: Semantic status decomposition — availability and urgency axes from raw taskStatus
- **FILT-03**: Fuzzy text search across task names and notes

### Entity Browsing (Milestone 3)

- **ENTY-01**: `list_projects`, `list_tags`, `list_folders`, `list_perspectives` tools
- **ENTY-02**: Single-item lookups (`get_task`, `get_project`, `get_tag`)
- **ENTY-03**: Count tools (`count_tasks`, `count_projects`)

### Perspectives & Field Selection (Milestone 4)

- **PERSP-01**: `show_perspective` and `get_current_perspective` UI tools
- **PERSP-02**: `list_tasks(current_perspective_only)` reads live from OmniFocus UI
- **PERSP-03**: Field projection (`fields` parameter) on all read tools

### Writes (Milestone 5)

- **WRIT-01**: `add_tasks`, `delete_tasks`, `edit_tasks` with patch semantics
- **WRIT-02**: `add_projects`, `edit_projects` with patch semantics
- **WRIT-03**: Snapshot invalidation after writes (lazy refresh)

## Out of Scope

| Feature | Reason |
|---------|--------|
| Workflow-specific logic (daily review, prioritization) | Server is a general-purpose bridge; workflow lives in the agent |
| Custom exception hierarchy | Use standard Python exceptions; refine when real error patterns emerge |
| Tag writes, folder writes, task reordering | Future milestones beyond M5 |
| Mobile/iOS support | OmniFocus desktop only (macOS) |
| TaskPaper output format | Future milestone — alternative serialization for token reduction |
| Production hardening (retry, crash recovery, idempotency) | Future milestone |
| MCP Prompts | Workflow-specific; server exposes primitives only |
| WebSocket/SSE transport | stdio only — local server, not networked |
| AppleScript/osascript bridge | File-based IPC is the differentiator |
| Real-time file watching for snapshot | mtime check on read is sufficient |
| Project deletion | Always manual in OmniFocus |

## Traceability

| Requirement | Phase | Status |
|-------------|-------|--------|
| SAFE-01 | Phase 8 | Complete |
| SAFE-02 | Phase 8 | Pending |
| ARCH-01 | Phase 5 | Complete |
| ARCH-02 | Phase 5 | Complete |
| ARCH-03 | Phase 1 | Complete |
| MODL-01 | Phase 2 | Complete |
| MODL-02 | Phase 2 | Complete |
| MODL-03 | Phase 2 | Complete |
| MODL-04 | Phase 2 | Complete |
| MODL-05 | Phase 2 | Complete |
| MODL-06 | Phase 2 | Complete |
| MODL-07 | Phase 2 | Complete |
| BRDG-01 | Phase 3 | Complete |
| BRDG-02 | Phase 3 | Complete |
| BRDG-03 | Phase 7 | Complete |
| BRDG-04 | Phase 8 | Complete |
| SNAP-01 | Phase 4 | Complete |
| SNAP-02 | Phase 4 | Complete |
| SNAP-03 | Phase 4 | Complete |
| SNAP-04 | Phase 4 | Complete |
| SNAP-05 | Phase 4 | Complete |
| SNAP-06 | Phase 4 | Complete |
| IPC-01 | Phase 6 | Complete |
| IPC-02 | Phase 6 | Complete |
| IPC-03 | Phase 6 | Complete |
| IPC-04 | Phase 6 | Complete |
| IPC-05 | Phase 6 | Complete |
| IPC-06 | Phase 6 | Complete |
| TOOL-01 | Phase 5 | Complete |
| TOOL-02 | Phase 5 | Complete |
| TOOL-03 | Phase 5 | Complete |
| TOOL-04 | Phase 5 | Complete |
| TEST-01 | Phase 7 | Complete |
| TEST-02 | Phase 8 | Pending |
| TEST-03 | Phase 8 | Pending |

**Coverage:**
- v1 requirements: 35 total
- Mapped to phases: 35
- Unmapped: 0

---
*Requirements defined: 2026-03-01*
*Last updated: 2026-03-01 after roadmap creation*
