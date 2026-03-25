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


## Exp 05: Middleware


## Exp 07: Progress


## Exp 08: Dependency Injection


## Exp 09: Elicitation


---

## Go / No-Go Decision

**Decision:**

**Rationale:**

**Migration scope (if go):**
- Must-do:
- Nice-to-have:
- Future milestone:
