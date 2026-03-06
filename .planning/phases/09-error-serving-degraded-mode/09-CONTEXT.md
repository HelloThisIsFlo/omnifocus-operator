# Phase 9: Error-Serving Degraded Mode - Context

**Gathered:** 2026-03-06
**Status:** Ready for planning

<domain>
## Phase Boundary

Instead of crashing on fatal startup errors, enter a degraded mode where the server stays alive and every tool call returns a clear, actionable error message. The agent surfaces the error on first use — no mystery, no log diving. This phase replaces the current fragile pre-async validation workaround in `__main__.py`.

</domain>

<decisions>
## Implementation Decisions

### Error capture scope
- Catch fatal errors inside `app_lifespan` with a generic `except Exception`
- On failure, yield an `ErrorOperatorService` instead of the real `OperatorService`
- Remove the pre-async `.ofocus` path validation from `__main__.py` — simplify to just `create_server()` + `server.run()`
- Keep the explicit `.ofocus` path check inside the lifespan for clear error messages — it gets caught by the generic `except` now instead of crashing
- The lifespan's `except` also logs the full traceback to stderr at ERROR level

### ErrorOperatorService design
- Subclass of `OperatorService` that uses `__getattr__` to dynamically raise on any method call
- Does not call `super().__init__()` — no instance attributes from parent, so all method calls fall through to `__getattr__`
- Future-proof: when new methods are added in later milestones, the error service covers them automatically
- This is Liskov Substitution — tool handlers don't know the difference between the real and error service

### Error message content
- Generic multi-line wrapper format (no per-error-type mapping):
  ```
  OmniFocus Operator failed to start:

  {str(exception)}

  Restart the server after fixing.
  ```
- Multi-line for readability, especially when the inner error message is itself multi-line
- Exception messages are already descriptive (e.g., the `.ofocus` check includes the path and env var hint)
- No log-checking instructions in the tool response — stderr is a debugging aid, not the primary channel

### Tool surface in error mode
- Same tools as the real server — no extra health/status tool
- Agent discovers the error on its first tool call through the normal tool response channel
- Log each degraded-mode tool call at WARNING level (tool name + "server is in error mode")

### Recovery behavior
- Stay in error mode until the process is restarted — no retry logic
- Error message says "Restart the server after fixing" (direct instruction, not agent-meta-instruction)
- Simple and predictable — no risk of partial recovery or flapping

### Claude's Discretion
- Exact `__getattr__` implementation details (closure pattern, method signature)
- Whether to also log at INFO level when entering degraded mode (in addition to ERROR for the traceback)
- Test structure and organization for the new error-serving code

</decisions>

<specifics>
## Specific Ideas

- The `__getattr__` trick ensures zero maintenance burden: no need to manually override each method as `OperatorService` grows across milestones
- The todo spec mentions removing the lifespan error handling workaround — this is exactly what the generic `except` replaces
- The pattern is generic enough to apply to any MCP server, not just this project

</specifics>

<code_context>
## Existing Code Insights

### Reusable Assets
- `_register_tools()` in `_server.py`: Already separated from `create_server()` — tool registration is independent of lifespan logic
- `OperatorService` in `service/_service.py`: The class that `ErrorOperatorService` will subclass
- MCP SDK's built-in error handling: `except Exception` at line 446 of `lowlevel/server.py` converts any raised exception to `CallToolResult(isError=True, content=[TextContent(text=str(e))])`

### Established Patterns
- Lifespan yields a context dict with `{"service": service}` — tool handlers read from this. The error service slots into the same dict key
- Logging to stderr only (TOOL-04) — all `logging.getLogger()` output goes to stderr via `__main__.py` config
- Bridge factory pattern in `_factory.py` with lazy imports inside match cases

### Integration Points
- `app_lifespan` in `_server.py` (lines 32-80): Where the try/except wraps initialization
- `__main__.py` (lines 22-33): Pre-async validation to remove
- `OperatorService` class: Parent for `ErrorOperatorService`
- Tool handlers access service via `ctx.request_context.lifespan_context["service"]` — unchanged

</code_context>

<deferred>
## Deferred Ideas

None — discussion stayed within phase scope

</deferred>

---

*Phase: 09-error-serving-degraded-mode*
*Context gathered: 2026-03-06*
