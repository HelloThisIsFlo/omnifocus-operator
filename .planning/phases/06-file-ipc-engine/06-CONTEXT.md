# Phase 6: File IPC Engine - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Async file-based IPC mechanism for exchanging commands and responses between the Python MCP server and an external process (OmniFocus via JXA script) via the filesystem. This phase builds the file IPC mechanics directly into `RealBridge` as the base class, with `_trigger_omnifocus()` as a no-op placeholder (Phase 8 fills in the URL scheme trigger). Phase 7's `SimulatorBridge` inherits from `RealBridge` and overrides the trigger to an explicit no-op.

</domain>

<decisions>
## Implementation Decisions

### File lifecycle & naming
- UUID-based filenames: `<pid>_<uuid>.request.json` and `<pid>_<uuid>.response.json`
- PID prefix enables per-instance isolation (multiple MCP server instances can share the same IPC directory safely)
- Response detection mechanism: Claude's discretion (polling vs filesystem watcher)
- Request file content format: Claude's discretion (dispatch string vs JSON envelope)
- Clean up both request and response files after successful round-trip
- On timeout, clean up the request file (late OmniFocus responses become orphans for next sweep)

### Directory structure & paths
- Flat directory structure: all request/response files in one directory
- IPC directory configurable via `OMNIFOCUS_IPC_DIR` env var (read by factory/wiring layer)
- Constructor also accepts explicit `ipc_dir` parameter (matches existing `OMNIFOCUS_BRIDGE` env var pattern)
- Default path: OmniFocus 4 group container `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/ipc/` (research agent should validate exact subpath)
- Auto-create IPC directory (mkdir -p) on initialization if it doesn't exist

### Error semantics & edge cases
- Startup sweep: PID-based ownership — check if owning PID is alive via `os.kill(pid, 0)`, only delete files from dead PIDs, skip files from alive PIDs
- No age-based fallback for sweep (PID check is sufficient; worst case is harmless orphaned files)
- Response validation depth: Claude's discretion (JSON parse + error key check vs raw pass-through)
- Timeout cleanup: delete request file when 10s timeout fires

### Module boundary & API surface
- Architecture: Template method pattern — `RealBridge` is the base class with all IPC mechanics
- `SimulatorBridge(RealBridge)` overrides `_trigger_omnifocus()` to no-op
- Phase 6 builds `RealBridge` with `_trigger_omnifocus()` as a no-op placeholder; Phase 8 fills in URL scheme trigger
- Granular API: `_write_request()` and `_wait_response()` as separate internal methods (RealBridge.send_command composes them with the trigger hook in between)
- Code location: `src/omnifocus_operator/bridge/` package (IPC is an implementation detail of the bridge, not a separate top-level package)

### Claude's Discretion
- Response detection mechanism (polling with `asyncio.to_thread` vs filesystem watcher)
- Request file content format (dispatch string only vs JSON envelope)
- Response validation depth (JSON + error key check vs raw pass-through)
- Exact polling interval if polling chosen
- Internal error types (reuse existing `BridgeError` hierarchy vs new IPC-specific errors)

</decisions>

<specifics>
## Specific Ideas

- "I always prefer composition over inheritance — it saves a lot of headaches down the line. But in this case inheritance models the domain correctly: SimulatorBridge IS a RealBridge that skips one step."
- The `34YW5A73WQ` string in the OmniFocus container path is the Omni Group's Apple Developer Team ID — standard across all macOS installs, not machine-specific.
- Multi-instance safety is critical: each Claude Code tab spawns its own MCP server process. PID-based file ownership prevents one instance's startup sweep from deleting another instance's in-flight requests.

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `Bridge` protocol (`bridge/_protocol.py`): `send_command(operation, params) -> response` — RealBridge will implement this directly
- `BridgeError` hierarchy (`bridge/_errors.py`): `BridgeError`, `BridgeTimeoutError`, `BridgeConnectionError`, `BridgeProtocolError` — all with `operation` + `cause` chaining. IPC timeout and protocol errors map naturally to these.
- `create_bridge()` factory (`bridge/_factory.py`): Currently has placeholder `NotImplementedError` for "real" type. Phase 6 replaces this with actual `RealBridge` instantiation.

### Established Patterns
- Non-blocking file I/O: `asyncio.to_thread(os.stat, path)` in `_mtime.py:42` — same pattern for `os.replace()`, `os.path.exists()`, file reads/writes
- Structural typing via `Protocol` classes (no ABC inheritance required for bridge interface)
- `asyncio.Lock` for concurrency control (`_repository.py:41`)
- Environment variable configuration: `OMNIFOCUS_BRIDGE` for bridge type selection

### Integration Points
- `RealBridge` will be instantiated by `create_bridge("real")` in `bridge/_factory.py`
- `SimulatorBridge` (Phase 7) will be instantiated by `create_bridge("simulator")`
- IPC directory path configuration connects to factory/wiring layer (env var + constructor param)

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 06-file-ipc-engine*
*Context gathered: 2026-03-02*
