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


## Exp 02: Client Logging *(WIP — format selection pending)*

**Verdict (preliminary):** `ctx.info()` / `ctx.warning()` are not useful for us. `StreamHandler` to stderr is the path forward for developer diagnostics.

**Observations:**
- Three logging paths tested: `ctx.info()`, `get_logger()`, plain `StreamHandler` to stderr
- `ctx.info()` → shows on Claude Desktop log page as `notifications/message` AND as FastMCP's internal echo. Not visible to the agent (Claude Code, Claude Desktop both ignore it in conversation)
- `get_logger()` → writes to stderr via FastMCP's Rich handler. Shows on log page. But: no logger name, effective level INFO (filters debug), no handlers of its own (relies on `fastmcp` root)
- Plain `StreamHandler(stderr)` → shows on log page. Full control: logger name visible, debug works, custom formatter
- `file_logger` with `propagate=False` → does NOT appear on log page at all (file only)
- Research confirmed: no major MCP client renders `notifications/message` in the conversation UI. Claude Code issue #3174 was closed as "not planned"

**Key insight:**
- Agent-facing warnings → stay in response payload (our existing design, works everywhere)
- Developer diagnostics → `StreamHandler` to stderr replaces `FileHandler`, shows on Claude Desktop log page
- `ctx.info()` → skip. No real-world value today

**`get_logger()` internals:**
- `get_logger("foo")` returns `logging.getLogger("fastmcp.foo")` — prefixes with `fastmcp.`
- No handlers, propagates to `fastmcp` root which has a Rich handler at INFO
- `name=` kwarg vs positional → no difference
- `.setLevel(DEBUG)` overrides parent's INFO filter

**Still to decide:**
- Formatter pattern — 11 options tested, format selection pending
- Whether to keep FileHandler alongside StreamHandler (belt + suspenders)
- Logger hierarchy design (e.g., `omnifocus_operator.service.add_tasks`)

## Exp 03: Server Logging


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
