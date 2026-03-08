# Phase 15: Write Pipeline & Task Creation - Context

**Gathered:** 2026-03-07
**Status:** Ready for planning

<domain>
## Phase Boundary

Full write pipeline through bridge with `add_tasks` tool. Agents can create tasks in OmniFocus via MCP -> Service (validate) -> Repository -> Bridge (execute) -> invalidate snapshot. No task editing, no lifecycle changes, no project/tag writes.

</domain>

<decisions>
## Implementation Decisions

### Parent field format
- Single `parent` ID field on write model (not separate `project` + `parent_task_id`)
- Server resolves type: try `get_project` first, then `get_task`, error if neither found
- Project takes precedence naturally from lookup order
- `parent: null` or omitted = inbox (consistent with Phase 14 read model)
- Parent validated before bridge execution using existing get-by-ID repository methods

### Tag reference format
- Tags specified as names (case-insensitive matching)
- Tag IDs also accepted as fallback for disambiguation
- Resolution: try name match first; if exactly one match, use it; if multiple, error with IDs listed
- Non-existent tag name/ID = validation error (no auto-create)
- Ambiguous tag name error includes matching tag IDs so agent can retry with specific ID

### Tool API shape
- Tool named `add_tasks` (plural) -- array input, future-proofed for batch
- Single-item constraint enforced: array of exactly 1 item, validation error if more
- Returns per-item result array: `[{ success: true, id: "...", name: "..." }]`
- Detailed tool description listing all fields, types, and constraints inline
- Fields: name (required), parent, tags, due_date, defer_date, planned_date, flagged, estimated_minutes, note

### Write path routing
- HybridRepository gains a bridge reference (always required, not optional)
- Reads stay SQLite, writes go through bridge
- `TEMPORARY_simulate_write` replaced with real bridge calls + `_stale = True`
- InMemoryRepository gains in-memory write methods (append to internal list)
- Bridge operation renamed: `snapshot` -> `get_all` in bridge.js
- 2s WAL mtime timeout for freshness after writes (existing pattern, sufficient)

### Bridge response
- Bridge returns minimal `{ success, id, name }` for add_task command
- No input echo -- caller already knows what it sent

### Claude's Discretion
- Write model Pydantic class design (TaskCreateSpec or similar)
- Bridge.js `add_task` command implementation details
- Test structure and organization for write pipeline
- How to wire the bridge into HybridRepository constructor in the factory
- Validation error message formatting

</decisions>

<specifics>
## Specific Ideas

- Parent validation uses existing `get_project`/`get_task` repository methods -- no new queries needed, and the underlying implementation cost (SQLite single-row vs BridgeRepository full dump) is abstracted away
- Tag resolution should show parent path in ambiguity errors (e.g., "Work > Personal" vs "Work > Office") for clarity

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `HybridRepository._stale` + `_wait_for_fresh_data()`: WAL mtime freshness detection already implemented, just needs real write trigger
- `RealBridge.send_command(operation, params)`: generic command dispatch, ready for new operations
- `get_task`/`get_project`/`get_tag` repository methods: used for parent and tag validation
- `TEMPORARY_simulate_write()`: placeholder showing exactly where real write logic goes
- `OmniFocusBaseModel` with camelCase aliases: write model inherits this for consistent serialization

### Established Patterns
- Repository protocol with structural typing: add `add_task` method to protocol
- Service layer as thin delegation + validation: service validates, delegates to repository
- FastMCP tool registration with ToolAnnotations: `add_tasks` gets `readOnlyHint=False`
- Bridge request files with atomic writes (.tmp -> rename): write payloads use same IPC pattern

### Integration Points
- `repository/protocol.py`: extend protocol with `add_task` method
- `repository/hybrid.py`: add bridge reference, implement `add_task` via bridge
- `repository/in_memory.py`: implement in-memory `add_task`
- `service.py`: add `add_task` with validation logic (parent exists, tags exist)
- `server.py`: register `add_tasks` tool
- `bridge/bridge.js`: add `add_task` command handler, rename `snapshot` -> `get_all`
- `repository/factory.py`: wire bridge into HybridRepository constructor

</code_context>

<deferred>
## Deferred Ideas

None -- discussion stayed within phase scope

</deferred>

---

*Phase: 15-write-pipeline-task-creation*
*Context gathered: 2026-03-07*
