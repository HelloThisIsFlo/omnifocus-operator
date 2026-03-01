# OmniFocus Operator

## What This Is

A Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. It provides a clean, protocol-first interface for querying, creating, and managing tasks, projects, tags, and perspectives — enabling any AI agent to interact with OmniFocus without workflow-specific assumptions.

The server is deliberately workflow-agnostic: it exposes OmniFocus primitives in a convenient, well-structured way. Workflow logic (daily review, prioritization strategies, planning routines) lives in the agent, not the server.

## Core Value

Reliable, simple, debuggable access to OmniFocus data for AI agents — executive function infrastructure that works at 7:30am.

## Requirements

### Validated

<!-- Shipped and confirmed valuable. -->

(None yet — ship to validate)

### Active

<!-- Current scope: Milestone 1 — Foundation -->

- [ ] Three-layer architecture: MCP Server → Service Layer → OmniFocus Repository
- [ ] Bridge interface with pluggable implementations (InMemory, Simulator, Real)
- [ ] Full database snapshot loaded into memory from bridge dump
- [ ] File-based IPC with atomic writes (`.tmp` → rename)
- [ ] `list_all` MCP tool returning full structured database
- [ ] Pydantic models derived from bridge script output shape
- [ ] Snapshot freshness via `.ofocus` directory mtime check
- [ ] Deduplication lock preventing parallel dump storms
- [ ] Mock simulator as standalone Python script for IPC testing
- [ ] Timeout handling with clear error messages

### Out of Scope

<!-- Explicit boundaries. Includes reasoning to prevent re-adding. -->

- Workflow-specific logic (daily review, prioritization) — server is a general-purpose bridge; workflow lives in the agent
- Custom exception hierarchy — use standard Python exceptions, refine when real error patterns emerge
- Tag writes, folder writes, task reordering, undo/dry run — future milestones
- Mobile/iOS support — OmniFocus desktop only (macOS)
- TaskPaper output format — future milestone
- Production hardening (retry logic, crash recovery, idempotency) — future milestone

## Context

- The primary user has ADHD and relies on OmniFocus as an external brain. This drives the emphasis on reliability, simplicity, and debuggability — not cleverness.
- OmniFocus exposes a JavaScript automation API (OmniJS) that runs inside its process. Communication with external code requires IPC — a bridge script handles the OmniFocus side.
- A draft bridge script (`operatorBridgeScript.js`) exists in `.research/` as a **proven direction** for the IPC approach and data shape. The direction (file-based IPC, atomic writes, minimal JS, Python does the thinking) is fixed; implementation details (readability, naming, structure) can be improved.
- Real OmniFocus database: ~2,400 tasks, ~363 projects, ~64 tags, ~79 folders, ~1.5MB JSON. Full in-memory snapshot is feasible and fast.
- Five milestones planned (Foundation → Filtering → Entity Browsing → Perspectives → Writes), each with detailed specs in `.research/`. M1 is the current GSD scope.
- Target API surface: 18 tools across reads, UI interaction, and writes — built incrementally across milestones.

## Constraints

- **Language**: Python 3.11+ with async, Pydantic models, MCP SDK
- **Platform**: macOS only — OmniFocus is a macOS application
- **IPC directory**: `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/` (configurable for dev/test)
- **Schema source**: Bridge script output defines the data shape — Pydantic models derive from it, not the other way around
- **Field naming**: JSON from OmniFocus is camelCase; Pydantic uses snake_case with camelCase aliases for serialization

## Key Decisions

| Decision | Rationale | Outcome |
|----------|-----------|---------|
| Three-layer architecture (MCP → Service → Repository) | Clear separation of concerns; service layer is thin in M1 but reserves space for filtering in M2 | — Pending |
| File-based IPC via OmniFocus sandbox | Benchmarked as most efficient; works within OmniFocus sandbox constraints | — Pending |
| Full snapshot in memory, no partial invalidation | Database is small (~1.5MB); sub-millisecond filtering; simplicity over complexity | — Pending |
| Bridge script as direction, not literal artifact | Proven IPC approach and data shape; implementation can be improved for readability | — Pending |
| Workflow-agnostic server | Expose primitives, not opinions; workflow logic belongs in the agent | — Pending |
| MCP tools are plural (arrays in/out), bridge ops are singular | Batch-friendly API from the start; bridge handles one item at a time | — Pending |
| Patch semantics for edits (omit/null/value) | Critical for date fields: `null` = clear, omit = no change, value = set | — Pending |

---
*Last updated: 2026-03-01 after initialization*
