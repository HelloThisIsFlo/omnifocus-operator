---
status: complete
phase: 05-service-layer-and-mcp-server
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md
started: 2026-03-02T13:00:00Z
updated: 2026-03-02T13:10:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Full test suite passes
expected: Running `uv run pytest` completes with all 106 tests passing and no errors. Coverage should be ~95%+.
result: pass

### 2. Server starts with inmemory bridge
expected: Running `OMNIFOCUS_BRIDGE=inmemory uv run python -m omnifocus_operator` starts the MCP server without errors. It will block waiting for stdio input (Ctrl+C to exit). No crash, no traceback.
result: pass

### 3. list_all tool returns structured data
expected: When connected to the server (OMNIFOCUS_BRIDGE=inmemory), calling the `list_all` tool returns a response containing all 5 entity collections: tasks, projects, tags, folders, perspectives. The response uses structuredContent format.
result: issue
reported: "Server stuck on connecting when used as MCP server in Claude Code. Cannot test tool calls."
severity: blocker

### 4. Output uses camelCase field names
expected: The outputSchema and response data from list_all uses camelCase field names (e.g., `dueDate`, `deferDate`, `parentId`) rather than snake_case.
result: issue
reported: "Cannot test — blocked by server connection issue (test 3)"
severity: blocker

### 5. Default bridge gives clear error
expected: Running `uv run python -m omnifocus_operator` (without OMNIFOCUS_BRIDGE set) defaults to "real" bridge and raises a NotImplementedError since it's not yet implemented — a clear error, not a silent failure.
result: issue
reported: "Cannot test — blocked by server connection issue (test 3)"
severity: blocker

### 6. Bridge factory rejects unknown values
expected: Setting OMNIFOCUS_BRIDGE to an invalid value (e.g., "bogus") raises a ValueError with a message indicating the bridge type is unknown.
result: issue
reported: "Cannot test — blocked by server connection issue (test 3)"
severity: blocker

## Summary

total: 6
passed: 2
issues: 4
pending: 0
skipped: 0

## Gaps

- truth: "list_all tool returns structured data when connected as MCP client"
  status: failed
  reason: "User reported: Server stuck on connecting when used as MCP server in Claude Code. Cannot test tool calls."
  severity: blocker
  test: 3
  root_cause: "__main__.py does sys.stdout = sys.stderr before server.run(transport='stdio'). MCP SDK's stdio_server() reads sys.stdout.buffer to write protocol responses — after redirect, all responses go to stderr and the client never receives them."
  artifacts:
    - path: "src/omnifocus_operator/__main__.py"
      issue: "sys.stdout = sys.stderr redirects MCP protocol output to stderr"
  missing:
    - "Preserve original stdout for MCP protocol, only redirect for print protection"
  debug_session: ""

- truth: "Output uses camelCase field names"
  status: failed
  reason: "User reported: Cannot test — blocked by server connection issue (test 3)"
  severity: blocker
  test: 4
  root_cause: "Blocked by test 3 — same stdout redirect issue"
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Default bridge gives clear error"
  status: failed
  reason: "User reported: Cannot test — blocked by server connection issue (test 3)"
  severity: blocker
  test: 5
  root_cause: "Blocked by test 3 — same stdout redirect issue"
  artifacts: []
  missing: []
  debug_session: ""

- truth: "Bridge factory rejects unknown values"
  status: failed
  reason: "User reported: Cannot test — blocked by server connection issue (test 3)"
  severity: blocker
  test: 6
  root_cause: "Blocked by test 3 — same stdout redirect issue"
  artifacts: []
  missing: []
  debug_session: ""
