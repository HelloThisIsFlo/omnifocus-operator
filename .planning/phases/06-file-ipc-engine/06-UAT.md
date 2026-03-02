---
status: complete
phase: 06-file-ipc-engine
source: 06-01-SUMMARY.md, 06-02-SUMMARY.md
started: 2026-03-02T16:00:00Z
updated: 2026-03-02T16:15:00Z
---

## Current Test

[testing complete]

## Tests

### 1. Test Suite Passes
expected: Run `uv run pytest` — all tests pass (137+), no failures, no errors.
result: pass

### 2. Package Exports
expected: Run `uv run python -c "from omnifocus_operator.bridge import RealBridge, sweep_orphaned_files; print('RealBridge:', RealBridge); print('sweep:', sweep_orphaned_files)"` — both names import successfully and print their representations.
result: pass

### 3. Factory Returns RealBridge
expected: Run `OMNIFOCUS_IPC_DIR=/tmp/of-test uv run python -c "from omnifocus_operator.bridge import create_bridge; b = create_bridge('real'); print(type(b).__name__)"` — prints "RealBridge".
result: pass

### 4. IPC Directory Auto-Creation
expected: Run `rm -rf /tmp/of-uat-dir && OMNIFOCUS_IPC_DIR=/tmp/of-uat-dir uv run python -c "from omnifocus_operator.bridge import create_bridge; create_bridge('real')" && ls -d /tmp/of-uat-dir` — the directory `/tmp/of-uat-dir` is created automatically by RealBridge init.
result: pass

### 5. Timeout Error Mentions OmniFocus
expected: Run `uv run python -c "from omnifocus_operator.bridge._errors import BridgeTimeoutError; e = BridgeTimeoutError('fetch', 5.0); print(str(e))"` — the error message includes "OmniFocus" (e.g., "OmniFocus did not respond within 5.0s").
result: pass

### 6. Orphan Sweep Runs at Server Startup
expected: Starting the MCP server with a real bridge should call sweep_orphaned_files() during lifespan startup, cleaning dead-PID IPC files before accepting requests.
result: issue
reported: "sweep_orphaned_files() exists and passes unit tests but is never called in app_lifespan in _server.py. Server starts without sweeping. Success criterion 6 says 'Server startup sweeps' but no wiring exists."
severity: major

## Summary

total: 6
passed: 5
issues: 1
pending: 0
skipped: 0

## Gaps

- truth: "Server startup sweeps orphaned request/response files from IPC directory"
  status: failed
  reason: "User reported: sweep_orphaned_files() exists and passes unit tests but is never called in app_lifespan in _server.py. Server starts without sweeping. Success criterion 6 says 'Server startup sweeps' but no wiring exists."
  severity: major
  test: 6
  root_cause: "app_lifespan() in src/omnifocus_operator/server/_server.py never calls sweep_orphaned_files(). The function is implemented and exported but not integrated into server startup."
  artifacts:
    - path: "src/omnifocus_operator/server/_server.py"
      issue: "app_lifespan missing sweep_orphaned_files() call"
    - path: "src/omnifocus_operator/bridge/_real.py"
      issue: "sweep_orphaned_files exists but is never invoked at startup"
  missing:
    - "Add sweep_orphaned_files(bridge.ipc_dir) call in app_lifespan before pre-warming cache"
  debug_session: ""
