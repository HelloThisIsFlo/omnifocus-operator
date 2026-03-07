# Phase 9: Error-Serving Degraded Mode - Research

**Researched:** 2026-03-06
**Domain:** MCP server error handling, Python `__getattr__` patterns, graceful degradation
**Confidence:** HIGH

## Summary

This phase replaces the current pre-async `.ofocus` path validation workaround in `__main__.py` with a robust degraded mode inside the MCP server lifespan. Instead of crashing on fatal startup errors (which are invisible in headless MCP servers), the server stays alive and serves actionable error messages through every tool call.

The implementation is straightforward: wrap the `app_lifespan` body in `try/except Exception`, and on failure yield an `ErrorOperatorService` instead of the real `OperatorService`. The `ErrorOperatorService` uses `__getattr__` to dynamically intercept any method call and raise an exception containing the startup error message. The MCP SDK's built-in exception handler (confirmed at `lowlevel/server.py:583`) catches the raised exception and returns it as `CallToolResult(isError=True, content=[TextContent(text=str(e))])` -- exactly the behavior we want.

**Primary recommendation:** Implement `ErrorOperatorService` as a minimal `OperatorService` subclass with `__getattr__`, wrap `app_lifespan` in try/except, and simplify `__main__.py` to just `create_server()` + `server.run()`.

<user_constraints>
## User Constraints (from CONTEXT.md)

### Locked Decisions
- Catch fatal errors inside `app_lifespan` with a generic `except Exception`
- On failure, yield an `ErrorOperatorService` instead of the real `OperatorService`
- Remove the pre-async `.ofocus` path validation from `__main__.py` -- simplify to just `create_server()` + `server.run()`
- Keep the explicit `.ofocus` path check inside the lifespan for clear error messages -- it gets caught by the generic `except` now instead of crashing
- The lifespan's `except` also logs the full traceback to stderr at ERROR level
- `ErrorOperatorService` subclasses `OperatorService` using `__getattr__` to dynamically raise on any method call
- Does not call `super().__init__()` -- no instance attributes from parent, so all method calls fall through to `__getattr__`
- Future-proof: when new methods are added in later milestones, the error service covers them automatically
- Generic multi-line wrapper format for error messages (no per-error-type mapping)
- Same tools as the real server -- no extra health/status tool
- Log each degraded-mode tool call at WARNING level (tool name + "server is in error mode")
- Stay in error mode until process restart -- no retry logic

### Claude's Discretion
- Exact `__getattr__` implementation details (closure pattern, method signature)
- Whether to also log at INFO level when entering degraded mode (in addition to ERROR for the traceback)
- Test structure and organization for the new error-serving code

### Deferred Ideas (OUT OF SCOPE)
None -- discussion stayed within phase scope.
</user_constraints>

## Architecture Patterns

### Current Code Structure (What Changes)

```
src/omnifocus_operator/
├── __main__.py          # MODIFY: Remove pre-async validation, simplify
├── server/
│   └── _server.py       # MODIFY: Add try/except in app_lifespan
└── service/
    ├── __init__.py       # MODIFY: Export ErrorOperatorService
    └── _service.py       # MODIFY: Add ErrorOperatorService class
```

### Pattern 1: ErrorOperatorService via `__getattr__`

**What:** A subclass of `OperatorService` that skips `__init__` and uses `__getattr__` to intercept all method calls, raising an exception with the startup error message.

**When to use:** When you need a drop-in replacement that fails predictably on any method call.

**Key implementation detail:** Python's `__getattr__` is only called when normal attribute lookup fails. By not calling `super().__init__()`, the instance has no `_repository` attribute. When the tool handler calls `service.get_all_data()`, Python looks up `get_all_data` on the instance, finds nothing (no instance dict), then checks the class and parent class for a method definition. Since `OperatorService.get_all_data` IS defined as a method on the class, `__getattr__` will NOT be triggered for `get_all_data()`.

**CRITICAL CORRECTION:** `__getattr__` will not work for methods defined on the parent class. `get_all_data()` exists on `OperatorService`, so Python will find it via normal MRO lookup and call it directly -- which will then fail with `AttributeError: 'ErrorOperatorService' has no attribute '_repository'` rather than our nice error message.

**Recommended approach:** Override `__getattr__` for catching attribute access on undefined names AND explicitly raise in the body. Two options:

**Option A: `__getattr__` + explicit override of known methods**
```python
class ErrorOperatorService(OperatorService):
    def __init__(self, error: Exception) -> None:
        # Deliberately skip super().__init__()
        self._error = error
        self._error_message = (
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\n"
            "Restart the server after fixing."
        )

    async def get_all_data(self) -> DatabaseSnapshot:
        raise RuntimeError(self._error_message)

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(self._error_message)
```

This requires maintaining `get_all_data` override but catches future methods via `__getattr__`. The `_error` and `_error_message` attributes are set in `__init__`, so `__getattr__` is not triggered for those.

**Option B: Pure `__getattr__` with NO parent init and NO instance attrs**
```python
class ErrorOperatorService(OperatorService):
    def __init__(self, error: Exception) -> None:
        # Store on class or use object.__setattr__ to avoid __getattr__ loop
        object.__setattr__(self, "_error_message",
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\n"
            "Restart the server after fixing."
        )

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(self._error_message)
```
Problem: `get_all_data` is still found via MRO on the parent class, so `__getattr__` still won't intercept it.

**Recommendation: Use Option A.** The explicit `get_all_data` override is 2 lines and guarantees the error message. The `__getattr__` catches any future methods added in later milestones. This matches the user's stated intent of "future-proof" while being correct for the current method. The maintenance cost is trivial -- if a new method is added to `OperatorService` and not overridden in `ErrorOperatorService`, the call will hit the parent method, which accesses `_repository` (which doesn't exist)... wait, we DO set `_error_message` in `__init__` so `__getattr__` WILL be called for `_repository` access.

**Actually, let me reconsider:** The flow for `get_all_data()` would be:
1. Python finds `get_all_data` on `OperatorService` (parent class) via MRO
2. Calls it: `return await self._repository.get_snapshot()`
3. `self._repository` -- Python checks instance dict, not found, checks class/parents, not found
4. Falls through to `__getattr__("_repository")` which raises RuntimeError

So `__getattr__` DOES work indirectly -- the parent method tries to access `self._repository`, which doesn't exist (we skipped `super().__init__()`), triggering `__getattr__`. The error message from `__getattr__` propagates up.

**However**, the error message would say the attribute name `_repository` in the traceback, and the `__getattr__` receives `name="_repository"` not `name="get_all_data"`. The WARNING log line should include the tool name, not the private attribute name. So there's a question of whether to:
- Log in `__getattr__` (knows attribute name but not tool name)
- Log in the `__getattr__`-returned callable (if returning a callable instead of raising)

**Final recommendation:** The simplest correct approach that matches the user's intent:

```python
class ErrorOperatorService(OperatorService):
    def __init__(self, error: Exception) -> None:
        # Skip super().__init__() deliberately -- no _repository
        object.__setattr__(self, "_error_message",
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\n"
            "Restart the server after fixing."
        )

    def __getattr__(self, name: str) -> Any:
        raise RuntimeError(self._error_message)
```

When `get_all_data()` is called: parent method runs -> accesses `self._repository` -> `__getattr__("_repository")` -> raises RuntimeError with the error message -> MCP SDK catches and returns as `isError=True` response. This works correctly. The `_error_message` is set via `object.__setattr__` so it exists in the instance dict and doesn't trigger `__getattr__`.

For the WARNING log on tool calls: this should happen in the `__getattr__` method since that's where the interception occurs. The `name` parameter will be `"_repository"` (not the tool name), but we can log a generic message like "server is in error mode" without the tool name. Alternatively, the tool handler itself doesn't need modification -- the WARNING log could be added in `__getattr__`.

**However**, the user decision says "log each degraded-mode tool call at WARNING level (tool name + server is in error mode)". The tool name is known in the tool handler (`list_all`), not in `__getattr__`. Two approaches:
1. Log in `__getattr__` with whatever `name` is (will be `_repository`, not ideal)
2. Override `get_all_data` explicitly to log with tool context, then raise

**Best approach for logging:** Override `get_all_data` explicitly. This gives us the method name for logging, produces a clean error, and `__getattr__` still catches future methods. The log for future methods via `__getattr__` will use the attribute name, which is acceptable since we can't predict future tool-to-method mappings anyway.

### Pattern 2: Lifespan try/except

**What:** Wrap the entire `app_lifespan` body in try/except, yielding ErrorOperatorService on failure.

```python
@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    try:
        # ... existing initialization code ...
        yield {"service": service}
        logger.info("Server shutting down")
    except Exception as exc:
        logger.exception("Fatal error during startup")
        error_service = ErrorOperatorService(exc)
        yield {"service": error_service}
        logger.info("Error-mode server shutting down")
```

**Important:** The `yield` must be inside both branches of the try/except. The `asynccontextmanager` requires exactly one yield. The `except` block yields the error service and then waits for shutdown (same as normal path).

### Pattern 3: Simplified `__main__.py`

**Current:** Pre-async path validation + create_server + run
**New:** Just create_server + run (all validation moved into lifespan where it's caught)

```python
def main() -> None:
    logging.basicConfig(...)
    server = create_server()
    server.run(transport="stdio")
```

### Anti-Patterns to Avoid

- **Returning error from `__getattr__` instead of raising:** The MCP SDK expects exceptions, not return values. Tool handlers must raise to trigger `isError=True` responses.
- **Catching specific exceptions:** The decision is `except Exception` -- don't narrow to `FileNotFoundError` or other specific types. Any fatal startup error should trigger degraded mode.
- **Adding retry/recovery logic:** The decision is "stay in error mode until restart." No timers, no retry, no health checks.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Error-to-tool-response conversion | Custom error serialization | MCP SDK's built-in `except Exception` at L583 | SDK already converts raised exceptions to `CallToolResult(isError=True)` |
| Tool registration in error mode | Separate tool set for errors | Same `_register_tools()` with ErrorOperatorService | Liskov substitution -- tools don't know the difference |

## Common Pitfalls

### Pitfall 1: `__getattr__` Not Intercepting Parent Methods
**What goes wrong:** `__getattr__` is never called for methods defined on parent classes via MRO.
**Why it happens:** Python finds the method on the parent class before falling through to `__getattr__`.
**How to avoid:** Rely on the indirect path: parent method accesses `self._repository` (which doesn't exist) -> triggers `__getattr__`. Or explicitly override known methods.
**Warning signs:** Tests pass but error message comes from wrong place (AttributeError on `_repository` vs RuntimeError with message).

### Pitfall 2: `__getattr__` Infinite Loop with Instance Attributes
**What goes wrong:** Accessing `self._error_message` inside `__getattr__` triggers `__getattr__` recursively.
**Why it happens:** If `_error_message` is not in the instance dict, accessing it calls `__getattr__` again.
**How to avoid:** Use `object.__setattr__(self, "_error_message", ...)` in `__init__` to bypass any custom setattr and ensure the attribute lands in the instance dict.
**Warning signs:** `RecursionError` in tests.

### Pitfall 3: asynccontextmanager with try/except and yield
**What goes wrong:** The `yield` must appear exactly once in an `@asynccontextmanager`. With try/except, you need a yield in each branch.
**Why it happens:** Python's contextlib requires the generator to yield exactly once.
**How to avoid:** Structure as try/except where the except branch also yields. Both paths yield a dict with `"service"` key.
**Warning signs:** `RuntimeError: generator didn't yield` or `RuntimeError: generator didn't stop`.

### Pitfall 4: ExceptionGroup from lifespan errors in tests
**What goes wrong:** Current test `test_default_real_bridge_fails_at_startup` expects `ExceptionGroup` from lifespan errors. After this phase, the lifespan catches the error instead of propagating it.
**Why it happens:** The try/except now absorbs the error that previously bubbled up.
**How to avoid:** Update the test to verify degraded-mode behavior instead of catching `ExceptionGroup`.
**Warning signs:** Existing test starts failing with "ExceptionGroup not raised".

### Pitfall 5: mypy strict mode with `__getattr__` return type
**What goes wrong:** mypy complains about `__getattr__` returning `Any` or the method raising unconditionally.
**Why it happens:** Project uses `strict = true` mypy and `from __future__ import annotations`.
**How to avoid:** Type `__getattr__` as `-> NoReturn` if it always raises, or `-> Any` with appropriate handling.
**Warning signs:** mypy errors in pre-commit hook.

## Code Examples

### ErrorOperatorService (Recommended Implementation)

```python
# Source: Project analysis + Python __getattr__ semantics
from __future__ import annotations

import logging
from typing import TYPE_CHECKING, Any, NoReturn

if TYPE_CHECKING:
    from omnifocus_operator.models._snapshot import DatabaseSnapshot

logger = logging.getLogger("omnifocus_operator")


class ErrorOperatorService(OperatorService):
    """Drop-in replacement that raises on every method call.

    Skips ``super().__init__()`` deliberately so ``self._repository``
    does not exist.  Any method inherited from ``OperatorService``
    that accesses ``self._repository`` triggers ``__getattr__``,
    which raises with the startup error message.
    """

    def __init__(self, error: Exception) -> None:
        # Use object.__setattr__ to put _error_message in instance dict
        # without triggering __getattr__ on future access.
        object.__setattr__(self, "_error_message",
            f"OmniFocus Operator failed to start:\n\n{error!s}\n\n"
            "Restart the server after fixing."
        )

    def __getattr__(self, name: str) -> NoReturn:
        logger.warning("Tool call in error mode (attribute: %s)", name)
        raise RuntimeError(self._error_message)
```

### Modified app_lifespan

```python
@asynccontextmanager
async def app_lifespan(app: FastMCP) -> AsyncIterator[dict[str, object]]:
    try:
        # ... existing initialization code (unchanged) ...
        yield {"service": service}
        logger.info("Server shutting down")
    except Exception as exc:
        logger.exception("Fatal error during startup")
        error_service = ErrorOperatorService(exc)
        yield {"service": error_service}
        logger.info("Error-mode server shutting down")
```

### Simplified __main__.py

```python
def main() -> None:
    logging.basicConfig(
        level=os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO").upper(),
        format="%(asctime)s [%(levelname)s] %(name)s: %(message)s",
        stream=sys.stderr,
    )
    from omnifocus_operator.server import create_server
    server = create_server()
    server.run(transport="stdio")
```

## Validation Architecture

### Test Framework
| Property | Value |
|----------|-------|
| Framework | pytest + pytest-asyncio |
| Config file | `pyproject.toml` [tool.pytest.ini_options] |
| Quick run command | `uv run pytest tests/test_server.py -x` |
| Full suite command | `uv run pytest` |

### Phase Requirements -> Test Map

Since no formal requirement IDs were assigned to Phase 9, the following are derived from the CONTEXT.md decisions:

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| ERR-01 | ErrorOperatorService raises RuntimeError with message on get_all_data | unit | `uv run pytest tests/test_service.py -x -k error` | Needs new tests |
| ERR-02 | ErrorOperatorService.__getattr__ raises for any attribute | unit | `uv run pytest tests/test_service.py -x -k error` | Needs new tests |
| ERR-03 | app_lifespan catches exceptions and yields ErrorOperatorService | integration | `uv run pytest tests/test_server.py -x -k error` | Needs new tests |
| ERR-04 | Tool call through error service returns isError=True with message | integration | `uv run pytest tests/test_server.py -x -k degraded` | Needs new tests |
| ERR-05 | __main__.py no longer has pre-async validation | unit | `uv run pytest tests/test_server.py -x` | Existing test needs update |
| ERR-06 | Traceback logged to stderr at ERROR level on startup failure | integration | `uv run pytest tests/test_server.py -x -k error_log` | Needs new tests |
| ERR-07 | WARNING logged for each tool call in error mode | integration | `uv run pytest tests/test_server.py -x -k warning` | Needs new tests |

### Sampling Rate
- **Per task commit:** `uv run pytest tests/test_server.py tests/test_service.py -x`
- **Per wave merge:** `uv run pytest`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps
- [ ] Error service unit tests in `tests/test_service.py` (ERR-01, ERR-02)
- [ ] Degraded mode integration tests in `tests/test_server.py` (ERR-03, ERR-04, ERR-06, ERR-07)
- [ ] Update existing `test_default_real_bridge_fails_at_startup` to verify degraded mode instead of ExceptionGroup (ERR-05)

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Pre-async validation in `__main__.py` | Lifespan try/except with ErrorOperatorService | This phase | Removes fragile workaround, errors visible through tool calls |
| Crash on startup error | Degraded mode serving errors | This phase | MCP server stays alive, agent discovers error on first tool call |

## Open Questions

1. **`__getattr__` type annotation for mypy strict**
   - What we know: `NoReturn` is correct since it always raises. mypy strict should accept this.
   - What's unclear: Whether the `from __future__ import annotations` + mypy strict combination has any edge cases with `NoReturn` on `__getattr__`.
   - Recommendation: Use `NoReturn`, fix if mypy complains.

2. **WARNING log content for `__getattr__`-intercepted calls**
   - What we know: `__getattr__` receives the attribute name (e.g., `_repository`), not the tool name (e.g., `list_all`).
   - What's unclear: Whether the user prefers the attribute name in the log or wants explicit method overrides for tool-name logging.
   - Recommendation: Log the attribute name in `__getattr__`. The tool name is already visible in the MCP protocol layer. Keeping it simple matches "Claude's discretion" on implementation details.

## Sources

### Primary (HIGH confidence)
- MCP SDK source at `.venv/lib/python3.12/site-packages/mcp/server/lowlevel/server.py:583` -- verified exception-to-error-result conversion
- Project source `server/_server.py` -- verified lifespan structure and tool registration pattern
- Project source `service/_service.py` -- verified OperatorService has single method `get_all_data` accessing `self._repository`
- Project source `__main__.py` -- verified pre-async validation code to remove

### Secondary (MEDIUM confidence)
- Python `__getattr__` semantics from Python data model documentation -- standard behavior, well-understood

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH - No new dependencies, all changes are in existing project code
- Architecture: HIGH - Pattern is simple, verified against MCP SDK source, and well-constrained by user decisions
- Pitfalls: HIGH - Identified from code analysis, each has clear mitigation

**Research date:** 2026-03-06
**Valid until:** 2026-04-06 (stable -- no external dependencies changing)
