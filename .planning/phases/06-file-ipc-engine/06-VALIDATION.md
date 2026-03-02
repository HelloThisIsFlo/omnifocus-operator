---
phase: 6
slug: file-ipc-engine
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 6 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.3+ |
| **Config file** | `pyproject.toml` ([tool.pytest.ini_options]) |
| **Quick run command** | `uv run pytest tests/test_real_bridge.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~3 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_real_bridge.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 06-01-01 | 01 | 1 | IPC-01 | unit | `uv run pytest tests/test_real_bridge.py::TestAtomicWrite -x` | ❌ W0 | ⬜ pending |
| 06-01-02 | 01 | 1 | IPC-02 | unit | `uv run pytest tests/test_real_bridge.py::TestNonBlockingIO -x` | ❌ W0 | ⬜ pending |
| 06-01-03 | 01 | 1 | IPC-03 | unit | `uv run pytest tests/test_real_bridge.py::TestDispatchProtocol -x` | ❌ W0 | ⬜ pending |
| 06-01-04 | 01 | 1 | IPC-04 | unit | `uv run pytest tests/test_real_bridge.py::TestIPCDirectory -x` | ❌ W0 | ⬜ pending |
| 06-01-05 | 01 | 1 | IPC-05 | unit | `uv run pytest tests/test_real_bridge.py::TestTimeout -x` | ❌ W0 | ⬜ pending |
| 06-01-06 | 01 | 1 | IPC-06 | unit | `uv run pytest tests/test_real_bridge.py::TestOrphanSweep -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_real_bridge.py` — test stubs for IPC-01 through IPC-06
- [ ] Test fixtures for tmp IPC directory (`tmp_path` from pytest)
- [ ] Test helper for creating fake IPC files with specific PID prefixes (for sweep tests)

*Testing strategy notes:*
- All tests use `tmp_path` (pytest fixture) as IPC directory — never real OmniFocus sandbox path
- Timeout tests use short timeout (0.2s) and no response file to avoid 10s waits
- PID liveness tests use `os.getpid()` (alive) and known-dead PID from exited subprocess
- SAFE-01/SAFE-02: No test touches RealBridge with actual OmniFocus trigger. Phase 6's `_trigger_omnifocus()` is a no-op.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Default IPC path resolves correctly on macOS | IPC-04 | Requires OmniFocus 4 installed + Group Container present | Phase 8 UAT: verify `DEFAULT_IPC_DIR` exists on a macOS system with OmniFocus 4 |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
