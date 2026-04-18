# OmniFocus Operator -- Updated Project Brief

## What We're Building

A Python MCP server that exposes OmniFocus (macOS task manager) as structured task infrastructure for AI agents. It powers a daily review workflow -- an AI-guided process for triaging inbox tasks, setting deadlines, estimating durations, extracting projects, prioritizing, and planning the day.

The user has ADHD and relies on OmniFocus as their external brain. This is executive function infrastructure: it needs to be reliable, simple, and easy to debug at 7:30am.

- **Name:** OmniFocus Operator
- **Slug:** `omnifocus-operator`
- **Language:** Python 3.12+ (async, Pydantic models, MCP SDK)
- **Repo:** https://github.com/HelloThisIsFlo/omnifocus-operator (public)

## Architecture

Three layers, each with a single responsibility:

```
MCP Server -> Service Layer -> Repository -> Bridge / SQLite
```

- **MCP Server**: Thin wrapper. Registers tools, calls service methods, returns results. No logic.
- **Service Layer**: Business logic and use cases. Filtering, semantic translation, search. Bridges "what OmniFocus reports" and "what makes sense to a human/agent."
- **Repository**: Data access via the Repository protocol. Three implementations:
  - **HybridRepository** (default): Reads from SQLite cache (~46ms), writes through OmniJS bridge. WAL-based freshness detection.
  - **BridgeRepository** (fallback via `OMNIFOCUS_REPOSITORY=bridge`): Reads and writes through OmniJS bridge. Mtime-based freshness on OmniFocus database.
  - **InMemoryRepository** (tests): In-memory data, no I/O.

### Two Read Paths

- **SQLite cache** (default): Direct read-only access to OmniFocus's SQLite database. ~46ms full snapshot. OmniFocus does not need to be running. Fresh connection per read, read-only mode.
- **OmniJS bridge** (fallback): File-based IPC to OmniFocus process. Slower (~2-3s), requires OmniFocus running. Reduced availability semantics (no `blocked`).

### Write Path

All writes go through the OmniJS bridge via the repository layer:

```
MCP -> Service (validate) -> Repository -> Bridge (execute) -> invalidate snapshot
```

After a successful write, the repository marks the snapshot as stale. The next read detects this via WAL mtime (hybrid) or database mtime (bridge) and loads fresh data.

### Two-Axis Status Model

OmniFocus's raw `taskStatus` is decomposed into two independent axes:

- **Urgency** (overdue / due_soon / none): How close is the deadline?
- **Availability** (available / blocked / completed / dropped): Can this task be acted on?

This replaces the original single-winner enums (`TaskStatus`, `ProjectStatus`) which conflated urgency with availability.

### IPC Protocol

File-based JSON request/response via OmniFocus's sandbox directory. Both sides use atomic writes (`.tmp` -> rename). The bridge script receives a dispatch string via URL scheme with `::::` delimiter.

### The Bridge Script

`operatorBridgeScript.js` runs inside OmniFocus via OmniJS. It's the source of truth for the data shape. Pydantic models are derived from what this script returns.

## Key Technical Decisions

- **JSON field names from OmniFocus are camelCase.** Pydantic models use snake_case with camelCase aliases.
- **`effective_*` fields are inherited values.** Always use `effective_*` variants for filtering.
- **Two-axis status model.** Decomposed from raw `taskStatus` at the repository/adapter level.
- **SQLite as primary read path.** 46ms vs multi-second bridge round-trip. No OmniFocus process needed.
- **Repository protocol (structural typing).** Swappable implementations without inheritance coupling.
- **Dict-based adapter mapping tables.** For enum transformations at the bridge boundary.
- **Fail-fast on unknown enum values.** Pydantic ValidationError with clear listing of valid values.
- **Error-serving degraded mode.** Fatal startup errors served as actionable MCP tool responses.
- **MCP tools are plural** (`add_tasks`, `edit_tasks`), taking and returning arrays.
- **Patch semantics for edits:** omit = no change, `null` = clear the field.
- **Workflow-agnostic server.** Expose primitives, not opinions. Workflow logic belongs in the agent.
- **Test data:** Tests use programmatic fixtures via InMemoryRepository. No pre-generated database dumps.

## Current State (after v1.1)

- ~14,144 LOC Python, ~215k LOC JS (bridge + deps), ~28k TS (tests)
- 313 pytest tests (~98% coverage), 26 Vitest tests
- Real OmniFocus database: ~2,400 tasks, ~363 projects, ~64 tags, ~79 folders
- 1 MCP tool (`list_all`)
- Two read paths: SQLite (default, ~46ms) and OmniJS bridge (fallback)

## API Surface (Target: 18 Tools)

### Reads
- `list_all()` -- full database snapshot (v1.0)
- `get_task(id)`, `get_project(id)`, `get_tag(id)` -- single item by ID (v1.2)
- `list_tasks(...)` -- tasks with filters and substring search (v1.3)
- `list_projects(...)` -- projects with filters (v1.3)
- `list_tags(...)`, `list_folders(...)` -- with status filter (v1.3)
- `list_perspectives()` -- all perspectives (v1.3)

### Writes
- `add_tasks([...])` -- task creation (v1.2)
- `edit_tasks([{ id, changes }])` -- task editing with patch semantics (v1.2)
- `add_projects([...])` -- project creation (v1.7)
- `edit_projects([{ id, changes }])` -- project editing (v1.7)

### UI
- `show_perspective(name)` -- switches OmniFocus UI perspective (v1.5)
- `get_current_perspective()` -- returns active perspective name (v1.5)
- `open_task(id)` -- opens task in OmniFocus UI (v1.5)

### Not in Scope
- Tag writes, folder writes, task reordering, undo/dry run, full-text indexing
- Utility methods (complete_task, drop_task, etc.) -- `edit_tasks`/`edit_projects` handle these

## Milestones

| # | Name | Tools After | Theme |
|---|------|-------------|-------|
| v1.0 | Foundation | 1 (`list_all`) | Architecture + real IPC pipeline |
| v1.1 | HUGE Performance Upgrade | 1 | SQLite read path + two-axis status model |
| v1.2 | Writes & Lookups | 6 | Get-by-ID + task write pipeline |
| v1.3 | Read Tools | 11 | SQL filtering, entity browsing |
| v1.4 | Response Shaping & Notes Append | 11 | Field projection, compact output (CSV or null-stripping), notes append |
| v1.4.1 | Task Properties & Subtree Retrieval | 11 | Presence flags (`hasNote`, `hasRepetition`, `hasAttachments`), auto-complete, parallel/sequential, `parent` filter |
| v1.5 | UI & Perspectives | 14 | Perspective switching, deep link, UI data path |
| v1.6 | Production Hardening | 14 | Retry, crash recovery, serial execution |
| v1.7 | Project Writes | 16 | Project creation, editing, review marking |

Each milestone has its own detailed spec file.

## Constraints

- **Language**: Python 3.12+ with async, Pydantic models, MCP SDK
- **Platform**: macOS only -- OmniFocus is a macOS application
- **Runtime deps**: `mcp>=1.26.0` only -- zero new deps (stdlib sqlite3)
- **IPC directory**: `~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/` (configurable for dev/test)
- **SQLite path**: `~/Library/Group Containers/34YW5A3IGP.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocusDatabase.db`
- **Field naming**: JSON from OmniFocus is camelCase; Pydantic uses snake_case with camelCase aliases

## Safety Rules

- **SAFE-01**: No automated test, CI, or agent touches `RealBridge`. All automated testing uses `InMemoryBridge` or `SimulatorBridge`. Bridge factory raises `RuntimeError` when `PYTEST_CURRENT_TEST` is set.
- **SAFE-02**: `RealBridge` interaction is manual UAT only. UAT scripts live in `uat/` and must NEVER be run by agents or CI.
