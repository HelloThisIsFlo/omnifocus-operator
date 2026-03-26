# Phase 30: Test Client Migration - Research

**Researched:** 2026-03-26
**Domain:** Test infrastructure migration -- FastMCP v3 Client pattern
**Confidence:** HIGH

## Summary

Replace all manual MCP test connection plumbing with FastMCP v3's native `Client(server)` pattern. The spike experiment (`04_test_client.py`) already proved end-to-end viability. The migration is mechanical: delete ~70 lines of `anyio`/`ClientSession` stream plumbing across 4 files, replace with 6-line `Client` fixture, update field accessors from camelCase to snake_case, and convert error assertions to `pytest.raises(ToolError)`.

The migration surface is well-bounded: 4 files, 3 plumbing artifacts to delete, ~160 field rename sites, and 18 error assertion conversions. All changes are test-only -- no production code changes.

**Primary recommendation:** Migrate in 3 waves: (1) fixture swap + field renames (mechanical), (2) error assertion migration, (3) `run_with_client` callers + cleanup of dead imports.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- **D-01:** Migrate ALL test files with manual plumbing -- conftest.py, test_server.py, test_simulator_bridge.py, test_simulator_integration.py
- **D-02:** Replace `client_session` fixture with 6-line async fixture yielding `Client`. Delete `_ClientSessionProxy` entirely. Keep `server` fixture as-is.
- **D-03:** `assert result.isError is True` + error message checks -> `pytest.raises(ToolError, match="...")` one-liner pattern
- **D-04:** `assert result.isError is not True` success guards -> removed entirely. No exception = success.
- **D-05:** All `result.isError` -> `result.is_error`, `result.structuredContent` -> `result.structured_content`, `list_tools().tools` -> `list_tools()` (FastMCP Client uses snake_case / flat list)

### Claude's Discretion
- Import organization within test files
- Whether to rename `client_session` -> `client` in one commit or split across files

### Deferred Ideas (OUT OF SCOPE)
None
</user_constraints>

<phase_requirements>
## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| TEST-01 | `_ClientSessionProxy` class deleted from conftest.py | Direct deletion: lines 439-484, replaced by 6-line `client` fixture using `async with Client(server)` |
| TEST-02 | `run_with_client` helper deleted from test_server.py | Direct deletion: lines 55-95. 14 call sites migrated to `async with Client(server)` inline |
| TEST-03 | All server tests use `async with Client(server) as client` pattern | `client_session` fixture (40 tests) replaced by `client` fixture; `run_with_client` callers (14) + simulator files (4) use Client directly |
| TEST-04 | Error assertions use `pytest.raises(ToolError)` instead of `is_error` boolean checks | 18 `isError is True` assertions -> `pytest.raises(ToolError, match=...)` |
| TEST-05 | All existing tests pass with new test client | Baseline: 68 tests in affected files. Full suite: 534+ tests. Run after each wave. |
</phase_requirements>

## Standard Stack

### Core
| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastmcp` | 3.1.1 | `Client(server)` for in-process test connections | Already installed; native test client replaces 70 lines of manual plumbing |
| `pytest` | (existing) | Test framework | Already configured with asyncio_mode="auto" |

### Key Imports (new)
```python
from fastmcp import Client
from fastmcp.exceptions import ToolError
```

### Imports Removed
```python
# DELETE these from test files:
import anyio
from mcp.client.session import ClientSession
from mcp.shared.message import SessionMessage
```

## Architecture Patterns

### New Fixture Pattern (conftest.py)

**Before (45 lines):**
```python
@pytest.fixture
def client_session(server):
    import anyio
    from mcp.client.session import ClientSession
    from mcp.shared.message import SessionMessage

    class _ClientSessionProxy:
        # ... 40 lines of anyio stream plumbing ...
    return _ClientSessionProxy(server)
```

**After (6 lines):**
```python
@pytest.fixture
async def client(server: Any) -> AsyncIterator[Any]:
    """FastMCP Client connected to the test server."""
    from fastmcp import Client
    async with Client(server) as c:
        yield c
```

### Test Pattern: Success Path

**Before:**
```python
async def test_get_task(self, client_session: ClientSession) -> None:
    result = await client_session.call_tool("get_task", {"id": "task-001"})
    assert result.isError is not True          # D-04: remove
    assert result.structuredContent is not None
    assert result.structuredContent["id"] == "task-001"
```

**After:**
```python
async def test_get_task(self, client: Client) -> None:
    result = await client.call_tool("get_task", {"id": "task-001"})
    assert result.structured_content is not None
    assert result.structured_content["id"] == "task-001"
```

Changes: `client_session` -> `client`, remove `isError is not True` guard, `structuredContent` -> `structured_content`.

### Test Pattern: Error Path

**Before:**
```python
async def test_not_found(self, client_session: ClientSession) -> None:
    result = await client_session.call_tool("get_task", {"id": "nonexistent"})
    assert result.isError is True
    text = result.content[0].text
    assert "Task not found: nonexistent" in text
```

**After:**
```python
async def test_not_found(self, client: Client) -> None:
    with pytest.raises(ToolError, match="Task not found: nonexistent"):
        await client.call_tool("get_task", {"id": "nonexistent"})
```

`ToolError` is raised because `Client.call_tool()` has `raise_on_error=True` by default. `match=` checks against `str(exception)`.

### Test Pattern: Error with Multi-line Match

Some error tests check multiple things about the error text (e.g., degraded mode checks "failed to start" AND "OMNIFOCUS_SQLITE_PATH"). Two approaches:

**Option A: Multiple match patterns**
```python
with pytest.raises(ToolError, match="failed to start") as exc_info:
    await client.call_tool("get_all")
assert "OMNIFOCUS_SQLITE_PATH" in str(exc_info.value)
```

**Option B: Single regex with `(?s)` flag**
```python
with pytest.raises(ToolError, match=r"(?si)failed to start.*OMNIFOCUS_SQLITE_PATH"):
    await client.call_tool("get_all")
```

Option A is clearer -- use it for complex error text assertions.

### Test Pattern: `list_tools()` Accessor

**Before:**
```python
tools_result = await client_session.list_tools()
names = [t.name for t in tools_result.tools]
tool = next(t for t in tools_result.tools if t.name == "get_all")
assert result.tools is not None  # existence check
```

**After:**
```python
tools = await client.list_tools()
names = [t.name for t in tools]
tool = next(t for t in tools if t.name == "get_all")
# existence check: remove entirely (list_tools always returns a list)
```

`Client.list_tools()` returns `list[mcp.types.Tool]` directly -- no `.tools` wrapper.

### Test Pattern: `run_with_client` Callers (inline Client)

Tests that create their own server (e.g., via `create_server()` with monkeypatch) currently use the `run_with_client` helper. These get inlined with `Client(server)`:

**Before:**
```python
async def test_something(self, monkeypatch):
    monkeypatch.setattr(...)
    server = create_server()

    async def _check(session: ClientSession) -> None:
        result = await session.call_tool("get_all")
        assert result.structuredContent is not None

    await run_with_client(server, _check)
```

**After:**
```python
async def test_something(self, monkeypatch):
    monkeypatch.setattr(...)
    server = create_server()

    async with Client(server) as client:
        result = await client.call_tool("get_all")
        assert result.structured_content is not None
```

Eliminates the callback indirection.

### Test Pattern: Degraded Mode (caplog tests)

Two degraded mode tests check log records AFTER a tool call. With ToolError raised, the call must be caught:

**Before:**
```python
async def _check(session):
    await session.call_tool("get_all")
await run_with_client(server, _check)
assert any("Fatal error" in r.message for r in caplog.records)
```

**After:**
```python
async with Client(server) as client:
    with pytest.raises(ToolError):
        await client.call_tool("get_all")
assert any("Fatal error" in r.message for r in caplog.records)
```

### Anti-Patterns to Avoid

- **Don't use `raise_on_error=False`:** The whole point of D-03/D-04 is to use idiomatic `pytest.raises(ToolError)`. Using `raise_on_error=False` would preserve the old `isError` pattern -- defeats the purpose.
- **Don't keep `isError is not True` guards:** Per D-04, no-exception = success. The next line's content assertion already catches regressions.
- **Don't import `ClientSession` or `anyio` in test files:** These are the manual plumbing imports being deleted.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| MCP test connections | `_ClientSessionProxy` with anyio streams | `Client(server)` | 45 lines -> 3 lines. FastMCP handles lifecycle, streams, initialization |
| Server-client wiring | `run_with_client` callback pattern | `async with Client(server)` | Eliminates callback indirection, clearer test structure |
| Error type checking | `result.isError is True` + text extraction | `pytest.raises(ToolError, match=...)` | One-liner, idiomatic pytest, match validates message content |

## Common Pitfalls

### Pitfall 1: `call_tool` Raises by Default
**What goes wrong:** Tests that previously checked `result.isError is True` will crash with unhandled `ToolError` instead of failing assertions gracefully.
**Why it happens:** `Client.call_tool()` has `raise_on_error=True` as default. Old `ClientSession.call_tool()` always returned `CallToolResult`.
**How to avoid:** Convert ALL `isError is True` assertions to `pytest.raises(ToolError)` BEFORE running. Never use `raise_on_error=False`.
**Warning signs:** `ToolError` traceback in test output where you expected assertion failure.

### Pitfall 2: `structuredContent` vs `structured_content`
**What goes wrong:** `AttributeError: 'CallToolResult' object has no attribute 'structuredContent'`
**Why it happens:** `CallToolResult` (FastMCP dataclass) uses snake_case. Old `mcp.types.CallToolResult` (Pydantic) used camelCase.
**How to avoid:** Find-and-replace: `structuredContent` -> `structured_content`, `isError` -> `is_error`.
**Warning signs:** `AttributeError` on field access.

### Pitfall 3: `list_tools().tools` vs `list_tools()`
**What goes wrong:** `AttributeError: 'list' object has no attribute 'tools'`
**Why it happens:** `Client.list_tools()` returns `list[Tool]` directly. Old `ClientSession.list_tools()` returned `ListToolsResult` wrapper with `.tools` attribute.
**How to avoid:** Remove `.tools` accessor from all `list_tools()` calls.
**Warning signs:** `AttributeError` on `.tools`.

### Pitfall 4: `_build_patched_server` Import Aliasing
**What goes wrong:** `_build_patched_server` in test_server.py locally imports `from fastmcp import FastMCP as FastMCPv3` and has a comment "Phase 30 will migrate the top-level import."
**Why it happens:** Phase 29 left this TODO for Phase 30.
**How to avoid:** Clean up the import alias during migration -- remove `from mcp.server.fastmcp import FastMCP` at the top and the local alias in `_build_patched_server`.
**Warning signs:** Two different `FastMCP` names in the same file.

### Pitfall 5: Degraded Mode Error Text Assertions
**What goes wrong:** Degraded mode tests check specific text in error messages. With `ToolError`, the text is in `str(exception)`, but the exact content may differ from `result.content[0].text`.
**Why it happens:** FastMCP may wrap the error differently than raw `ClientSession`.
**How to avoid:** After converting to `pytest.raises(ToolError, match=...)`, verify the error text matches. Use `exc_info.value` for multi-assertion checks.
**Warning signs:** Match pattern doesn't match. Run affected tests first.

### Pitfall 6: Async Fixture Requires `AsyncIterator`
**What goes wrong:** New `client` fixture must be async (uses `async with`). Without proper typing, pytest may not handle it correctly.
**Why it happens:** The fixture uses `yield` inside an `async with` block.
**How to avoid:** Use `AsyncIterator` return type annotation and ensure pytest-asyncio is configured (`asyncio_mode = "auto"` -- already set).
**Warning signs:** Fixture never yields, tests hang.

## Migration Surface (Quantified)

### Files to Modify
| File | Changes | Complexity |
|------|---------|------------|
| `tests/conftest.py` | Delete `_ClientSessionProxy` (lines 420-484), add `client` fixture (6 lines) | Low |
| `tests/test_server.py` | Delete `run_with_client` (lines 55-95), migrate 14 callers to `Client`, rename 40 `client_session` params, update 52 `structuredContent`, 51 `isError`, 11 `.tools` | High (volume) |
| `tests/test_simulator_bridge.py` | Delete `_run_with_client` (lines 77-114), migrate 3 callers, update 1 `structuredContent`, 1 `.tools` | Low |
| `tests/test_simulator_integration.py` | Delete `_run_with_client` (lines 117-154), migrate 1 caller, update 3 `structuredContent`, 1 `.tools` | Low |

### Counts by Transformation Type
| Transformation | Count | Pattern |
|---------------|-------|---------|
| `client_session` -> `client` (param names) | 40 | Rename in test_server.py |
| `structuredContent` -> `structured_content` | 56 total | 52 + 1 + 3 |
| `isError is True` -> `pytest.raises(ToolError)` | 18 | test_server.py only |
| `isError is not True` -> DELETE | 32 | test_server.py only |
| `tools_result.tools` -> `tools_result` (or `tools`) | 12 total | 11 + 1 |
| `run_with_client` call sites -> inline `Client` | 21 total | 14 + 4 + 1 + (conftest internal) |
| Import cleanup (delete `anyio`, `ClientSession`, `SessionMessage`) | 4 files | All affected files |
| `_build_patched_server` import alias cleanup | 1 | test_server.py |
| `ClientSession` type hints in TYPE_CHECKING | 2 | test_server.py, test_simulator_integration.py |

### CallToolResult API Mapping

| Old (`mcp.types.CallToolResult`) | New (`fastmcp.client.client.CallToolResult`) | Notes |
|----------------------------------|----------------------------------------------|-------|
| `result.isError` | `result.is_error` | snake_case |
| `result.structuredContent` | `result.structured_content` | snake_case |
| `result.content` | `result.content` | Unchanged -- `list[ContentBlock]` |
| `result.content[0].text` | Only via `ToolError` exception text | When `raise_on_error=True` |
| N/A | `result.data` | New -- parsed return value |
| N/A | `result.meta` | New -- metadata dict |

### list_tools API Mapping

| Old (`ClientSession`) | New (`Client`) | Notes |
|----------------------|----------------|-------|
| `list_tools().tools` | `list_tools()` | Returns `list[Tool]` directly |
| `result.tools is not None` | Always a list | Remove existence check |

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest 8.x with pytest-asyncio (asyncio_mode="auto") |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_server.py tests/test_simulator_bridge.py tests/test_simulator_integration.py -x -q --no-header --tb=short --no-cov` |
| Full suite command | `uv run pytest -x` |

### Phase Requirements -> Test Map
| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| TEST-01 | `_ClientSessionProxy` deleted | grep verification | `grep -r '_ClientSessionProxy' tests/ && echo FAIL \|\| echo PASS` | N/A |
| TEST-02 | `run_with_client` deleted | grep verification | `grep -r 'run_with_client' tests/ && echo FAIL \|\| echo PASS` | N/A |
| TEST-03 | All tests use `Client(server)` pattern | grep + test run | `uv run pytest tests/test_server.py tests/test_simulator_bridge.py tests/test_simulator_integration.py -x -q --no-cov` | Existing |
| TEST-04 | Error assertions use `pytest.raises(ToolError)` | grep verification | `grep -r 'isError' tests/ && echo FAIL \|\| echo PASS` | N/A |
| TEST-05 | All existing tests pass | full test suite | `uv run pytest -x` | Existing |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_server.py tests/test_simulator_bridge.py tests/test_simulator_integration.py -x -q --no-cov`
- **Per wave merge:** `uv run pytest -x --no-cov`
- **Phase gate:** Full suite green + grep verifications for TEST-01 through TEST-04

### Wave 0 Gaps
None -- existing test infrastructure covers all phase requirements. No new test files or frameworks needed. The migration modifies existing tests.

## Code Examples

### New `client` Fixture (conftest.py)
```python
# Source: CONTEXT.md D-02 + spike experiment 04_test_client.py
@pytest.fixture
async def client(server: Any) -> AsyncIterator[Any]:
    """FastMCP Client connected to the test server.

    Chain: @pytest.mark.snapshot(...) -> bridge -> repo -> service -> server -> client
    """
    from fastmcp import Client  # noqa: PLC0415

    async with Client(server) as c:
        yield c
```

### Error Assertion with Match
```python
# Source: fastmcp.exceptions.ToolError + pytest.raises
from fastmcp.exceptions import ToolError

async def test_not_found(self, client: Client) -> None:
    with pytest.raises(ToolError, match="Task not found: nonexistent"):
        await client.call_tool("get_task", {"id": "nonexistent"})
```

### Inline Client for Monkeypatched Servers
```python
# Source: spike experiment 04_test_client.py pattern
from fastmcp import Client

async def test_degraded(self, monkeypatch):
    with patch("omnifocus_operator.repository.create_repository",
               side_effect=RuntimeError("exploded")):
        server = create_server()
        async with Client(server) as client:
            with pytest.raises(ToolError, match="(?i)failed to start"):
                await client.call_tool("get_all")
```

## Open Questions

1. **ToolError text for degraded mode**
   - What we know: `ErrorOperatorService.__getattr__` raises `RuntimeError` with specific text. FastMCP wraps it as `ToolError`.
   - What's unclear: Whether `str(ToolError)` contains the exact same text as `result.content[0].text` did before. Likely yes (FastMCP uses `str(exception)` as error message), but verify during implementation.
   - Recommendation: Implement degraded mode tests first and verify text matches. If wrapping adds prefix, adjust match patterns.

2. **`_build_patched_server` survival**
   - What we know: This helper creates a server with patched lifespan. It currently imports `FastMCP as FastMCPv3` locally as a Phase 29 leftover.
   - What's unclear: Whether to keep it (used by 2 test classes) or inline its logic.
   - Recommendation: Keep it but clean up the import alias. It provides genuine value (DRY for custom-service tests).

## Sources

### Primary (HIGH confidence)
- FastMCP v3.1.1 source code -- `CallToolResult` dataclass fields verified via runtime inspection
- `Client.call_tool` signature verified: `raise_on_error=True` default
- `Client.list_tools` return type verified: `list[mcp.types.Tool]`
- Spike experiment `04_test_client.py` -- proven end-to-end Client(server) pattern

### Secondary (MEDIUM confidence)
- FINDINGS.md from spike -- error behavior and adaptation points documented

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- fastmcp 3.1.1 already installed, API verified via runtime inspection
- Architecture: HIGH -- patterns proven in spike experiment, all field names verified
- Pitfalls: HIGH -- every pitfall derived from verified API differences between old/new patterns

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable -- fastmcp 3.1.1 is pinned)
