---
phase: 6
slug: file-ipc-engine
status: validated
nyquist_compliant: true
created: 2026-03-02
validated: 2026-03-07
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.3+ |
| **Config file** | `pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `uv run pytest tests/test_ipc_engine.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_ipc_engine.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | IPC-01 | unit | `uv run pytest tests/test_ipc_engine.py::TestAtomicWrite -x` | tests/test_ipc_engine.py | COVERED |
| 06-01-02 | 01 | 1 | IPC-02 | unit | `uv run pytest tests/test_ipc_engine.py::TestNonBlockingIO -x` | tests/test_ipc_engine.py | COVERED |
| 06-01-03 | 01 | 1 | IPC-03 | unit | `uv run pytest tests/test_ipc_engine.py::TestRequestEnvelope -x` | tests/test_ipc_engine.py | COVERED |
| 06-01-04 | 02 | 2 | IPC-04 | unit | `uv run pytest tests/test_ipc_engine.py::TestIPCDirectory -x` | tests/test_ipc_engine.py | COVERED |
| 06-01-05 | 01 | 1 | IPC-05 | unit | `uv run pytest tests/test_ipc_engine.py::TestTimeout -x` | tests/test_ipc_engine.py | COVERED |
| 06-01-06 | 02/03 | 2/1 | IPC-06 | unit+integration | `uv run pytest tests/test_ipc_engine.py::TestOrphanSweep tests/test_server.py::TestIPC06OrphanSweepWiring -x` | tests/test_ipc_engine.py, tests/test_server.py | COVERED |

*Status: COVERED · PARTIAL · MISSING*

---

## Additional Test Coverage

Tests beyond the minimum validation map:

| Test Class | File | What it covers |
|-----------|------|----------------|
| TestSuccessfulRoundTrip | test_ipc_engine.py | End-to-end IPC round-trip: response parsing, file cleanup, protocol errors |
| TestTriggerHook | test_ipc_engine.py | _trigger_omnifocus() no-op behavior and call ordering |
| TestSAFE01FactoryGuard | test_ipc_engine.py | SAFE-01: create_bridge("real") raises RuntimeError in pytest |
| TestExports | test_ipc_engine.py | Package exports: RealBridge, sweep_orphaned_files |
| TestIpcDirProperty | test_ipc_engine.py | RealBridge.ipc_dir read-only property |

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Default IPC path resolves correctly on macOS | IPC-04 | Requires OmniFocus 4 installed + Group Container present | Phase 8 UAT: verify `DEFAULT_IPC_DIR` exists on a macOS system with OmniFocus 4 |

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] All requirements covered by passing tests
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 6 IPC requirements (IPC-01 through IPC-06) have automated test coverage across 50 passing tests in `test_ipc_engine.py` (35 tests) and `test_server.py` (15 tests, including 3 sweep-wiring tests). Test suite runs in ~2.7s at 93.57% coverage.
