# Feature Landscape: FastMCP v3 Migration

**Domain:** MCP server infrastructure migration (mcp SDK -> fastmcp>=3 standalone)
**Researched:** 2026-03-25
**Overall confidence:** HIGH -- spike experiments (8 of 8) validated all claims against real clients

## In Scope (This Milestone)

Features to implement, ordered by migration dependency chain.

| Feature | What Changes | Complexity | Spike Reference |
|---------|-------------|------------|-----------------|
| Dependency swap | pyproject.toml + all imports | Low | Exp 01 |
| Lifespan shortcut | `ctx.request_context.lifespan_context` -> `ctx.lifespan_context` (6 sites) | Low | Exp 01 |
| Test client | Delete _ClientSessionProxy + run_with_client, replace with Client(server) | Med-High (wide diff, ~1164 lines in test_server.py) | Exp 04 |
| Middleware | New ToolLoggingMiddleware, delete log_tool_call() + 6 call sites | Med | Exp 05 |
| Dual logging | stderr + file handlers in __main__.py | Low | Exp 02/03 |
| Progress reporting | ctx.report_progress() in add_tasks/edit_tasks | Low | Exp 06 |
| Documentation | README + landing page dependency references | Low | -- |

## Explicitly NOT Building (Deferred)

| Feature | Why Defer | When to Revisit |
|---------|-----------|-----------------|
| Elicitation (`ctx.elicit()`) | Claude Desktop doesn't support it. Primary target client. | When Claude Desktop adds elicitation support |
| `Depends()` DI | Current lifespan pattern works. Depends() is per-request, our service is singleton. | Never, unless architecture changes to per-request services |
| Background tasks (`@mcp.tool(task=True)`) | No use case. Our tools are fast (<50ms reads, <2s writes). | If we add long-running tools (bulk imports?) |
| Tool versioning | No breaking changes planned. | If we need to ship breaking tool API changes |
| `ctx.info()` / `ctx.warning()` | Dead end. No major client renders protocol log messages. | Never. Use response-payload warnings instead. |

## Feature Dependencies

```
Dependency swap ──┬──> Test client migration ──> Middleware ──> Logging rework
                  │
                  └──> Progress reporting (independent)
                                                              Documentation (last)
```

## Anti-Features

| Anti-Feature | Why Avoid | What to Do Instead |
|--------------|-----------|-------------------|
| `ctx.info()` for agent messages | No client renders them | Response-payload warnings (existing pattern) |
| `Client.call_tool()` in tests | Raises ToolError, breaks existing assertions | Use `call_tool_mcp()` -- same return type as current ClientSession |
| Rich logging via `get_logger()` | No logger name in output, hardcoded INFO level | Plain Python `logging.getLogger()` with custom handlers |
| `propagate = False` on root logger | Breaks dual-handler setup | Let propagation work, add handlers to root logger |

## Sources

- Spike findings: `.research/deep-dives/fastmcp-spike/FINDINGS.md`
- Spike experiments: `.research/deep-dives/fastmcp-spike/experiments/`
