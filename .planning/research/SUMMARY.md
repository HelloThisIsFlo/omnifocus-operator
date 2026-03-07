# Project Research Summary

**Project:** OmniFocus Operator v1.2 -- Writes & Lookups
**Domain:** MCP server write pipeline for local macOS task management app
**Researched:** 2026-03-07
**Confidence:** HIGH

## Executive Summary

v1.2 adds write capabilities (task creation, editing, lifecycle) and get-by-ID lookups to an existing read-only MCP server. The critical insight: **zero new dependencies are needed.** The existing stack (Python 3.12, Pydantic v2 via MCP SDK, OmniJS bridge IPC) handles everything. Writes flow through the OmniJS bridge exclusively -- SQLite remains read-only because OmniFocus owns its database. Get-by-ID is implemented as a filter on the already-cached snapshot, not as new bridge commands (sub-ms vs multi-second).

The recommended approach is a 4-phase incremental build: get-by-ID (warmup, zero risk) -> add_tasks (proves full write pipeline) -> edit_tasks fields (adds patch semantics) -> edit_tasks lifecycle (needs research spike). Each phase proves one new capability before the next adds complexity. The write pipeline follows asymmetric read/write paths -- reads from SQLite cache, writes through OmniJS bridge, with WAL-based invalidation connecting them.

Key risks center on OmniJS constraints: no transactions (partial writes are permanent), 1ms/task/property-access cost (never iterate in bridge.js), and unverified APIs for task movement and lifecycle edge cases. Mitigation: validate everything in Python before touching OmniJS, start with single-item arrays (no batch), and run research spikes before implementing movement and lifecycle operations.

## Key Findings

### Recommended Stack

No new dependencies. The entire v1.2 scope is covered by what's already installed.

**Core technologies (all existing):**
- **Python 3.12 + Pydantic v2** -- new input models (AddTaskRequest, EditTaskChanges, WriteResult) use standard Pydantic validators for patch semantics, mutual exclusivity, ISO8601 dates
- **OmniJS bridge (bridge.js)** -- new `add_task` and `edit_task` operation handlers using request file payloads
- **SQLite (stdlib)** -- read-only path unchanged; get-by-ID can use single-row queries in HybridRepository
- **MCP SDK (FastMCP)** -- 5 new tool registrations, same patterns as existing tools

**Key technical decisions:**
- HybridRepository gains an optional bridge dependency (constructor injection) for writes
- `TEMPORARY_simulate_write()` replaced with real `_mark_stale()` using same WAL pattern
- Patch semantics via Pydantic optional fields + None sentinel (no jsonschema/json-patch)
- Get-by-ID implemented as snapshot filter, not new bridge commands

### Expected Features

**Must have (table stakes):**
- Get-by-ID for tasks, projects, tags -- agents need single-entity inspection after writes
- Task creation (add_tasks) -- core write primitive, project/inbox/subtask placement
- Task field editing (edit_tasks) -- name, dates, flags, notes, estimated_minutes
- Tag management -- three modes: replace (tags), add (add_tags), remove (remove_tags)
- Task completion and dropping -- most common lifecycle operations
- Snapshot invalidation after writes -- stale reads after mutations break agent trust
- Service-layer validation with clear error messages -- catch errors in Python, not OmniJS
- Batch-shaped API (array in/out) -- even if single-item initially, forward-compatible shape
- Patch semantics (omit/null/value) -- industry standard for partial updates

**Should have (differentiators):**
- Task reactivation (markIncomplete) -- undo wrong completion
- Three tag edit modes -- avoids read-then-write for tag changes
- Move to inbox (project: null) -- distinct from "leave project unchanged"
- Rich LLM-optimized tool descriptions
- Per-item result reporting

**Defer (v1.4+):**
- delete_tasks (drop covers most intent)
- Project/tag/folder writes (unverified APIs)
- True batch execution (no transactions = partial failure risk)
- Retry/resilience (v1.5)
- Dry run / preview mode

### Architecture Approach

Asymmetric read/write paths. Reads stay on SQLite cache (46ms). Writes go through OmniJS bridge, then mark the snapshot stale for lazy invalidation. Get-by-ID filters the cached snapshot (sub-ms). Validation lives in the service layer; the bridge receives pre-validated payloads ("dumb bridge, smart Python").

**Major components (modified/new):**
1. **MCP tools (server.py)** -- 5 new tool registrations (get_task, get_project, get_tag, add_tasks, edit_tasks)
2. **OperatorService (service.py)** -- validation against snapshot, tag name-to-ID resolution, write delegation
3. **Repository protocol** -- extended with add_tasks(), edit_tasks() signatures; all 3 implementations updated
4. **HybridRepository** -- gains optional bridge dependency for writes, replaces TEMPORARY_simulate_write
5. **bridge.js** -- new add_task/edit_task handlers with request file payloads and hasOwnProperty patch semantics

**Key patterns:**
- Field name translation (snake_case -> camelCase) at repository boundary via dict mapping
- Tag name resolution in Python (microsecond lookup from cached snapshot vs 2.8s OmniJS iteration)
- Per-item WriteResult for batch-shaped operations
- Optional bridge in HybridRepository (None = read-only mode for tests)

### Critical Pitfalls

1. **Snapshot invalidation race** -- OmniJS write completes before SQLite flush. Prevention: return bridge response as source of truth, don't re-read to confirm. WAL polling handles next-read freshness.
2. **No transactions in OmniJS** -- partial writes are permanent. Prevention: validate everything in Python first, enforce single-item arrays in v1.2.
3. **`assignedContainer` always null** -- task movement API is unverified. Prevention: research spike before implementing movement; test `moveTasks()`, `containingProject` assignment, and `task.parent` in OmniJS.
4. **Repeating task completion spawns new ID** -- agent loses reference to successor. Prevention: check `repetitionRule` before completion, return successor_id in response.
5. **`markIncomplete()` silent no-op on dropped tasks** -- agent thinks reactivation succeeded. Prevention: service-layer pre-check of task availability, explicit error for dropped tasks.
6. **Tag name ambiguity** -- OmniFocus allows duplicate tag names. Prevention: service-layer duplicate check, error with disambiguation info.
7. **`flattenedTasks` iteration in bridge.js** -- 2.8s frozen UI. Prevention: use `Task.byIdentifier(id)` for O(1) lookups, never iterate.

## Implications for Roadmap

### Phase 1: Get-by-ID Tools
**Rationale:** Zero write risk, validates new service methods, enables write verification in later phases
**Delivers:** get_task, get_project, get_tag MCP tools
**Addresses:** Single-entity inspection (table stakes feature)
**Avoids:** flattenedTasks scan pitfall (use byIdentifier or snapshot filter)
**Complexity:** Low. Pure Python filtering on cached snapshot. No bridge changes, no protocol changes, no new models.

### Phase 2: Write Pipeline + add_tasks
**Rationale:** Establishes the entire write pattern. Creation is simpler than editing (no patch semantics). Proves the full stack end-to-end.
**Delivers:** Pydantic write models, repository protocol extension, HybridRepository bridge injection, bridge add_task handler, add_tasks MCP tool, snapshot invalidation (_mark_stale replacing TEMPORARY_simulate_write)
**Addresses:** Task creation, service validation, tag name resolution, snapshot invalidation (all table stakes)
**Avoids:** No-transaction pitfall (single-item constraint), snapshot race (return bridge response), tag ambiguity (duplicate check)
**Complexity:** Medium. Highest-risk phase -- first real write through the full stack.

### Phase 3: edit_tasks -- Fields, Tags, Movement
**Rationale:** Field editing reuses the proven write pipeline. Movement needs a research spike at phase start.
**Delivers:** edit_tasks MCP tool for name, note, dates, flags, estimated_minutes, tags (3 modes), project/parent movement
**Addresses:** Task editing, tag management, task movement (table stakes + differentiators)
**Avoids:** assignedContainer pitfall (research spike first), tag mode conflicts (mutual exclusion validation)
**Complexity:** Medium-high. Patch semantics + tag modes + movement = most fields to handle.

### Phase 4: edit_tasks -- Lifecycle Changes
**Rationale:** Lifecycle operations have open questions (repeating tasks, drop permanence) requiring a research spike before implementation
**Delivers:** complete, drop, reactivate via edit_tasks
**Addresses:** Task completion and dropping (table stakes), reactivation (differentiator)
**Avoids:** markIncomplete no-op pitfall (pre-check availability), repeating task ID pitfall (return successor_id)
**Complexity:** Medium. Fewer fields than Phase 3, but requires research spike for OmniJS lifecycle behavior.

### Phase Ordering Rationale

- **Dependency chain:** Get-by-ID (Phase 1) enables write verification. add_tasks (Phase 2) proves the full write pipeline. edit_tasks fields (Phase 3) reuses that pipeline with patch semantics. Lifecycle (Phase 4) adds OmniJS quirks on top.
- **Risk escalation:** Each phase adds one new capability. Phase 1 is pure Python. Phase 2 is first bridge write. Phase 3 adds patch semantics. Phase 4 adds lifecycle edge cases.
- **Research spikes isolated:** Movement API research gates only Phase 3. Lifecycle research gates only Phase 4. Neither blocks earlier phases.

### Research Flags

**Phases needing deeper research during planning:**
- **Phase 3 (movement):** Task movement API is unverified. Must empirically test `moveTasks()`, `containingProject` setter, and `task.parent` assignment before implementing.
- **Phase 4 (lifecycle):** `markComplete()` on repeating tasks, `drop(false)` vs `drop(true)`, `markIncomplete()` on dropped tasks -- all need OmniJS verification.

**Phases with standard patterns (skip research-phase):**
- **Phase 1 (get-by-ID):** Snapshot filtering is trivial. Well-understood pattern.
- **Phase 2 (add_tasks):** Bridge IPC, Pydantic models, service validation -- all established patterns. Only novelty is wiring them for writes.

## Confidence Assessment

| Area | Confidence | Notes |
|------|------------|-------|
| Stack | HIGH | Zero new deps. All technologies already in use and proven in v1.0-v1.1. |
| Features | HIGH | Spec is detailed (MILESTONE-v1.2.md). Feature scope well-defined with clear defer decisions. |
| Architecture | HIGH | Extends existing patterns. Asymmetric read/write is the only viable approach given OmniFocus owns SQLite. |
| Pitfalls | HIGH | BRIDGE-SPEC is empirically verified against live OmniFocus v4.8.8. Pitfalls are concrete, not speculative. |

**Overall confidence:** HIGH

### Gaps to Address

- **Task movement API:** `assignedContainer` confirmed broken. `containingProject` setter and `moveTasks()` unverified. Resolve via research spike at Phase 3 start.
- **Repeating task completion semantics:** Successor ID behavior, `drop(false)` vs `drop(true)` -- needs empirical verification. Resolve via research spike at Phase 4 start.
- **`markIncomplete()` on dropped tasks:** Confirmed no-op but no recovery strategy defined. Decide during Phase 4: error out or attempt `document.undo()`.
- **Partial failure strategy:** Moot with single-item constraint in v1.2 but needs a decision before batch is enabled.
- **Tag name ambiguity UX:** Accept both names and IDs? Qualified paths like "Work/Meeting"? Decide during Phase 2 implementation.

## Sources

### Primary (HIGH confidence)
- `.research/deep-dives/omnifocus-api-ground-truth/BRIDGE-SPEC.md` -- empirical spec from 27 audit scripts against OmniFocus v4.8.8
- `.research/updated-spec/MILESTONE-v1.2.md` -- detailed v1.2 spec with field tables and open questions
- Existing codebase (v1.1) -- direct inspection of bridge.js, hybrid.py, bridge.py, protocol.py, service.py, server.py

### Secondary (MEDIUM confidence)
- [OmniFocus Tasks - Omni Automation](https://www.omni-automation.com/omnifocus/task.html) -- OmniJS task API reference
- [MCP Tools Specification](https://modelcontextprotocol.io/specification/2025-06-18/server/tools) -- official MCP tools spec
- [54 Patterns for Building Better MCP Tools](https://www.arcade.dev/blog/mcp-tool-patterns) -- MCP tool design patterns

---
*Research completed: 2026-03-07*
*Ready for roadmap: yes*
