# Quick Task 1: Remove eager cache hydration on startup — Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Task Boundary

Remove the eager cache pre-warming on MCP server startup. The `get_snapshot()` method already handles a cold cache (`self._snapshot is None`), so the first tool call will lazily populate it. This avoids blocking OmniFocus for ~3 seconds every time a new Claude session starts.

</domain>

<decisions>
## Implementation Decisions

### initialize() method
- Delete entirely — remove the method from OmniFocusRepository and all its dedicated tests. It becomes dead code with no callers. `get_snapshot()` already handles the cold cache path.

### Lifespan logging
- Remove the "Pre-warming repository cache..." and "Cache pre-warmed successfully" log lines silently. No replacement log message needed.

### Test cleanup scope
- Full cleanup: update all test setup calls that use `initialize()` to use `get_snapshot()` directly. Delete the dedicated `initialize()` tests (SNAP-06 group).

</decisions>

<specifics>
## Specific Ideas

- The lifespan in `_server.py` lines 78-84 has the `initialize()` call and try/except — remove that entire block.
- `_repository.py` lines 70-76: delete the `initialize()` method.
- Tests referencing `initialize()`: ~10 occurrences across `test_repository.py`, `test_server.py`, `test_simulator_integration.py`, `test_simulator_bridge.py`.

</specifics>
