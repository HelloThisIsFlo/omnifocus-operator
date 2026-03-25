# Domain Pitfalls

**Domain:** FastMCP v3 migration in existing MCP server with 697 tests
**Researched:** 2026-03-25
**Confidence:** HIGH -- all pitfalls discovered during spike experiments or verified via source inspection

## Critical Pitfalls

### Pitfall 1: Client.call_tool() raises ToolError by default

**What goes wrong:** Tests that check `result.isError is True` fail because `call_tool()` raises before returning.
**Why it happens:** FastMCP v3's `Client.call_tool()` has `raise_on_error=True` as default. The old `ClientSession.call_tool()` always returned `CallToolResult` regardless of errors.
**Consequences:** Every error-assertion test fails. ~10 tests in test_server.py check for `isError=True`.
**Prevention:** Use `call_tool_mcp()` instead of `call_tool()`. Returns raw `CallToolResult` (same as current ClientSession behavior). Zero assertion changes needed for error tests.
**Detection:** Tests fail with `ToolError` exception instead of assertion failure. Easy to spot.

### Pitfall 2: ToolAnnotations import path unchanged

**What goes wrong:** Mechanical find-and-replace changes `from mcp.types import ToolAnnotations` to something fastmcp-based, which fails.
**Why it happens:** FastMCP does NOT re-export `ToolAnnotations`. It lives in `mcp.types` only.
**Consequences:** ImportError at server startup. All 6 tool registrations break.
**Prevention:** Leave `from mcp.types import ToolAnnotations` unchanged. `mcp` is a transitive dependency of `fastmcp` so the import always works.
**Detection:** ImportError on first test run or server start.

### Pitfall 3: Mixing import migration with behavior changes

**What goes wrong:** Changing imports AND deleting test plumbing AND adding middleware in one phase makes failures impossible to attribute.
**Why it happens:** "It's just an SDK swap" tempts doing everything at once.
**Consequences:** When tests fail, unclear whether it's a bad import, a test client difference, or a middleware side effect.
**Prevention:** Phase 1 changes ONLY imports. Tests must pass before any behavior changes. Then test client (phase 2), then middleware (phase 3).
**Detection:** Multiple unrelated failures in a single commit.

## Moderate Pitfalls

### Pitfall 4: Client lifecycle management in fixtures

**What goes wrong:** Tests hang or fail with connection errors because `Client(server)` was not used as async context manager.
**Why it happens:** Current `_ClientSessionProxy` manages its own lifecycle per-call. `Client(server)` requires explicit `async with`.
**Prevention:** Use async fixture with `yield`:
```python
@pytest.fixture
async def client(server):
    async with Client(server) as c:
        yield c
```
**Detection:** Tests hang on first `call_tool` call or raise `RuntimeError: Client not connected`.

### Pitfall 5: Middleware logger setup ordering

**What goes wrong:** Middleware fires before loggers are configured, producing no output or crashing.
**Why it happens:** `create_server()` runs before `__main__.py` sets up logging. If middleware is wired in `create_server()`, loggers may not exist yet.
**Prevention:** Two valid approaches:
- Wire middleware in `__main__.py` after logger setup (preferred -- keeps `create_server()` pure)
- Use lazy logger creation in middleware (works but less explicit)
**Detection:** Silent middleware (no log output) or `AttributeError` on logger.

### Pitfall 6: Tests that construct servers directly

**What goes wrong:** Tests using `FastMCP("omnifocus-operator", lifespan=app_lifespan)` directly (degraded mode tests, IPC sweep tests) need updated imports but may also need adapted for Client pattern.
**Why it happens:** These tests bypass the `server` fixture and build custom servers. They currently use `run_with_client()` which gets deleted.
**Prevention:** Identify all direct server construction sites before migration. Migrate them to `async with Client(custom_server) as client:` inline.
**Detection:** Grep for `FastMCP(` and `run_with_client` in test files.

### Pitfall 7: Structured content extraction differences

**What goes wrong:** `call_tool()` (the raising variant) returns `CallToolResult` but wraps list returns in `{"result": [...]}` -- tests extracting `result.structuredContent["result"]` may see different shapes.
**Why it happens:** FastMCP v3 serialization may differ from the low-level `ClientSession`.
**Prevention:** Use `call_tool_mcp()` which returns the identical `CallToolResult` object. Verify one test end-to-end early.
**Detection:** `KeyError` or unexpected dict structure in test assertions.

## Minor Pitfalls

### Pitfall 8: anyio dependency removal

**What goes wrong:** `import anyio` left in test files after migration (unused import lint warning or confusion).
**Why it happens:** `anyio` was imported for `create_memory_object_stream` which is no longer needed.
**Prevention:** Remove all `anyio` imports from test files during phase 2. Also remove `ClientSession` and `SessionMessage` imports.
**Detection:** Ruff/flake8 unused import warning.

### Pitfall 9: ctx.info() temptation

**What goes wrong:** Someone adds `ctx.info("Processing batch item N")` thinking it shows in Claude Desktop.
**Why it happens:** FastMCP docs prominently feature `ctx.info()` / `ctx.warning()`. Looks like the right API.
**Prevention:** Document in CLAUDE.md or code comments: "Do NOT use ctx.info() -- no major client renders it. Use response-payload warnings for agent-facing messages."
**Detection:** Log messages that never appear in any client.

### Pitfall 10: stderr hijacking myth resurfaces

**What goes wrong:** Future developer re-adds `propagate = False` and file-only logging because they think stderr is hijacked.
**Why it happens:** The misdiagnosis was convincing. Claude Code does swallow stderr during tool calls (issue #29035), which looks like hijacking.
**Prevention:** Replace the misdiagnosis comment with an accurate explanation: "Claude Code swallows stderr during tool execution (issue #29035). FileHandler is a fallback for Claude Code debugging. stderr still works for Claude Desktop."
**Detection:** Logs disappearing from Claude Desktop's log page.

## Phase-Specific Warnings

| Phase | Likely Pitfall | Mitigation |
|-------|---------------|------------|
| 1: Dep Swap | ToolAnnotations import broken (Pitfall 2) | Leave `from mcp.types` unchanged |
| 2: Test Client | Client lifecycle in fixtures (Pitfall 4) | Use async fixture with yield |
| 2: Test Client | Error assertion breakage (Pitfall 1) | Use `call_tool_mcp()` uniformly |
| 2: Test Client | Direct server construction tests (Pitfall 6) | Grep and migrate individually |
| 3: Middleware | Logger ordering (Pitfall 5) | Wire in `__main__.py` after logger setup |
| 5: Progress | None identified | Trivial API, graceful no-op |

## Sources

- Pitfall 1: `Client.call_tool` source inspection, `raise_on_error=True` default confirmed
- Pitfall 2: Live import test -- `from fastmcp import ToolAnnotations` raises ImportError
- Pitfall 4: FastMCP docs + spike experiment 04
- Pitfall 5: Observed during spike middleware experiment setup
- Pitfall 9: Spike experiment 02 -- comprehensive client visibility matrix
- Pitfall 10: Spike experiment 03 -- stderr hijacking debunked
