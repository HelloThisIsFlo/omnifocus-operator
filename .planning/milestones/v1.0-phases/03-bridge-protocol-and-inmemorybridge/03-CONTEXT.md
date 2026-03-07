# Phase 3: Bridge Protocol and InMemoryBridge - Context

**Gathered:** 2026-03-01
**Status:** Ready for planning

<domain>
## Phase Boundary

A pluggable bridge abstraction that decouples all upstream code from OmniFocus, with a test implementation that returns data from memory. The bridge protocol defines the contract that Repository, Service, and MCP layers program against. InMemoryBridge is the first concrete implementation, purpose-built for testing.

</domain>

<decisions>
## Implementation Decisions

### Command contract
- Use Python `Protocol` (structural typing), not ABC — implementations don't need to inherit from a base class
- `send_command` is async-only — the MCP server runs in an async event loop, and file IPC (Phases 6-8) is inherently async
- Include an optional `params` argument from day one — `dump_all` ignores it, but future operations (create_task, complete_task) can use it without protocol signature changes
- Returns raw `dict[str, Any]` payload — the caller (Repository) is responsible for parsing into DatabaseSnapshot or other models. Keeps the bridge simple: it shuttles data, not domain objects

### Error contract
- Error hierarchy from the start: base `BridgeError` with subclasses for distinct failure modes (timeout, connection, protocol)
- Errors include structured context: the operation that failed + optional chained cause exception
- Rationale: the MCP server needs to tell the AI agent *why* it failed — "OmniFocus isn't running, ask the user to open it" vs "timed out, try again" vs "response was garbled" are genuinely different user-facing responses

### Test bridge (InMemoryBridge)
- Configurable error simulation — can be set up to raise specific BridgeError subclasses on demand, so downstream tests (Repository, Service) can test error handling without the real bridge
- Built-in call tracking — records each `send_command` call (operation + params). Essential for testing repository caching in Phase 4: assert the cache prevents extra bridge calls
- User's rationale: "InMemoryBridge is built for tests anyway — tracking doesn't pollute the logic"

### Claude's Discretion
- Operation identifier style (string literals vs typed enum vs command objects)
- Return type details beyond raw dict
- Data injection approach (constructor injection vs builder vs other)
- Whether InMemoryBridge provides a sensible default snapshot or requires explicit data

</decisions>

<specifics>
## Specific Ideas

- Call tracking example the user liked: `assert bridge.call_count == 1` and `assert bridge.calls[0].operation == "dump_all"` — clean, pytest-native assertions
- Error hierarchy motivated by future UX: different error types enable the AI agent to give the user actionable advice ("open OmniFocus" vs "try again")

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `OmniFocusBaseModel` (models/_base.py): Base with camelCase aliases and `validate_by_name=True` — bridge errors and protocol types can extend this if they need serialization
- `DatabaseSnapshot` (models/_snapshot.py): The type that `dump_all` responses parse into — bridge returns raw dict, Repository calls `DatabaseSnapshot.model_validate(data)`
- `make_snapshot_dict()` and entity factories (tests/conftest.py): Ready-made camelCase dicts for constructing test data — InMemoryBridge can use these directly

### Established Patterns
- `TYPE_CHECKING` imports for forward references with `model_rebuild()` in `__init__.py` — follow this pattern if bridge types reference models
- Private module convention: `_base.py`, `_task.py` etc. with public re-exports from `__init__.py`
- pytest with factory functions (not fixtures) for test data construction

### Integration Points
- Bridge module will live at `src/omnifocus_operator/bridge/` (new package)
- Repository (Phase 4) will accept bridge protocol as constructor dependency
- Service layer (Phase 5) wires bridge → repository via DI

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 03-bridge-protocol-and-inmemorybridge*
*Context gathered: 2026-03-01*
