---
phase: 3
slug: bridge-protocol-and-inmemorybridge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-01
---

# Phase 3 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.3+ |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_bridge.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_bridge.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 03-01-01 | 01 | 1 | BRDG-01 | unit | `uv run pytest tests/test_bridge.py::TestBridgeProtocol -x` | ❌ W0 | ⬜ pending |
| 03-01-02 | 01 | 1 | BRDG-01 | type-check | `uv run mypy src/omnifocus_operator/bridge/` | ❌ W0 | ⬜ pending |
| 03-01-03 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge -x` | ❌ W0 | ⬜ pending |
| 03-01-04 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge::test_call_tracking -x` | ❌ W0 | ⬜ pending |
| 03-01-05 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge::test_error_simulation -x` | ❌ W0 | ⬜ pending |
| 03-01-06 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestBridgeErrors -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_bridge.py` — stubs for BRDG-01, BRDG-02 (protocol, in-memory bridge, errors)
- [ ] No new conftest fixtures needed — InMemoryBridge IS the test fixture; existing `make_snapshot_dict()` in `tests/conftest.py` provides data

*Existing infrastructure covers framework and conftest needs.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
