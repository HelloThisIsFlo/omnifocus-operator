---
status: complete
phase: 05-service-layer-and-mcp-server
source: 05-01-SUMMARY.md, 05-02-SUMMARY.md
started: 2026-03-02T14:00:00Z
updated: 2026-03-02T14:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Full test suite passes
expected: Running `uv run pytest` completes with all tests passing and no errors. Coverage should be ~95%+.
result: pass

### 2. Server starts with inmemory bridge
expected: Running `OMNIFOCUS_BRIDGE=inmemory uv run python -m omnifocus_operator` starts the MCP server without errors. It will block waiting for stdio input (Ctrl+C to exit). No crash, no traceback.
result: pass

### 3. MCP tool call works end-to-end
expected: With the server configured in Claude Code (via .mcp.json), calling the `list_all` tool returns a response containing all 5 entity collections: tasks, projects, tags, folders, perspectives. The server connects successfully (no "stuck connecting" issue).
result: pass

### 4. Output uses camelCase field names
expected: The response data from list_all uses camelCase field names (e.g., `dueDate`, `deferDate`, `parentId`) rather than snake_case.
result: issue
reported: "InMemory bridge returns empty collections so camelCase field names cannot be verified in actual response. Need seed data in inmemory bridge."
severity: major

### 5. Default bridge gives clear error
expected: Running `uv run python -m omnifocus_operator` (without OMNIFOCUS_BRIDGE set) defaults to "real" bridge and raises a NotImplementedError since it's not yet implemented — a clear error, not a silent failure.
result: pass

### 6. Bridge factory rejects unknown values
expected: Setting `OMNIFOCUS_BRIDGE=bogus uv run python -m omnifocus_operator` raises a ValueError with a message indicating the bridge type is unknown.
result: pass

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Output uses camelCase field names visible in list_all response"
  status: failed
  reason: "User reported: InMemory bridge returns empty collections so camelCase field names cannot be verified in actual response. Need seed data in inmemory bridge."
  severity: major
  test: 4
  artifacts: []
  missing: []
  debug_session: ""
