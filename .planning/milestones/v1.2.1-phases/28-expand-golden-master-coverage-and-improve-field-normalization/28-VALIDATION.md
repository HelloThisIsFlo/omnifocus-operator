---
phase: 28
slug: expand-golden-master-coverage-and-improve-field-normalization
status: complete
nyquist_compliant: true
wave_0_complete: true
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
| 28-01-01 | 01 | 1 | NORM-03 | integration | `uv run pytest tests/test_bridge_contract.py -x -v -k "inheritance"` | ✅ | ✅ green |
| 28-01-02 | 01 | 1 | NORM-01, NORM-02, NORM-04 | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ✅ green |
| 28-01-03 | 01 | 1 | GOLD-03 | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ✅ green |
| 28-02-01 | 02 | 1 | GOLD-01, GOLD-02 | syntax | `python -c "import ast; ast.parse(open('uat/capture_golden_master.py').read())"` | ✅ | ✅ green |
| 28-03-01 | 03 | 2 | GOLD-01, GOLD-02 | manual-only | Human runs `uv run python uat/capture_golden_master.py` | ✅ | ✅ green |
| 28-04-01 | 04 | 3 | GOLD-03, NORM-01..04 | integration | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The contract test file exists and was updated in-phase. No new test framework or config needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Capture script runs all 42 scenarios against live OmniFocus | GOLD-02 | SAFE-01/02: no automated test may touch the real Bridge | User runs `uv run python uat/capture_golden_master.py`, verifies all scenarios pass, commits fixtures |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-22

---

## Validation Audit 2026-03-22

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

### Evidence

- **42/42 contract tests pass** — `uv run pytest tests/test_bridge_contract.py -x -v` (0.26s)
- **690/690 full suite passes** — `uv run pytest` (14.17s, 98% coverage)
- **7/7 requirements COVERED** — all have automated verification via contract tests
- **42 fixture files** across 7 numbered subfolders (01-add through 07-inheritance)
- **Inheritance verified** — `_compute_effective_field`/`_compute_effective_flagged` called in add/edit/move paths
- **Presence-check verified** — lifecycle fixtures show `"<set>"` sentinel for completionDate/dropDate fields
- **repetitionRule verified** — exact match (null), removed from UNCOMPUTED
