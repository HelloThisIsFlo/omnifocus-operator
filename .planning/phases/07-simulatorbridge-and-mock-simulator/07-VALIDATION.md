---
phase: 7
slug: simulatorbridge-and-mock-simulator
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-02
validated: 2026-03-07
---

# Phase 7 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_simulator_bridge.py tests/test_simulator_integration.py -x` |
| **Full suite command** | `uv run pytest --tb=short -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_simulator_bridge.py tests/test_simulator_integration.py -x`
- **After every plan wave:** Run `uv run pytest --tb=short -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 07-01-01 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestSimulatorBridge -x` | Yes | COVERED |
| 07-01-02 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestFactory -x` | Yes | COVERED |
| 07-01-03 | 01 | 1 | BRDG-03 | unit | `uv run pytest tests/test_simulator_bridge.py::TestPackageExport -x` | Yes | COVERED |
| 07-01-04 | 01 | 1 | BRDG-03 | integration | `uv run pytest tests/test_simulator_bridge.py::TestLifespan -x` | Yes | COVERED |
| 07-02-01 | 02 | 1 | TEST-01 | integration | `uv run pytest tests/test_simulator_integration.py::TestSimulatorProcess -x` | Yes | COVERED |
| 07-02-02 | 02 | 1 | TEST-01 | integration | `uv run pytest tests/test_simulator_integration.py::TestEndToEnd -x` | Yes | COVERED |
| 07-02-03 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_integration.py::TestErrorSimulation -x` | Yes | COVERED |
| 07-02-04 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_integration.py::TestFailAfter -x` | Yes | COVERED |
| 07-02-05 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_integration.py::TestDelay -x` | Yes | COVERED |
| 07-02-06 | 02 | 2 | TEST-01 | integration | `uv run pytest tests/test_simulator_integration.py::TestMcpIntegration -x` | Yes | COVERED |

*Status: COVERED · PARTIAL · MISSING*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have automated verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] All test files exist and tests pass (24/24 green)
- [x] No watch-mode flags
- [x] Feedback latency < 15s (actual: ~5s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests | 24 |
| Tests passing | 24 |
| Coverage | 95.34% |
