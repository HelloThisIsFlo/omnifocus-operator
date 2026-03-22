---
phase: 27
slug: repository-contract-tests-for-behavioral-equivalence
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-21
validated: 2026-03-22
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x with pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_bridge_contract.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~14 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_bridge_contract.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 14 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 01-01 | 01 | 1 | INFRA-13, INFRA-14 | unit | `uv run pytest tests/test_stateful_bridge.py -x -v` | ✅ | ✅ green |
| 01-02 | 01 | 1 | INFRA-13, INFRA-14 | unit | `uv run python -c "from tests.golden_master import normalize_for_comparison"` | ✅ | ✅ green |
| 02-01 | 02 | 2 | INFRA-13 | manual (UAT) | `uv run python uat/capture_golden_master.py` | ✅ | ✅ green |
| 02-02 | 02 | 2 | INFRA-14 | unit | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ✅ green |
| 03-01 | 03 | 1 | INFRA-14 | unit | `uv run pytest tests/test_stateful_bridge.py tests/test_service.py -x` | ✅ | ✅ green |
| 03-02 | 03 | 1 | INFRA-14 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_move_to_project_ending -x` | ✅ | ✅ green |
| 04-01 | 04 | 2 | INFRA-13, INFRA-14 | unit | `uv run pytest tests/test_bridge_contract.py -x -v` | ✅ | ✅ green |
| 04-02 | 04 | 2 | INFRA-13, INFRA-14 | unit | `uv run pytest tests/test_bridge_contract.py -x -v -k "18 or 19 or 20"` | ✅ | ✅ green |
| 04-03 | 04 | 2 | INFRA-13 | manual (UAT) | `uv run python uat/capture_golden_master.py` (re-capture in raw format) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `uat/capture_golden_master.py` — interactive capture script (20 scenarios)
- [x] `tests/golden_master/snapshots/` — golden master fixture directory (20 scenarios + initial_state)
- [x] `tests/test_bridge_contract.py` — CI contract tests (20 parametrized scenarios)
- [x] `tests/golden_master/normalize.py` — VOLATILE/UNCOMPUTED field normalization

*Existing infrastructure covers test framework and configuration.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Golden master capture from RealBridge | INFRA-13 | Requires live OmniFocus database (SAFE-01) | Run `uv run python uat/capture_golden_master.py`, follow guided prompts, verify 20 scenario files written |
| Spot-check fixture privacy | INFRA-13 | Requires human inspection of JSON content | Open `tests/golden_master/snapshots/scenario_01_add_inbox_task.json`, verify all entity names start with `GM-` prefix |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 14s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-22

---

## Validation Audit 2026-03-22

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

### Coverage Summary

| Requirement | Tests | Status |
|-------------|-------|--------|
| INFRA-13 (Golden master captured from RealBridge) | 20 golden master snapshots in raw format, capture script UAT performed twice | COVERED |
| INFRA-14 (CI contract tests verify InMemoryBridge matches) | 20/20 `test_bridge_contract.py::test_scenario[*]` PASSED | COVERED |

### Test Suite Metrics

- **Total tests:** 668
- **Contract tests:** 20/20 passed
- **Bridge tests:** 44/44 passed
- **Full suite:** 668/668 passed
- **Coverage:** 98%
