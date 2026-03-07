---
phase: 3
slug: bridge-protocol-and-inmemorybridge
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-01
validated: 2026-03-07
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
| 03-01-01 | 01 | 1 | BRDG-01 | unit | `uv run pytest tests/test_bridge.py::TestBridgeProtocol -x` | YES | COVERED |
| 03-01-02 | 01 | 1 | BRDG-01 | type-check | `uv run mypy src/omnifocus_operator/bridge/` | YES | COVERED |
| 03-01-03 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge -x` | YES | COVERED |
| 03-01-04 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge::test_call_count -x` | YES | COVERED |
| 03-01-05 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestInMemoryBridge::test_error_simulation -x` | YES | COVERED |
| 03-01-06 | 01 | 1 | BRDG-02 | unit | `uv run pytest tests/test_bridge.py::TestBridgeErrors -x` | YES | COVERED |

*Status: COVERED | PARTIAL | MISSING*

---

## Wave 0 Requirements

- [x] `tests/test_bridge.py` — 22 tests for BRDG-01, BRDG-02 (protocol, in-memory bridge, errors)
- [x] No new conftest fixtures needed — InMemoryBridge IS the test fixture

*All Wave 0 infrastructure in place.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all references
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

All 22 tests pass. mypy strict clean. All 6 verification tasks COVERED.
