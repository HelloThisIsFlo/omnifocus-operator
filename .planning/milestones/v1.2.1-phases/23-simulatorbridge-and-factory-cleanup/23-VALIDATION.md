---
phase: 23
slug: simulatorbridge-and-factory-cleanup
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
---

# Phase 23 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x --timeout=30 -q` |
| **Full suite command** | `uv run pytest tests/ --timeout=30 -q` |
| **Estimated runtime** | ~13 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=30 -q`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=30 -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 13 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 23-01-01 | 01 | 1 | INFRA-07 | unit | `uv run pytest tests/test_ipc_engine.py::TestRealBridgeSafety -v` | ✅ | ✅ green |
| 23-01-01 | 01 | 1 | INFRA-07 | unit | `uv run pytest tests/test_simulator_bridge.py::TestPackageExport::test_create_bridge_not_importable_from_package -v` | ✅ | ✅ green |
| 23-01-01 | 01 | 1 | INFRA-06 | grep | `grep -r 'OMNIFOCUS_BRIDGE[^_]' src/ --include='*.py' \| grep -v docstring` | ✅ | ✅ green |
| 23-01-02 | 01 | 1 | INFRA-04 | unit | `uv run pytest tests/test_simulator_bridge.py::TestPackageExport::test_simulator_bridge_not_importable_from_package -v` | ✅ | ✅ green |
| 23-01-02 | 01 | 1 | INFRA-04 | unit | `uv run pytest tests/test_simulator_bridge.py::TestPackageExport::test_simulator_bridge_not_in_all -v` | ✅ | ✅ green |
| 23-01-02 | 01 | 1 | INFRA-05 | grep | `grep -r 'from omnifocus_operator\.bridge import.*SimulatorBridge' tests/` (expect 0 matches) | ✅ | ✅ green |
| 23-01-02 | 01 | 1 | INFRA-07 | filesystem | `test ! -f src/omnifocus_operator/bridge/factory.py` | ✅ | ✅ green |
| 23-01-02 | 01 | 1 | ALL | integration | `uv run pytest tests/ -x --timeout=30 -q` (592 pass) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-20
