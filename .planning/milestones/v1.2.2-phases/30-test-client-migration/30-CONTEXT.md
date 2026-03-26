# Phase 30: Test Client Migration - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace all manual test connection plumbing (`_ClientSessionProxy`, `run_with_client`) with FastMCP's native `Client(server)` pattern. All tests use the new pattern, all manual plumbing deleted, all tests pass.

</domain>

<decisions>
## Implementation Decisions

### Migration scope
- **D-01:** Migrate ALL test files with manual plumbing — conftest.py, test_server.py, test_simulator_bridge.py, test_simulator_integration.py
- Not just the files named in TEST-01/TEST-02. D-09 from Phase 29 ("built from scratch with fastmcp>=3") means no manual plumbing should survive anywhere

### Fixture strategy
- **D-02:** Replace `client_session` fixture with a 6-line async fixture yielding `Client`
- Delete `_ClientSessionProxy` entirely (45 lines)
- New fixture: `async def client(server) -> AsyncIterator[Client]` using `async with Client(server) as c: yield c`
- Keep `server` fixture as-is — it encapsulates InMemoryBridge chain and snapshot seeding, which is genuine test infrastructure
- Tests inject `client: Client` instead of `client_session: ClientSession`

### Error assertion migration
- **D-03:** `assert result.isError is True` + error message checks → `pytest.raises(ToolError, match="...")` — one-liner pattern
- **D-04:** `assert result.isError is not True` success guards → removed entirely. No exception = success. Content assertions on the next line already catch regressions
- Verified: no orphan tests exist — every guard is either followed by content assertions or is a setup step in a test whose name and final assertions make the purpose clear
- If during implementation any test looks ambiguous after guard removal ("what's the point?"), add a try/except with `pytest.fail("should not raise")` for that specific case

### Field renames (mechanical)
- **D-05:** All `result.isError` → `result.is_error`, `result.structuredContent` → `result.structured_content` (FastMCP Client uses snake_case)
- `list_tools().tools` → `list_tools()` (FastMCP Client returns flat list, not wrapper object)

### Claude's Discretion
- Import organization within test files
- Whether to rename `client_session` → `client` in one commit or split across files

</decisions>

<specifics>
## Specific Ideas

No specific requirements — the spike experiment (`04_test_client.py`) already proved the pattern works end-to-end.

</specifics>

<canonical_refs>
## Canonical References

### FastMCP Client pattern
- `.research/deep-dives/fastmcp-spike/experiments/04_test_client.py` — Proven Client(server) test pattern with call_tool, ToolError assertions
- `.research/deep-dives/fastmcp-spike/FINDINGS.md` — Spike findings including Client lifecycle and error behavior

### Phase requirements
- `.planning/ROADMAP.md` Phase 30 section — TEST-01 through TEST-05 requirements and success criteria

### Prior phase decisions
- `.planning/phases/29-dependency-swap-imports/29-CONTEXT.md` — D-09 (built from scratch with fastmcp>=3), D-12 (TODO comments for deferred cleanup)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- `server` fixture (conftest.py line 396): FastMCP server with patched lifespan — keep as-is, it's the right abstraction level
- Spike experiment `04_test_client.py`: Working reference implementation of Client(server) pattern

### Established Patterns
- `@pytest.mark.snapshot(...)` → `bridge` → `repo` → `service` → `server` fixture chain — unchanged, `client` fixture adds one more link
- Tests grouped in classes by tool (`TestGetById`, `TestAddTasks`, `TestEditTasks`)
- `pytest.raises(ToolError, match=...)` already established as preferred error testing pattern (feedback memory)

### Integration Points
- `conftest.py` `client_session` fixture → replaced by `client` fixture (all downstream tests affected)
- `test_server.py` `run_with_client` helper → deleted, callers migrated
- `test_simulator_bridge.py` / `test_simulator_integration.py` `_run_with_client` helpers → deleted, callers migrated

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 30-test-client-migration*
*Context gathered: 2026-03-26*
