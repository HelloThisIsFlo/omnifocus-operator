# Phase 31: Middleware & Logging - Research

**Researched:** 2026-03-26
**Domain:** FastMCP middleware, Python logging (stdlib), dual-handler setup
**Confidence:** HIGH

## Summary

Phase 31 replaces manual `log_tool_call()` with FastMCP's `Middleware` base class and redesigns the logging setup from single FileHandler to dual-handler (stderr + rotating file) under proper `omnifocus_operator.*` namespace hierarchy.

All building blocks are proven: the spike (exp 05) provides a copy-paste-ready `ToolLoggingMiddleware`, the middleware API is stable and minimal (`Middleware` base class + `MiddlewareContext`), and Python's stdlib `logging` covers the dual-handler design with zero dependencies.

**Primary recommendation:** Implement in two waves -- (1) middleware + delete `log_tool_call()`, (2) logging redesign in `__main__.py` + `__name__` logger convention across modules.

<user_constraints>

## User Constraints (from CONTEXT.md)

### Locked Decisions

- **D-01:** `ToolLoggingMiddleware` lives in new `src/omnifocus_operator/middleware.py`
- **D-02:** Middleware takes injected `logging.Logger` via constructor (not `__name__`)
- **D-03:** `server.py` passes its own logger: `mcp.add_middleware(ToolLoggingMiddleware(logger))`
- **D-04:** Log full tool arguments at INFO on entry
- **D-05:** Delete `log_tool_call()` and all 6 call sites
- **D-06:** Keep response-shape `logger.debug()` in each handler (task counts, names, warning flags)
- **D-07:** All loggers use `logging.getLogger(__name__)` convention
- **D-08:** Root logger `omnifocus_operator` configured in `__main__.py` with StreamHandler(stderr) + RotatingFileHandler
- **D-09:** Child loggers inherit both handlers via propagation
- **D-10:** Both handlers same level, controlled by `OMNIFOCUS_LOG_LEVEL` env var (default `INFO`)
- **D-11:** RotatingFileHandler with 5MB max, 3 backups
- **D-12:** Remove emoji startup banner

### Claude's Discretion

- Log format strings (timestamp format, level padding, etc.)
- Separator style in middleware entry/exit logs (`>>>` / `<<<` vs alternatives)

### Deferred Ideas (OUT OF SCOPE)

None

</user_constraints>

<phase_requirements>

## Phase Requirements

| ID | Description | Research Support |
|----|-------------|------------------|
| MW-01 | `ToolLoggingMiddleware` logs tool entry, exit (timing), errors automatically | Spike `05_middleware.py` provides reference impl; `Middleware` base class + `on_call_tool` hook verified |
| MW-02 | `log_tool_call()` function and all 6 call sites deleted from server.py | Grep confirms: 1 function def (line 55) + 6 call sites (lines 126, 143, 156, 169, 204, 279) |
| MW-03 | Middleware fires for every tool call without manual wiring | `mcp.add_middleware()` appends to server's middleware list; fires automatically on every `on_call_tool` |
| LOG-01 | `StreamHandler(stderr)` active | Spike exp 03 proved stderr not hijacked; `StreamHandler(sys.stderr)` is safe under stdio transport |
| LOG-02 | `FileHandler(~/Library/Logs/omnifocus-operator.log)` active | Current `__main__.py` already creates this path; switch to `RotatingFileHandler` per D-11 |
| LOG-03 | Logger hierarchy uses `omnifocus_operator.*` namespace | Change all 10 modules from `getLogger("omnifocus_operator")` to `getLogger(__name__)` |
| LOG-04 | stderr hijacking misdiagnosis comment removed | Lines 15-17 of `__main__.py` -- the TODO comment referencing Phase 31 |
| LOG-05 | `ctx.info()` / `ctx.warning()` not used anywhere | Already satisfied -- grep confirms zero uses in `src/omnifocus_operator/` |

</phase_requirements>

## Standard Stack

### Core

| Library | Version | Purpose | Why Standard |
|---------|---------|---------|--------------|
| `fastmcp` | 3.1.1 (latest; 3.1.0 installed) | `Middleware` base class, `MiddlewareContext` | Project dependency; middleware API stable since 3.0 |
| `logging` (stdlib) | n/a | Dual-handler setup, logger hierarchy | Python stdlib; zero deps |
| `logging.handlers.RotatingFileHandler` (stdlib) | n/a | File rotation with size limit | Stdlib; proven, zero maintenance |

### Supporting

None needed -- this phase uses only project dependency (`fastmcp`) and stdlib.

### Alternatives Considered

| Instead of | Could Use | Tradeoff |
|------------|-----------|----------|
| RotatingFileHandler | TimedRotatingFileHandler | Time-based rotation adds complexity; size-based is simpler for a log that grows on tool calls |
| `logging.getLogger(__name__)` per module | Single root logger everywhere | Loses per-module granularity in log output; `__name__` is Python convention |

## Architecture Patterns

### Module Map After Phase 31

```
src/omnifocus_operator/
  __main__.py          # Root logger config: dual handler + env var level
  middleware.py        # NEW: ToolLoggingMiddleware class
  server.py            # log_tool_call() DELETED; add_middleware() wired in create_server()
  service/             # getLogger(__name__) in each module (was hardcoded "omnifocus_operator")
  repository/          # getLogger(__name__) in each module
  bridge/              # getLogger(__name__) in each module
```

### Pattern 1: Middleware with Injected Logger

**What:** `ToolLoggingMiddleware` receives a `logging.Logger` via constructor, logs entry/timing/errors for every tool call.
**When to use:** Cross-cutting concerns that apply to all tools.

```python
# Source: spike experiments/05_middleware.py (verified working)
from fastmcp.server.middleware import Middleware, MiddlewareContext

class ToolLoggingMiddleware(Middleware):
    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    async def on_call_tool(self, context, call_next):
        tool_name = context.message.name      # CallToolRequestParams.name
        args = context.message.arguments       # CallToolRequestParams.arguments
        self._log.info(">>> %s(%s)", tool_name, args) if args else self._log.info(">>> %s()", tool_name)
        start = time.monotonic()
        try:
            result = await call_next(context)
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.info("<<< %s -- %.1fms OK", tool_name, elapsed_ms)
            return result
        except Exception as e:
            elapsed_ms = (time.monotonic() - start) * 1000
            self._log.error("!!! %s -- %.1fms FAILED: %s", tool_name, elapsed_ms, e)
            raise
```

### Pattern 2: Root Logger with Dual Handlers

**What:** Configure root `omnifocus_operator` logger once in `__main__.py`; child loggers inherit via propagation.
**When to use:** Application entry point.

```python
# Source: spike FINDINGS.md exp 02 format decisions
import logging
import sys
from logging.handlers import RotatingFileHandler

def _configure_logging() -> None:
    level = os.environ.get("OMNIFOCUS_LOG_LEVEL", "INFO").upper()
    root = logging.getLogger("omnifocus_operator")
    root.setLevel(level)
    root.propagate = False  # Don't leak to Python root logger

    # Handler 1: stderr (Claude Desktop log page)
    stderr_handler = logging.StreamHandler(sys.stderr)
    stderr_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
        datefmt="%H:%M:%S",
    ))
    root.addHandler(stderr_handler)

    # Handler 2: rotating file (persistent; fallback for Claude Code)
    # Claude Code swallows stderr during tool execution:
    # https://github.com/anthropics/claude-code/issues/29035
    # This handler may become redundant when that issue is resolved.
    log_path = os.path.expanduser("~/Library/Logs/omnifocus-operator.log")
    os.makedirs(os.path.dirname(log_path), exist_ok=True)
    file_handler = RotatingFileHandler(
        log_path, maxBytes=5_000_000, backupCount=3,
    )
    file_handler.setFormatter(logging.Formatter(
        "%(asctime)s %(levelname)-8s [%(name)s] %(message)s",
    ))
    root.addHandler(file_handler)
```

### Pattern 3: `__name__` Logger Convention

**What:** Every module uses `logger = logging.getLogger(__name__)`.
**When to use:** Every Python module that logs.

```python
# In any module, e.g. omnifocus_operator/service/service.py
logger = logging.getLogger(__name__)
# Resolves to "omnifocus_operator.service.service"
# Inherits handlers from "omnifocus_operator" root via propagation
```

### Anti-Patterns to Avoid

- **Hardcoded logger names:** `getLogger("omnifocus_operator")` in every module flattens the namespace hierarchy. Use `__name__`.
- **Adding handlers to child loggers:** Only the root `omnifocus_operator` logger should have handlers. Children inherit via `propagate=True` (the default).
- **Using `get_logger()` from FastMCP:** Returns `fastmcp.*` namespace, no logger name in output. Wrong namespace for project logs.
- **Using `ctx.info()` / `ctx.warning()`:** No client renders these. Dead end.

## Don't Hand-Roll

| Problem | Don't Build | Use Instead | Why |
|---------|-------------|-------------|-----|
| Per-tool logging | Manual `log_tool_call()` in each handler | `ToolLoggingMiddleware` via `Middleware` base class | Automatic, can't forget, no boilerplate |
| Log rotation | Custom file management | `RotatingFileHandler(maxBytes=5_000_000, backupCount=3)` | Stdlib, atomic, thread-safe |
| Logger hierarchy | Manual handler setup per module | `getLogger(__name__)` + root logger propagation | Python's logger tree does this natively |

## Common Pitfalls

### Pitfall 1: Forgetting `propagate = False` on Root Logger

**What goes wrong:** Log messages appear twice (once from `omnifocus_operator` handlers, once from Python's root logger).
**Why it happens:** `propagate` defaults to `True`. If Python's root logger has a handler (some libraries add one), messages bubble up.
**How to avoid:** Set `root.propagate = False` on the `omnifocus_operator` root logger only.
**Warning signs:** Duplicate log lines, especially at WARNING+ level.

### Pitfall 2: Middleware Return Value

**What goes wrong:** Middleware doesn't return the result from `call_next()`, causing tool to return `None`.
**Why it happens:** Easy to forget `return result` in the try block.
**How to avoid:** Always `return await call_next(context)`.
**Warning signs:** Tools returning empty/None results.

### Pitfall 3: Logger Level on Children vs Root

**What goes wrong:** Child logger has a more restrictive level, silently filters messages.
**Why it happens:** Calling `setLevel()` on a child logger overrides inheritance.
**How to avoid:** Only call `setLevel()` on the root `omnifocus_operator` logger. Children inherit it.
**Warning signs:** Missing log messages from specific modules.

### Pitfall 4: RotatingFileHandler Directory Creation

**What goes wrong:** `RotatingFileHandler` fails if `~/Library/Logs/` doesn't exist.
**Why it happens:** `RotatingFileHandler` doesn't create parent directories.
**How to avoid:** `os.makedirs(os.path.dirname(log_path), exist_ok=True)` before creating handler.
**Warning signs:** `FileNotFoundError` at startup.

### Pitfall 5: `context.message` Attribute Path

**What goes wrong:** Using wrong attribute name to access tool call details.
**Why it happens:** API confusion -- `message` is the `CallToolRequestParams` object.
**How to avoid:** Verified API: `context.message.name` (tool name), `context.message.arguments` (dict or None).
**Warning signs:** `AttributeError` in middleware.

## Code Examples

### Wiring Middleware in `create_server()`

```python
# In server.py, inside create_server():
def create_server() -> FastMCP:
    mcp = FastMCP("omnifocus-operator", lifespan=app_lifespan)
    _register_tools(mcp)
    # D-03: Server passes its own logger
    mcp.add_middleware(ToolLoggingMiddleware(logger))
    return mcp
```

### Modules Requiring Logger Name Change

10 modules change from `getLogger("omnifocus_operator")` to `getLogger(__name__)`:

| File | Current | After |
|------|---------|-------|
| `server.py:52` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.server` |
| `service/service.py:37` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.service.service` |
| `service/domain.py:47` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.service.domain` |
| `service/payload.py:23` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.service.payload` |
| `service/resolve.py:22` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.service.resolve` |
| `repository/factory.py:22` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.repository.factory` |
| `repository/hybrid.py:45` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.repository.hybrid` |
| `repository/bridge.py:26` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.repository.bridge` |
| `bridge/real.py:25` | `getLogger("omnifocus_operator")` | `getLogger(__name__)` → `omnifocus_operator.bridge.real` |
| `simulator/__main__.py:30` | `getLogger("omnifocus_operator.simulator")` | `getLogger(__name__)` → `omnifocus_operator.simulator.__main__` |

Note: `__main__.py` root logger uses `getLogger("omnifocus_operator")` (hardcoded) -- this is correct because it IS the root of the hierarchy, not a child.

### Deleting `log_tool_call()`

```python
# DELETE: server.py lines 55-65 (function definition)
# DELETE: server.py line 126  -- log_tool_call("get_all")
# DELETE: server.py line 143  -- log_tool_call("get_task", id=id)
# DELETE: server.py line 156  -- log_tool_call("get_project", id=id)
# DELETE: server.py line 169  -- log_tool_call("get_tag", id=id)
# DELETE: server.py line 204  -- log_tool_call("add_tasks", items=len(items))
# DELETE: server.py line 279  -- log_tool_call("edit_tasks", items=len(items))
# KEEP:  logger.debug() lines in each handler (D-06)
```

## State of the Art

| Old Approach | Current Approach | When Changed | Impact |
|--------------|------------------|--------------|--------|
| Manual `log_tool_call()` per handler | `Middleware.on_call_tool()` | FastMCP 3.0 | Zero-boilerplate logging for all current + future tools |
| Single FileHandler | Dual StreamHandler + RotatingFileHandler | Spike finding | Visible in Claude Desktop AND persistent |
| Hardcoded `"omnifocus_operator"` name | `__name__` convention | Python best practice | Per-module granularity in log output |
| Emoji startup banner | Rely on FastMCP's built-in banner | D-12 | Cleaner startup, no custom noise |

## Validation Architecture

### Test Framework

| Property | Value |
|----------|-------|
| Framework | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| Config file | `pyproject.toml` `[tool.pytest.ini_options]` |
| Quick run command | `uv run pytest tests/test_server.py -x -q --no-cov` |
| Full suite command | `uv run pytest --timeout=30` |

### Phase Requirements --> Test Map

| Req ID | Behavior | Test Type | Automated Command | File Exists? |
|--------|----------|-----------|-------------------|-------------|
| MW-01 | Middleware logs entry, timing, errors | unit | `uv run pytest tests/test_middleware.py -x -q --no-cov` | -- Wave 0 |
| MW-02 | `log_tool_call()` deleted | grep check | `! grep -r 'log_tool_call' src/` | n/a (structural) |
| MW-03 | Middleware fires without manual wiring | integration | `uv run pytest tests/test_server.py -x -q --no-cov` (existing tests pass = no regression) | -- existing |
| LOG-01 | StreamHandler(stderr) active | unit | `uv run pytest tests/test_middleware.py -x -q --no-cov` | -- Wave 0 |
| LOG-02 | RotatingFileHandler active | unit | `uv run pytest tests/test_middleware.py -x -q --no-cov` | -- Wave 0 |
| LOG-03 | `omnifocus_operator.*` namespace | grep check | `grep -r 'getLogger("omnifocus_operator")' src/ \| grep -v __main__` should return 0 | n/a (structural) |
| LOG-04 | Misdiagnosis comment removed | grep check | `! grep -r 'hijack' src/` | n/a (structural) |
| LOG-05 | No `ctx.info()`/`ctx.warning()` in production | grep check | `! grep -rP 'ctx\.(info\|warning)\(' src/` | n/a (structural; already passing) |

### Sampling Rate

- **Per task commit:** `uv run pytest tests/test_server.py tests/test_middleware.py -x -q --no-cov`
- **Per wave merge:** `uv run pytest --timeout=30`
- **Phase gate:** Full suite green before `/gsd:verify-work`

### Wave 0 Gaps

- [ ] `tests/test_middleware.py` -- MW-01 (middleware logs correctly), LOG-01/LOG-02 (handler setup)
- [ ] Middleware tests need: mock logger to capture log calls, verify entry/exit/error messages, verify timing is non-zero

## Open Questions

1. **`simulator/__main__.py` logger name**
   - What we know: Currently uses `getLogger("omnifocus_operator.simulator")`, `__name__` would give `omnifocus_operator.simulator.__main__`
   - What's unclear: Is the `.__main__` suffix desirable for the simulator?
   - Recommendation: Use `__name__` for consistency. The suffix is a cosmetic detail in log lines. Simulator is a separate entry point, not a production concern.

2. **Middleware added before or after `_register_tools()`?**
   - What we know: `mcp.add_middleware()` appends to a list; order determines execution order (outer to inner)
   - What's unclear: Whether ordering matters when there's only one middleware
   - Recommendation: Add after `_register_tools()` for readability (register tools, then configure cross-cutting). Functionally equivalent.

## Sources

### Primary (HIGH confidence)

- FastMCP 3.1.0 installed -- `Middleware`, `MiddlewareContext` classes inspected directly via `inspect.getsource()`
- `MiddlewareContext.message` is `CallToolRequestParams` with `.name` and `.arguments` attributes (verified)
- `Middleware.on_call_tool(self, context, call_next) -> ToolResult` signature confirmed
- `RotatingFileHandler(filename, maxBytes=0, backupCount=0)` stdlib signature confirmed
- Spike `experiments/05_middleware.py` -- working reference implementation
- Spike `experiments/03_server_logging.py` -- stderr safety proof
- Spike `FINDINGS.md` -- exp 02 (logging decisions), exp 03 (stderr verdict), exp 05 (middleware verdict)

### Secondary (MEDIUM confidence)

- PyPI: FastMCP 3.1.1 is latest (project requires `>=3.1.1`, 3.1.0 installed -- will resolve via `uv sync`)

### Tertiary (LOW confidence)

None -- all findings verified against installed code and spike experiments.

## Metadata

**Confidence breakdown:**
- Standard stack: HIGH -- all components are stdlib or already-installed project dependency
- Architecture: HIGH -- spike provides working reference implementations; API verified via source inspection
- Pitfalls: HIGH -- all identified from spike experiment experience and Python logging well-known gotchas

**Research date:** 2026-03-26
**Valid until:** 2026-04-26 (stable domain -- Python logging stdlib + FastMCP middleware API)
