---
status: complete
phase: 09-error-serving-degraded-mode
source: [09-01-SUMMARY.md]
started: 2026-03-06T20:00:00Z
updated: 2026-03-06T20:05:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Normal Startup Still Works
expected: Start the MCP server normally. It boots without errors, connects successfully, and calling the `list_all` tool returns OmniFocus data as before. No regression from the degraded mode changes.
result: pass

### 2. Degraded Mode on Startup Failure
expected: When the OmniFocus bridge fails to initialize (e.g., simulate by temporarily setting an invalid bridge configuration or running on a machine without OmniFocus), the MCP server does NOT crash. Instead it stays running and enters degraded mode. You should see an ERROR-level log with the traceback of the startup failure.
result: pass

### 3. Error Tool Responses in Degraded Mode
expected: While the server is in degraded mode (from test 2), call any MCP tool (e.g., `list_all`). Instead of crashing or hanging, the tool returns an error response (isError: true) with an actionable message explaining the startup failure and what to fix.
result: pass

## Summary

total: 3
passed: 3
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
