# Phase 7: SimulatorBridge and Mock Simulator - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

A file-based IPC bridge (SimulatorBridge) and companion mock simulator script that prove the full IPC pipeline works end-to-end without OmniFocus running. SimulatorBridge sends commands via file IPC; the simulator watches for request files and writes response files. The MCP server can be started with SimulatorBridge and list_all returns simulator-produced data.

</domain>

<decisions>
## Implementation Decisions

### Simulator data fidelity
- Realistic data covering common OmniFocus patterns: inbox tasks, tasks in projects, flagged items, some with due dates, a few completed, tags assigned, nested folders
- Representative of a typical OmniFocus power user's database
- Data is static between requests (same snapshot every time dump_all is called)

### Simulator invocation & lifecycle
- Runs forever until Ctrl+C (daemon-style, matching how real OmniFocus behaves)
- Started as a subprocess in pytest integration tests (pytest fixture manages start/stop)
- Verbose logging to stderr by default (each request/response cycle logged)
- Prints config summary to stderr on startup (IPC dir, fail mode, delay, etc.)

### Error simulation modes
- Supports configurable failure modes via CLI flags:
  - `--fail-mode timeout` — receives request but never writes response (tests 10s timeout path)
  - `--fail-mode error` — writes `{"success": false, "error": "simulated error"}` response
  - `--fail-mode malformed` — writes invalid JSON to response file
- `--fail-after N` — first N requests succeed, then failure mode activates
- `--delay <seconds>` — delays all responses by N seconds (independent of fail mode; tests near-timeout behavior)

### Bridge architecture
- SimulatorBridge subclasses RealBridge with a permanently locked no-op `_trigger_omnifocus()`
- Lives in its own file: `bridge/_simulator.py` (follows existing pattern: `_in_memory.py`, `_real.py`)
- Uses ConstantMtimeSource (data is static; cache invalidation already tested in Phase 4)
- Factory wiring: `create_bridge("simulator")` returns SimulatorBridge instance

### Claude's Discretion
- Data source format (hardcoded dict vs JSON fixture file)
- Exact simulator entry point pattern (module `__main__` vs script)
- Simulator polling interval for watching request files
- Integration test fixture implementation details (subprocess management, readiness detection)

</decisions>

<specifics>
## Specific Ideas

- Simulator should feel like a proper dev tool — config summary on startup, per-request logging, clear shutdown
- Error simulation covers the full error surface so integration tests can validate all error paths cross-process, not just via unit mocks

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RealBridge` (`bridge/_real.py`): Full IPC mechanics — atomic file writes, response polling, timeout, cleanup. SimulatorBridge subclasses this directly.
- `sweep_orphaned_files()` (`bridge/_real.py`): PID-based orphan cleanup. SimulatorBridge inherits `ipc_dir` property so the lifespan sweep already works.
- `Bridge` protocol (`bridge/_protocol.py`): Structural typing interface. SimulatorBridge satisfies it via RealBridge inheritance.
- `BridgeTimeoutError`, `BridgeProtocolError` (`bridge/_errors.py`): Error types that SimulatorBridge + error simulation will exercise.
- `InMemoryBridge` sample data pattern (`bridge/_factory.py`): Reference for realistic data structure shape.

### Established Patterns
- Atomic file writes: `.tmp` + `os.replace()` — simulator must follow same pattern for response files
- Async file I/O via `asyncio.to_thread()` — simulator is a standalone sync process (no async needed)
- IPC file naming: `<pid>_<uuid>.(request|response).json` — simulator watches for `.request.json` files and writes `.response.json`
- Factory pattern: `create_bridge(bridge_type)` switch — "simulator" case ready to be wired

### Integration Points
- `bridge/_factory.py`: Wire `"simulator"` case to return `SimulatorBridge(ipc_dir=...)` with `OMNIFOCUS_IPC_DIR` env var support
- `server/_server.py` lifespan: Currently raises `NotImplementedError` for non-inmemory bridge types. Needs `"simulator"` case with `ConstantMtimeSource`
- `bridge/__init__.py`: Export `SimulatorBridge` in `__all__`

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 07-simulatorbridge-and-mock-simulator*
*Context gathered: 2026-03-02*
