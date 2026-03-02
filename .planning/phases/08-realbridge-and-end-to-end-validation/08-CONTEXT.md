# Phase 8: RealBridge and End-to-End Validation - Context

**Gathered:** 2026-03-02
**Status:** Ready for planning

<domain>
## Phase Boundary

Production bridge that communicates with live OmniFocus via `omnifocus:///omnijs-run` URL scheme trigger. Complete test suite covering all layers (models, bridge, repository, service, MCP server). Safety guardrails enforced to prevent any automated code from touching the real database. Manual UAT framework established for human-only testing against live OmniFocus.

</domain>

<decisions>
## Implementation Decisions

### Safety guardrail enforcement
- CI check + runtime guard — belt and suspenders approach
- Runtime guard at **factory level**: `create_bridge("real")` refuses when `PYTEST_CURRENT_TEST` is set, raising a clear error directing to `inmemory` or `simulator`
- CI step that greps test files for RealBridge usage and fails the build if found
- Update CLAUDE.md with explicit SAFE-01/02 rules so AI agents get the warning upfront
- Both pytest `testpaths` config and CI pipeline exclude the `uat/` directory

### Manual UAT experience
- Dedicated `uat/` folder at project root (alongside `src/` and `tests/`)
- UAT scripts are Python scripts run via `uv run python uat/<script>.py` — uses the project's own code (RealBridge, models)
- Concept document (`uat/README.md`) explaining the UAT folder philosophy: human-only execution, future vision for sandboxed test data setup/teardown, safety posture for write operations in future milestones
- For Phase 8: read-only UAT script that connects to real OmniFocus, calls `dump_all`, and pretty-prints/validates the response
- Future milestones will add UAT scripts that set up sandboxed test data, prompt the user for verification, perform operations, and clean up — with explicit confirmation before any write action
- Excluded from pytest discovery AND CI pipeline (double protection, consistent with SAFE-01/02)
- Agents must NEVER run UAT scripts — human-only, enforced by convention and CI exclusion

### Error experience
- Error messages are **agent-optimized**: include structured context the AI agent can act on (operation name, timeout duration, likely cause, suggested next step)
- Example: "OmniFocus did not respond within 10.0s for dump_all. Likely cause: OmniFocus not running. Suggestion: ask user to open OmniFocus and retry."
- **Specific error types** for different failure modes: timeout (no response), protocol error (bad response format), connection error (URL scheme failed). Gives the agent maximum diagnostic information
- **Fail fast, no retry**: 10s timeout then immediate error. Retry logic belongs in the agent, not in the bridge. Keeps the bridge simple and predictable
- The existing error hierarchy (`BridgeTimeoutError`, `BridgeProtocolError`, `BridgeConnectionError`) already supports this — enhance messages to be agent-friendly

### Test coverage scope
- **Gap audit + fill**: audit existing tests across all layers, identify missing coverage, fill gaps. Builds on existing work, avoids redundant tests
- TEST-02 (full pipeline via InMemoryBridge): Claude determines whether a single E2E smoke test or additional layer integration tests are needed based on existing coverage
- TEST-03 (tests for each layer): verify each layer has tests, fill any discovered gaps
- SAFE-01 enforcement meta-test: Claude decides whether to add a pytest meta-test or CI-only grep script based on existing patterns

### Claude's Discretion
- Exact CI implementation approach for the safety grep check (standalone script vs pytest conftest hook)
- Whether the SAFE-01 enforcement is a meta-test in pytest or a CI-only script
- E2E pipeline test granularity (single smoke test vs smoke + layer integration tests)
- URL scheme trigger implementation details (`subprocess.run(["open", url])` vs alternatives)
- FileMtimeSource path configuration for the "real" bridge type in app_lifespan
- Error message exact wording and structure

</decisions>

<specifics>
## Specific Ideas

- UAT folder should grow into a full UAT framework across milestones — Phase 8 establishes the pattern, future write-capable phases add sandboxed scenarios with setup/teardown
- UAT concept doc captures the philosophy so future phases don't need re-explanation: "This folder contains human-only test scripts that verify real OmniFocus interaction. Agents must never execute these."
- Error messages should help Claude help the user at 7:30am — "OmniFocus not running" is more useful than "connection refused"
- The `_trigger_omnifocus()` method in RealBridge is currently a no-op placeholder (line 123) — Phase 8 implements it with the URL scheme
- `app_lifespan` currently raises `NotImplementedError` for bridge type `"real"` (line 62) — Phase 8 wires in FileMtimeSource

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `RealBridge` class (`bridge/_real.py`): Full IPC mechanics already implemented — atomic writes, async polling, dispatch protocol, timeout, orphan sweep. Only `_trigger_omnifocus()` is a no-op
- `SimulatorBridge` (`bridge/_simulator.py`): Subclasses RealBridge, proves the template method pattern works — RealBridge just needs its trigger implemented
- `BridgeTimeoutError`, `BridgeProtocolError`, `BridgeConnectionError` (`bridge/_errors.py`): Error hierarchy already exists with operation tracking
- `create_bridge()` factory (`bridge/_factory.py`): Already handles `"real"` type, returns `RealBridge`. Safety guard goes here
- `app_lifespan` (`server/_server.py`): Wiring point for FileMtimeSource — currently `NotImplementedError` for "real" bridge type

### Established Patterns
- Template method: `_trigger_omnifocus()` is the override hook — SimulatorBridge proves this pattern
- Factory DI: `OMNIFOCUS_BRIDGE` env var selects bridge type, `OMNIFOCUS_IPC_DIR` overrides IPC path
- Async file I/O: all file operations wrapped in `asyncio.to_thread()` — maintain this pattern
- Error hierarchy: typed exceptions with `operation` field for context

### Integration Points
- `_trigger_omnifocus()` in `RealBridge` — implement URL scheme trigger here
- `app_lifespan` bridge_type=="real" branch — wire `FileMtimeSource` with `.ofocus` directory path
- `bridge/__init__.py` — exports already include `RealBridge` and `sweep_orphaned_files`
- `pyproject.toml` — add pytest `testpaths` exclusion for `uat/`
- CI config — add safety grep step and `uat/` exclusion

</code_context>

<deferred>
## Deferred Ideas

- UAT framework for write operations (sandboxed test data setup/teardown with confirmation prompts) — future milestones when WRIT-01/02/03 are implemented
- Retry/resilience logic for bridge communication — tracked in Out of Scope as "Production hardening"
- Agent-facing structured error responses (JSON error objects vs string messages) — refine when real error patterns emerge

</deferred>

---

*Phase: 08-realbridge-and-end-to-end-validation*
*Context gathered: 2026-03-02*
