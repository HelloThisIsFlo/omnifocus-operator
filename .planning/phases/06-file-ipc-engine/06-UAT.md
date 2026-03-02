---
status: complete
phase: 06-file-ipc-engine
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md, 06-03-SUMMARY.md
started: 2026-03-02T18:00:00Z
updated: 2026-03-02T18:30:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite Passes
expected: Run `uv run pytest` — all tests pass (142+), no failures, no errors.
result: pass

### 2. Package Exports
expected: Run `uv run python -c "from omnifocus_operator.bridge import RealBridge, sweep_orphaned_files; print('RealBridge:', RealBridge); print('sweep:', sweep_orphaned_files)"` — both names import successfully and print their representations.
result: pass

### 3. Factory Returns RealBridge
expected: Run `OMNIFOCUS_IPC_DIR=/tmp/of-test uv run python -c "from omnifocus_operator.bridge import create_bridge; b = create_bridge('real'); print(type(b).__name__)"` — prints "RealBridge".
result: pass

### 4. IPC Directory Auto-Creation
expected: Run `rm -rf /tmp/of-uat-dir && OMNIFOCUS_IPC_DIR=/tmp/of-uat-dir uv run python -c "from omnifocus_operator.bridge import create_bridge; create_bridge('real')" && ls -d /tmp/of-uat-dir` — the directory `/tmp/of-uat-dir` is created automatically.
result: pass

### 5. Timeout Error Mentions OmniFocus
expected: Run `uv run python -c "from omnifocus_operator.bridge._errors import BridgeTimeoutError; e = BridgeTimeoutError('fetch', 5.0); print(str(e))"` — the error message includes "OmniFocus".
result: pass

### 6. Orphan Sweep Wired Into Server Startup
expected: Create orphaned IPC files in /tmp/of-sweep-test from dead PID 99999, start MCP server with OMNIFOCUS_BRIDGE=real and OMNIFOCUS_IPC_DIR=/tmp/of-sweep-test — orphaned .request.json and .response.json files are deleted, unrelated files preserved.
result: pass

## Summary

total: 6
passed: 6
issues: 0
pending: 0
skipped: 0

## Gaps

[none yet]
