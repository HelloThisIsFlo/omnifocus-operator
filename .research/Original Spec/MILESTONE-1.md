# Milestone 1 — Foundation

## Goal

One MCP tool (`list_all`) works end-to-end. First with an in-process mock bridge, then with real file-based IPC. This milestone proves the architecture and establishes the infrastructure everything else builds on.

## What to Build

### Three-Layer Architecture

See project brief for the layer overview. In this milestone:

- **MCP Server** registers `list_all`, calls the service, returns the result.
- **Service Layer** is a passthrough — it exists to reserve the space for filtering logic in Milestone 2. Add a comment explaining why it's thin.
- **OmniFocus Repository** owns the snapshot and the bridge.

### Pydantic Models

Derived from the bridge script (`operatorBridgeScript.js`). Don't invent fields — match the dump. Use snake_case with camelCase aliases for serialization.

**Task** — all fields from the bridge dump: id, name, note, added, modified, active, effective_active, status (raw taskStatus — internal, excluded from serialization in Milestone 2), completed, completed_by_children, flagged, effective_flagged, sequential, due_date, defer_date, effective_due_date, effective_defer_date, completion_date, effective_completion_date, planned_date, effective_planned_date, drop_date, effective_drop_date, estimated_minutes, has_children, in_inbox, should_use_floating_time_zone, repetition_rule, project (ID), parent (ID), assigned_container (ID), tags (list of names).

**Project, Tag, Folder, Perspective** — same principle, all fields from the bridge dump.

### Bridge Interface + InMemoryBridge

The bridge interface: `send_command(operation, params) → response`. The InMemoryBridge returns test data from memory on `dump_all` commands. No IPC, no file I/O. Just Python. Injected at startup — no hardcoded mock references in the server or service layer.

### Database Snapshot

Loads once from the bridge, serves from memory. Subsequent calls return from the in-memory snapshot without calling the bridge again.

### File-Based IPC

Shared by SimulatorBridge and RealBridge. The flow:

1. Generate UUID request ID
2. Write request JSON to `requests/<uuid>.tmp`, rename to `requests/<uuid>.json` (atomic)
3. *(RealBridge only)* Trigger OmniFocus via URL scheme: `omnifocus:///omnijs-run?script=<url-encoded-js>&arg=<request_id>::::dump`
4. Poll `responses/<uuid>.json` until it appears or timeout (10s hardcoded — configurable later)
5. Read, parse, clean up

The IPC base directory (`~/Library/Containers/com.omnigroup.OmniFocus4/Data/Documents/omnifocus-operator/`) must be configurable for dev/test.

SimulatorBridge and RealBridge differ only in whether the URL scheme trigger fires. This can be one class with an optional trigger hook or two classes with a shared base — implementer's choice.

### Mock Simulator

A standalone Python script (not part of the server) that simulates what OmniFocus would do:

1. Watch `requests/` for new `.json` files
2. Parse the argument string (split on `::::`) to get request ID and operation
3. For `dump`: return test data (a representative OmniFocus database structure)
4. For `ping`: return a simple acknowledgment
5. Write response atomically to `responses/`

### Snapshot Freshness

On every read, `stat()` the `.ofocus` package directory for its mtime. If unchanged, serve from memory. If changed, ask the bridge for a fresh dump and replace the entire snapshot.

### Deduplication Lock

An asyncio Lock prevents multiple parallel MCP calls from each triggering their own dump. First caller acquires the lock and triggers the bridge. Others wait on the lock and use the freshly cached snapshot.

### Timeout Handling

If the response file doesn't appear within 10 seconds, raise a clear error: "OmniFocus did not respond within 10s — is it running?"

## Key Design Decisions

- **Atomic file writes everywhere.** Both sides write `.tmp` then rename to `.json`.
- **The bridge script is the schema.** Pydantic models derive from the bridge dump shape.
- **The mock simulator is intentionally simple.** No delay simulation, no failure modes. It proves the IPC mechanics work.
- **JS bootstrap is kept lean.** OmniFocus JS does the minimum (read data, serialize, write file). Python does the thinking.

## Key Acceptance Criteria

- Full pipeline works: MCP → Service → Repository → Snapshot → Bridge → structured Pydantic data back.
- Bridge is injected at startup. No code changes in MCP or service layer between InMemoryBridge and RealBridge.
- Snapshot serves from memory after first load (InMemoryBridge called once, not per-request).
- Mock simulator works end-to-end as a separate process.
- Mtime-based freshness: unchanged mtime = cached, changed mtime = fresh dump.
- Deduplication lock: multiple parallel calls share a single bridge dump.
- Timeout raises a clear, descriptive error when the mock simulator is not running.

## Tools After This Milestone

One: `list_all`.

