# FastMCP v3 Spike — Findings

> Built up during experimentation. Each section filled in after running.

## Exp 01: Server & Context

**Verdict:** Migration pattern works cleanly. No blockers.

**Observations:**
- Import: `from mcp.server.fastmcp import FastMCP, Context` → `from fastmcp import FastMCP, Context`
- `ToolAnnotations` stays at `mcp.types` — unchanged
- Both `ctx.request_context.lifespan_context` and `ctx.lifespan_context` work — migrate at our pace
- Lifespan pattern (context manager injecting service) works identically

**Surprises:**
- 34 attributes on `ctx` — much richer than expected. `elicit`, `report_progress`, `sample`, state management, component visibility control
- `client_id` and `transport` are `None` in test client — expected but worth noting for assertions

**Migration impact:**
- Find-and-replace imports (mechanical)
- Optional: shorten `ctx.request_context.lifespan_context` → `ctx.lifespan_context`


## Exp 02: Client vs Server Logging

**Verdict:** `ctx.info()` is pointless for us. Plain Python `StreamHandler` to stderr is the path forward for developer diagnostics. Not FastMCP-specific — works with old `mcp` SDK too.

**Observations:**
- Three logging paths tested: `ctx.info()`, `get_logger()`, plain `StreamHandler` to stderr
- `ctx.info()` → protocol `notifications/message`. No major client renders these in conversation UI. Claude Code issue #3174 closed as "not planned". Research confirmed: only MCP Inspector shows them.
- `get_logger()` → writes to stderr via FastMCP's Rich handler. No logger name in output, effective level INFO (filters debug), no handlers of its own (relies on `fastmcp` root propagation)
- Plain `StreamHandler(stderr)` → full control: logger name visible, all levels, custom formatter
- `FileHandler` with `propagate=False` → file only, never appears on any client log page

**Client visibility matrix:**

| What | Claude Desktop log page | Claude Code |
|------|------------------------|-------------|
| `ctx.info()` / `ctx.warning()` | Shows as `notifications/message` | Invisible |
| `StreamHandler` to stderr | Shows as captured stderr | Invisible during tool calls ([issue #29035](https://github.com/anthropics/claude-code/issues/29035)) |
| `FileHandler` to file | Invisible | Tail the file yourself |

**Decisions:**
- Agent-facing warnings → stay in response payload (our existing design, first-class, works everywhere)
- Developer diagnostics → dual handler: `StreamHandler(stderr)` primary (Claude Desktop), `FileHandler(~/Library/Logs/omnifocus-operator.log)` fallback
- `ctx.info()` → skip entirely
- Logger hierarchy: `omnifocus_operator.service`, `omnifocus_operator.service.add_tasks`, etc.
- Format (stderr — live debugging):
  - `%(asctime)s %(levelname)-8s [%(name)s] %(message)s` with `datefmt="%H:%M:%S"`
  - Produces: `21:04:07 DEBUG    [omnifocus_operator.service] Cache hit for tag 'Work'`
- Format (file — persistent, needs date for context across sessions):
  - `%(asctime)s %(levelname)-8s [%(name)s] %(message)s` (default `asctime`, no `datefmt`)
  - Produces: `2026-03-24 21:04:07,591 DEBUG    [omnifocus_operator.service] Cache hit for tag 'Work'`

**`get_logger()` internals (for reference):**
- `get_logger("foo")` → `logging.getLogger("fastmcp.foo")` — prefixes with `fastmcp.`
- No handlers, propagates to `fastmcp` root (Rich handler at INFO)
- `name=` kwarg vs positional → no difference
- `.setLevel(DEBUG)` overrides parent's INFO filter

**Key surprise:** Logging story is independent of the FastMCP migration. `StreamHandler` to stderr works with the old `mcp` SDK too — we just never checked Claude Desktop's log page before.

### Gotcha: `ctx.info()` / `ctx.warning()` is a dead end

FastMCP prominently documents `ctx.info()`, `ctx.warning()`, `ctx.error()` as "client logging" — sending messages from the server to the client. Sounds great. In practice: **no major MCP client shows these to the user or the LLM.**

- Claude Desktop: not in the chat UI. Only visible in the developer log page as raw protocol entries.
- Claude Code: completely invisible. Issue [#3174](https://github.com/anthropics/claude-code/issues/3174) was filed and **closed as "not planned"**.
- Cursor: [confirmed not rendered](https://forum.cursor.com/t/bug-report-cursor-ui-not-displaying-mcp-progress-updates/134794).
- VS Code: only recently added to a developer output pane, not in chat.
- MCP Inspector: the only client that renders them — and that's a dev tool.

The MCP spec says clients "MAY" present log messages. In practice, none do. Every GitHub example using `ctx.info()` is tutorial/demo code. No production MCP server uses it for meaningful work. Don't waste time trying to make it work — it doesn't.

### Gotcha: Claude Code swallows stderr during tool execution

`StreamHandler` to stderr works beautifully on Claude Desktop's log page. On Claude Code: **stderr output only appears at server startup, not during tool calls.** The MCP log files at `~/Library/Caches/claude-cli-nodejs/.../mcp-logs-*/` confirm this — they log "Calling MCP tool" and "completed successfully" but none of the stderr content.

Open issue: [anthropics/claude-code#29035](https://github.com/anthropics/claude-code/issues/29035). Until resolved, use `FileHandler` as a fallback for Claude Code debugging (`~/Library/Logs/omnifocus-operator.log`).

## Exp 03: stderr Hijacking

**Verdict:** stderr is **NOT hijacked** by either SDK. `StreamHandler(stderr)` is safe under stdio transport.

**Observations:**
- Tested both SDKs with the same script (`old` / `new` CLI arg):
  - Old `mcp` SDK (`mcp.server.fastmcp`): `sys.stderr is sys.__stderr__` → `True`
  - FastMCP v3 (`fastmcp`): `sys.stderr is sys.__stderr__` → `True`
- Direct `sys.stderr.write()` succeeds, no protocol corruption
- `StreamHandler(stderr)` with 4 log levels: all written, tool response returned correctly
- Both SDKs only wrap `stdin` and `stdout` for JSON-RPC — stderr is left untouched

### Gotcha: stderr hijacking in the base `mcp` SDK was a misdiagnosis

Our `__main__.py:15` says `"stdio_server() hijacks stderr"` — this was the original reason we used `FileHandler` instead of `StreamHandler`, and **one of the main drivers for considering the FastMCP v3 migration.** Turns out it was completely wrong.

What actually happened: we tested logging in **Claude Code**, saw nothing on stderr, and concluded the SDK was hijacking it. But the SDK never touched stderr — it was **Claude Code swallowing stderr during tool execution** (see Gotcha above, issue [#29035](https://github.com/anthropics/claude-code/issues/29035)). If we'd checked Claude Desktop's log page back then, we'd have seen our stderr output all along.

This means:
- `StreamHandler(stderr)` was always safe, on both the old `mcp` SDK and FastMCP v3
- The `FileHandler` workaround was unnecessary from day one
- **Logging is not a reason to migrate to FastMCP v3** — the logging story is identical on both SDKs
- The migration may still be worth it for other reasons (test client, cleaner API) — that's what the remaining experiments will determine

## Exp 04: Test Client

**Verdict:** Pass. Massive DX improvement — ~70 lines of test plumbing replaced by 3 lines.

**Before vs after:**

```
CURRENT conftest.py (lines 439-481, 40+ lines):
┌──────────────────────────────────────────────────────────┐
│ class _ClientSessionProxy:                               │
│     async def _with_session(self, method, args, kwargs): │
│         s2c_send, s2c_recv = anyio.create_memory_...     │
│         c2s_send, c2s_recv = anyio.create_memory_...     │
│         async with anyio.create_task_group() as tg:      │
│             tg.start_soon(_run_server)                   │
│             async with ClientSession(...) as session:    │
│                 await session.initialize()               │
│                 result = await getattr(session, ...)     │
│                 tg.cancel_scope.cancel()                 │
│         return result                                    │
│     async def call_tool(self, *args, **kwargs):          │
│     async def list_tools(self, *args, **kwargs):         │
└──────────────────────────────────────────────────────────┘

FASTMCP v3 (3 lines):
┌──────────────────────────────────────────────────────────┐
│ async with Client(server) as client:                     │
│     result = await client.call_tool("tool", {})          │
└──────────────────────────────────────────────────────────┘
```

**What was tested:**
- Basic tool call + list_tools: works
- State persistence across calls within a session: works
- Error handling: tool exceptions wrapped as `ToolError` (raises, not `is_error=True`)
- Session isolation: lifespan re-runs per `Client()` session, service state shared if externally owned

**Adaptation points (not blockers):**
- `result.data` returns Pydantic `Root()` objects for list returns instead of raw dicts — need to check extraction pattern for test assertions
- Error handling: raises `ToolError` instead of returning `CallToolResult(is_error=True)` — tests need different assertion pattern
- Both are small test refactors, not architectural changes

**Migration impact:**
- Delete `_ClientSessionProxy` (conftest.py:439-481)
- Delete `run_with_client` (test_server.py:51-82)
- Remove `anyio`, `ClientSession`, `SessionMessage` imports from test infra
- Update test assertions for the two adaptation points above

## Exp 05: Middleware

**Verdict:** Pass. Huge DX win — replaces manual `log_tool_call()` with automatic, stackable middleware.

**What it replaces:**
- `server.py:53-63` — manual `log_tool_call()` function
- 6 call sites where `log_tool_call("tool_name", ...)` is called explicitly at the top of each tool handler
- Middleware fires automatically for every tool call — no manual wiring

**Pattern (reference implementation in `experiments/05_middleware.py`):**
```python
class ToolLoggingMiddleware(Middleware):
    def __init__(self, logger: logging.Logger) -> None:
        self._log = logger

    async def on_call_tool(self, context: MiddlewareContext, call_next):
        tool_name = context.message.name
        args = context.message.arguments
        self._log.info(f">>> {tool_name}({args})" if args else f">>> {tool_name}()")
        start = time.monotonic()
        try:
            result = await call_next(context)
            self._log.info(f"<<< {tool_name} — {elapsed_ms:.1f}ms OK")
            return result
        except Exception as e:
            self._log.error(f"!!! {tool_name} — {elapsed_ms:.1f}ms FAILED: {e}")
            raise

# One class, two instances — different destinations, same logic
mcp.add_middleware(ToolLoggingMiddleware(stderr_logger))
mcp.add_middleware(ToolLoggingMiddleware(file_logger))
```

**Observations:**
- Multiple middleware stack and both fire for every call
- `context.message.name` for tool name, `context.message.arguments` for args (per official docs)
- Error handling works across the stack — exception propagates through all middleware
- Clean separation: middleware handles cross-cutting concerns, tools stay focused on business logic

**Migration impact:**
- Delete `log_tool_call()` and all 6 call sites
- Add `ToolLoggingMiddleware` class + `create_logger` factory (experiment file is a reference implementation, adapt as needed)


## Exp 06: Progress

**Verdict:** Pass — works beautifully in Claude Code. Worth adding to batch operations.

**How it looks in Claude Code (real output):**
```
  ⎿  █▋                   8%
  ⎿  ███████▉             39%
  ⎿  █████████████        65%
  ⎿  ████████████████████ 100%
```

**Client support:**
- Claude Code CLI: **YES** — renders a real progress bar with percentage. Looks great.
- Claude Desktop: no rendering (tested)
- Cursor: reportedly sends `progressToken` but UI broken (not tested, from research)
- MCP Inspector: reportedly broken (not tested, from research)

**Observations:**
- `process_batch` (known total): perfect progress bar with percentage
- `process_with_messages` (`ctx.info()` + progress): messages are invisible (as expected from exp 02), but progress bar works fine
- `process_unknown_total` (no total): works but looks weird — just shows a number, no bar. Usable but not as nice.

**Migration impact:**
- Add `await ctx.report_progress(progress=i, total=total)` to `add_tasks` and `edit_tasks` batch loops
- Trivial to add — the API no-ops gracefully when the client doesn't send a `progressToken`
- No fallback needed: clients that don't support it simply don't see it

**Research note:** The background agent reported zero clients support progress. That was wrong — Claude Code CLI renders it perfectly. Always verify with real clients.

## Exp 07: Dependency Injection


## Exp 08: Elicitation


---

## Go / No-Go Decision

**Decision:**

**Rationale:**

**Migration scope (if go):**
- Must-do:
- Nice-to-have:
- Future milestone:
