# Requirements: OmniFocus Operator

**Defined:** 2026-03-25
**Core Value:** Reliable, simple, debuggable access to OmniFocus data for AI agents -- executive function infrastructure that works at 7:30am.

## v1.2.2 Requirements

Requirements for FastMCP v3 Migration. Infrastructure upgrade — no new tools, no behavioral changes.

### Dependency Migration

- [ ] **DEP-01**: Server runs on `fastmcp>=3.1.1` with all 6 tools functional
- [ ] **DEP-02**: All imports migrated from `mcp.server.fastmcp` to `fastmcp`
- [ ] **DEP-03**: `ctx.lifespan_context` shorthand replaces `ctx.request_context.lifespan_context` in all tool handlers
- [ ] **DEP-04**: `pyproject.toml` declares `fastmcp>=3.1.1` replacing `mcp>=1.26.0`

### Test Infrastructure

- [ ] **TEST-01**: `_ClientSessionProxy` class deleted from conftest.py
- [ ] **TEST-02**: `run_with_client` helper deleted from test_server.py
- [ ] **TEST-03**: All server tests use `async with Client(server) as client` pattern
- [ ] **TEST-04**: Error assertions use `pytest.raises(ToolError)` instead of `is_error` boolean checks
- [ ] **TEST-05**: All existing tests pass with new test client

### Middleware

- [ ] **MW-01**: `ToolLoggingMiddleware` class logs tool entry, exit (with timing), and errors automatically
- [ ] **MW-02**: `log_tool_call()` function and all 6 call sites deleted from server.py
- [ ] **MW-03**: Middleware fires for every tool call without manual wiring

### Logging

- [ ] **LOG-01**: `StreamHandler(stderr)` active for Claude Desktop log visibility
- [ ] **LOG-02**: `FileHandler(~/Library/Logs/omnifocus-operator.log)` active for persistent debugging
- [ ] **LOG-03**: Logger hierarchy uses `omnifocus_operator.*` namespace
- [ ] **LOG-04**: stderr hijacking misdiagnosis comment removed from `__main__.py`
- [ ] **LOG-05**: `ctx.info()` / `ctx.warning()` not used anywhere

### Progress

- [ ] **PROG-01**: `add_tasks` reports progress via `ctx.report_progress()` during batch processing
- [ ] **PROG-02**: `edit_tasks` reports progress via `ctx.report_progress()` during batch processing

### Documentation

- [ ] **DOC-01**: README reflects `fastmcp>=3.1.1` as runtime dependency
- [ ] **DOC-02**: Landing page reflects new dependency and unchanged tool count

## Future Requirements

### Elicitation (deferred — Claude Desktop unsupported)

- **ELICIT-01**: Destructive operations prompt for confirmation via `ctx.elicit()`
- **ELICIT-02**: Graceful fallback when client doesn't support elicitation

## Out of Scope

| Feature | Reason |
|---------|--------|
| New MCP tools | Infrastructure milestone — no new tools |
| Behavioral changes to existing tools | Pure migration — output must be identical |
| `ctx.info()` / `ctx.warning()` protocol logging | Dead end — no major client renders these (Claude Code #3174 closed "not planned") |
| `Depends()` DI pattern | Lifespan pattern works; `Depends()` solves a different lifecycle problem |
| Elicitation (`ctx.elicit()`) | Claude Desktop doesn't support it; revisit when it does |
| `get_logger()` from FastMCP | Wrong namespace (`fastmcp.*`), no logger name in output |
| Background tasks (`@mcp.tool(task=True)`) | No use case in current tool set |

## Traceability

Which phases cover which requirements. Updated during roadmap creation.

| Requirement | Phase | Status |
|-------------|-------|--------|
| DEP-01 | — | Pending |
| DEP-02 | — | Pending |
| DEP-03 | — | Pending |
| DEP-04 | — | Pending |
| TEST-01 | — | Pending |
| TEST-02 | — | Pending |
| TEST-03 | — | Pending |
| TEST-04 | — | Pending |
| TEST-05 | — | Pending |
| MW-01 | — | Pending |
| MW-02 | — | Pending |
| MW-03 | — | Pending |
| LOG-01 | — | Pending |
| LOG-02 | — | Pending |
| LOG-03 | — | Pending |
| LOG-04 | — | Pending |
| LOG-05 | — | Pending |
| PROG-01 | — | Pending |
| PROG-02 | — | Pending |
| DOC-01 | — | Pending |
| DOC-02 | — | Pending |

**Coverage:**
- v1.2.2 requirements: 21 total
- Mapped to phases: 0
- Unmapped: 21 ⚠️

---
*Requirements defined: 2026-03-25*
*Last updated: 2026-03-25 after initial definition*
