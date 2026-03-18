---
phase: 20
slug: model-taxonomy
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-18
validated: 2026-03-18
---

# Phase 20 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ with pytest-asyncio 1.3.0+ |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/ -x -q --no-header --tb=short` |
| **Full suite command** | `uv run pytest tests/ --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --no-header --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=30` + `uv run mypy src/`
- **Before `/gsd:verify-work`:** Full suite must be green + mypy clean
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 20-01-01 | 01 | 1 | MODL-01 | smoke | `uv run pytest tests/test_contracts_smoke.py -x` | ✅ | ✅ green |
| 20-01-02 | 01 | 1 | MODL-02 | regression | `uv run pytest tests/ -x -q --no-header --tb=short` | ✅ | ✅ green |
| 20-02-01 | 02 | 2 | MODL-03 | unit+regression | `uv run pytest tests/test_service.py tests/test_repository.py tests/test_hybrid_repository.py -x` | ✅ | ✅ green |
| 20-02-02 | 02 | 2 | MODL-04 | regression | `uv run pytest tests/test_models.py tests/test_service.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] Import smoke test verifying `contracts/` package is importable with correct model names — `tests/test_contracts_smoke.py::TestContractsImportSmoke`
- [x] Verification that `models/write.py` is deleted and `from omnifocus_operator.models.write import ...` raises ImportError — `tests/test_contracts_smoke.py::TestOldFileDeletionGuards::test_models_write_deleted`
- [x] Verification that `bridge/protocol.py` and `repository/protocol.py` are deleted — `tests/test_contracts_smoke.py::TestOldFileDeletionGuards::test_bridge_protocol_deleted` + `test_repository_protocol_deleted`

*All Wave 0 gaps filled by `tests/test_contracts_smoke.py` (8 tests).*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-18

---

## Validation Audit 2026-03-18

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |

**Test file generated:** `tests/test_contracts_smoke.py` (8 tests)
- 4 import smoke tests (all exports + schema generation for 4 models)
- 3 deletion guard tests (models/write.py, bridge/protocol.py, repository/protocol.py)
- Full suite: 525 passed, 96% coverage
