---
phase: 7
slug: simulatorbridge-and-mock-simulator
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_simulator_bridge.py -x` |
| **Full suite command** | `uv run pytest --tb=short -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_simulator_bridge.py -x`
- **After every plan wave:** Run `uv run pytest --tb=short -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestSimulatorBridgeUnit -x` | ❌ W0 | ⬜ pending |
| 07-01-02 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestFactory -x` | ❌ W0 | ⬜ pending |
| 07-01-03 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestTriggerNoOp -x` | ❌ W0 | ⬜ pending |
| 07-01-04 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestLifespan -x` | ❌ W0 | ⬜ pending |
| 07-01-05 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestIpcDirInheritance -x` | ❌ W0 | ⬜ pending |
| 07-02-01 | 02 | 1 | TEST-01 | integration | `uv run pytest tests/test_simulator_bridge.py::TestSimulatorProcess -x` | ❌ W0 | ⬜ pending |
| 07-02-02 | 02 | 1 | TEST-01 | integration | `uv run pytest tests/test_simulator_bridge.py::TestEndToEnd -x` | ❌ W0 | ⬜ pending |
| 07-02-03 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_bridge.py::TestErrorSimulation -x` | ❌ W0 | ⬜ pending |
| 07-02-04 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_bridge.py::TestFailAfter -x` | ❌ W0 | ⬜ pending |
| 07-02-05 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_bridge.py::TestDelay -x` | ❌ W0 | ⬜ pending |
| 07-02-06 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_bridge.py::TestMcpIntegration -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_simulator_bridge.py` — stubs for BRDG-03 and TEST-01 (unit + integration)
- [ ] `src/omnifocus_operator/bridge/_simulator.py` — SimulatorBridge class
- [ ] `src/omnifocus_operator/simulator/__init__.py` — simulator package marker
- [ ] `src/omnifocus_operator/simulator/__main__.py` — simulator entry point
- [ ] `src/omnifocus_operator/simulator/_data.py` — static snapshot data

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
