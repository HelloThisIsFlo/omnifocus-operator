# Phase 31: Middleware & Logging - Context

**Gathered:** 2026-03-26
**Status:** Ready for planning

<domain>
## Phase Boundary

Replace manual `log_tool_call()` with automatic `ToolLoggingMiddleware`. Redesign logging with dual-handler (stderr + file) under `omnifocus_operator.*` namespace. Delete stderr hijacking misdiagnosis. Ensure `ctx.info()`/`ctx.warning()` are not used in production code.

</domain>

<decisions>
## Implementation Decisions

### Middleware design
- **D-01:** `ToolLoggingMiddleware` lives in a new `src/omnifocus_operator/middleware.py` — dedicated file, clean home for future middleware (v1.6 retry/crash recovery)
- **D-02:** Middleware class takes an injected `logging.Logger` via constructor (like the spike). It does NOT use `__name__` — it receives the server's logger so all MCP-layer log lines show `[omnifocus_operator.server]`
- **D-03:** `server.py` passes its own logger when wiring: `mcp.add_middleware(ToolLoggingMiddleware(logger))`

### Argument logging
- **D-04:** Middleware logs full tool arguments at INFO level on entry. Batch limit is currently 1, so payloads are small. Revisit if batch sizes grow.

### Per-tool handler logs
- **D-05:** Delete `log_tool_call()` function and all 6 call sites — middleware covers entry/exit/timing automatically
- **D-06:** Keep response-shape `logger.debug()` lines in each handler (task counts, names, warning flags). These carry info middleware can't see (it only knows timing + success/failure, not response content)

### Logger hierarchy
- **D-07:** All loggers use `__name__` convention — `logging.getLogger(__name__)` in each module. Module paths (`omnifocus_operator.server`, `omnifocus_operator.service`, etc.) naturally form the namespace hierarchy
- **D-08:** One root logger (`omnifocus_operator`) configured in `__main__.py` with two handlers:
  - `StreamHandler(sys.stderr)` — primary, visible in Claude Desktop logs
  - `RotatingFileHandler(~/Library/Logs/omnifocus-operator.log)` — fallback for Claude Code where stderr is swallowed during tool calls (see `anthropics/claude-code#29035`). Add a comment with this issue link explaining why the file handler exists and that it may become redundant when the issue is resolved
- **D-09:** Child loggers inherit both handlers via propagation — zero handler config per file, just `logger = logging.getLogger(__name__)`
- **D-10:** Both handlers use the same log level, controlled by `OMNIFOCUS_LOG_LEVEL` env var (default `INFO`). One knob.
- **D-11:** `RotatingFileHandler` with 5MB max size, 3 backups (~15MB ceiling). Zero maintenance.

### Startup banner
- **D-12:** Remove the emoji startup banner (`log.warning("...STARTING...")`) from `__main__.py`. FastMCP's own startup banner is sufficient.

### Claude's Discretion
- Log format strings (timestamp format, level padding, etc.) — spike has a reference but exact format is implementation detail
- Whether to keep or adjust the separator style in middleware entry/exit logs (`>>>` / `<<<` from spike vs something else)

</decisions>

<canonical_refs>
## Canonical References

**Downstream agents MUST read these before planning or implementing.**

### Spike reference implementations
- `.research/deep-dives/fastmcp-spike/experiments/05_middleware.py` — ToolLoggingMiddleware reference implementation with injected logger pattern
- `.research/deep-dives/fastmcp-spike/experiments/03_server_logging.py` — Proof that stderr is NOT hijacked under stdio transport
- `.research/deep-dives/fastmcp-spike/FINDINGS.md` — Exp 02 (logging), Exp 03 (stderr), Exp 05 (middleware) findings and decisions

### Current implementation
- `src/omnifocus_operator/server.py` — `log_tool_call()` (lines 55-65), 6 call sites, per-tool `logger.debug()` lines, `create_server()` where middleware would be wired
- `src/omnifocus_operator/__main__.py` — Current logging setup (FileHandler only), TODO comment for Phase 31, emoji startup banner

### Requirements
- `.planning/REQUIREMENTS.md` — MW-01..03, LOG-01..05

### Prior phase decisions
- `.planning/phases/29-dependency-swap-imports/29-CONTEXT.md` — D-09 (built from scratch with fastmcp>=3), D-06 (MCP concerns at handler level), deferred note about logging redesign

### External references
- `anthropics/claude-code#29035` — Claude Code swallows stderr during tool execution (reason for FileHandler fallback)

</canonical_refs>

<code_context>
## Existing Code Insights

### Reusable Assets
- Spike `05_middleware.py` — copy-paste reference for `ToolLoggingMiddleware` class
- Spike `03_server_logging.py` — proof that `StreamHandler(stderr)` is safe under stdio transport

### Established Patterns
- `__name__`-based logger convention already used in some modules
- `logging.getLogger("omnifocus_operator")` already exists in `server.py` (line 52) — rename to `__name__`
- Method Object pattern in service layer — middleware is an analogous pattern at the MCP layer

### Integration Points
- `server.py` line 330: `create_server()` — add `mcp.add_middleware(...)` call
- `server.py` lines 55-65: `log_tool_call()` — delete
- `server.py` lines 126, 143, 156, 169, 204, 279: 6 `log_tool_call(...)` call sites — delete
- `__main__.py` lines 15-27: logging setup — redesign with dual handler + remove emoji banner

</code_context>

<specifics>
## Specific Ideas

- Middleware receives the server's logger via injection, not its own — all MCP-layer logs under one namespace
- FileHandler comment must reference `anthropics/claude-code#29035` and explain the handler may become redundant when that issue is resolved
- FastMCP's built-in startup banner replaces the custom emoji banner

</specifics>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 31-middleware-logging*
*Context gathered: 2026-03-26*
