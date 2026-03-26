---
status: complete
phase: 31-middleware-logging
source: [31-01-SUMMARY.md, 31-02-SUMMARY.md]
started: 2026-03-26T20:30:00Z
updated: 2026-03-26T20:37:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Cold Start Smoke Test
expected: Kill any running omnifocus-operator process. Start the server fresh. Server boots without errors, logging setup completes, and the server is ready to accept MCP calls.
result: pass

### 2. Middleware Pattern Review
expected: Open `src/omnifocus_operator/middleware.py`. ToolLoggingMiddleware is a clean, self-contained class inheriting from FastMCP Middleware. Logger is injected via constructor. Entry/exit/error logging is clear. No business logic leaks. The pattern reads as "this is how you add cross-cutting concerns."
result: pass

### 3. Server Cleanup Review
expected: Open `src/omnifocus_operator/server.py`. The old `log_tool_call()` function is gone. No manual logging boilerplate in tool handlers. Middleware is wired in `create_server()` cleanly. Response-shape debug logs remain in handlers (they log response content the middleware can't see).
result: pass

### 4. Logger Naming Convention
expected: Spot-check 3-4 modules (e.g. service.py, hybrid.py, bridge.py, factory.py). All use `logging.getLogger(__name__)` — no hardcoded string loggers. Pattern is consistent and idiomatic Python.
result: pass

### 5. Dual-Handler Logging Setup
expected: Open `src/omnifocus_operator/__main__.py`. `_configure_logging()` sets up two handlers on the root `omnifocus_operator` logger: StreamHandler(stderr) for Claude Desktop visibility + RotatingFileHandler(5MB, 3 backups) for persistent logs. Default level, formatter, and propagate settings are sensible. Old stderr hijacking comment and emoji banner are gone.
result: pass

### 6. Log Output Verification
expected: With the server running, make a tool call (e.g. `get_all`). Stderr shows entry/exit log lines from the middleware with timing. Log file is created at the expected path. Per-module logger names (e.g. `omnifocus_operator.server`, `omnifocus_operator.middleware`) appear in the output.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0
blocked: 0

## Gaps

[none yet]
