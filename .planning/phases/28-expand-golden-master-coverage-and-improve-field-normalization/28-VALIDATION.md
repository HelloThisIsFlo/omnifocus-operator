---
phase: 28
slug: expand-golden-master-coverage-and-improve-field-normalization
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-22
---

# Phase 28 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_bridge_contract.py -x -v` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_bridge_contract.py -x -v`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | GOLD-01 | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ⬜ pending |
| TBD | 01 | 1 | GOLD-03 | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ⬜ pending |
| TBD | 01 | 1 | NORM-01 | integration | `uv run pytest tests/test_bridge_contract.py -x -v -k "lifecycle"` | ✅ | ⬜ pending |
| TBD | 01 | 1 | NORM-02 | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ⬜ pending |
| TBD | 01 | 1 | NORM-03 | integration | `uv run pytest tests/test_bridge_contract.py -x -v -k "inheritance"` | ✅ | ⬜ pending |
| TBD | 01 | 1 | NORM-04 | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ⬜ pending |
| TBD | - | - | GOLD-02 | manual-only | Human runs `uv run python uat/capture_golden_master.py` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The contract test file exists and will be updated in-phase. No new test framework or config needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Capture script runs all ~42 scenarios against live OmniFocus | GOLD-02 | SAFE-01/02: no automated test may touch RealBridge | User runs `uv run python uat/capture_golden_master.py`, verifies all scenarios pass, commits fixtures |
| InMemoryBridge fix triage (Plan 2) | NORM-01..04 | Interactive decisions on fix vs. known-divergence | User runs contract tests, triages failures with Claude |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
