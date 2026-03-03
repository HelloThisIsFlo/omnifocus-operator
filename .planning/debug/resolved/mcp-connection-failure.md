---
status: resolved
trigger: "Claude Code fails to connect to the omnifocus-operator MCP server configured in `.mcp.json`. Error: Failed to reconnect to omnifocus-operator."
created: 2026-03-02T00:00:00Z
updated: 2026-03-02T00:00:00Z
---

## Current Focus

hypothesis: CONFIRMED -- sys.stdout = sys.stderr in __main__.py causes MCP SDK's stdio_server to write protocol messages to stderr instead of stdout, so Claude Code never receives them
test: Verified that sys.stdout.buffer points to stderr buffer after redirection
expecting: n/a -- root cause confirmed
next_action: Awaiting human verification that Claude Code can now connect to the MCP server

## Symptoms

expected: When Claude Code starts, it should launch the MCP server process and connect to it, making MCP tools available (e.g., `list_all`).
actual: Connection refused/timeout. Error message: "Failed to reconnect to omnifocus-operator."
errors: "Failed to reconnect to omnifocus-operator."
reproduction: Start Claude Code in the project directory. The `.mcp.json` file configures the server. Claude cannot connect.
started: First time trying to connect -- `.mcp.json` was just created as part of Phase 5 development.

## Eliminated

- hypothesis: Server process fails to start (import error, missing dep, crash)
  evidence: Manual run with exact .mcp.json command succeeds -- process starts, lifespan completes, logs show "Cache pre-warmed successfully"
  timestamp: 2026-03-02T00:01:00Z

## Evidence

- timestamp: 2026-03-02T00:01:00Z
  checked: Manual execution of server with `uv run --directory ... python -m omnifocus_operator`
  found: Server starts cleanly, lifespan runs, logs appear on stderr. Exit 143 (SIGTERM) when killed.
  implication: Process starts fine; issue is in stdio communication, not startup failure.

- timestamp: 2026-03-02T00:02:00Z
  checked: MCP SDK `stdio_server()` source code in `mcp.server.stdio`
  found: Uses `sys.stdout.buffer` to get the write stream for protocol messages
  implication: If sys.stdout is replaced, the buffer reference changes too

- timestamp: 2026-03-02T00:03:00Z
  checked: Effect of `sys.stdout = sys.stderr` on `sys.stdout.buffer`
  found: After redirect, `sys.stdout.buffer is sys.__stderr__.buffer` = True, `sys.stdout.buffer is sys.__stdout__.buffer` = False
  implication: MCP protocol output goes to stderr, Claude Code reads stdout and gets nothing -> connection failure

## Resolution

root_cause: `__main__.py` line 16 does `sys.stdout = sys.stderr` BEFORE `server.run(transport="stdio")`. The MCP SDK's `stdio_server()` reads `sys.stdout.buffer` to get the output stream. After the redirect, `sys.stdout.buffer` is stderr's buffer. All MCP protocol messages are written to stderr. Claude Code reads stdout and receives nothing, causing "Failed to reconnect."
fix: Save original stdout before redirecting, restore it before server.run() so the MCP SDK gets the real stdout for protocol messages.
verification: |
  1. Sent MCP initialize request to server process via stdin -- received valid JSON-RPC response on stdout (previously got nothing on stdout)
  2. stderr correctly receives log messages only (no protocol leakage)
  3. All 106 existing tests pass with no regressions
files_changed:
  - src/omnifocus_operator/__main__.py
