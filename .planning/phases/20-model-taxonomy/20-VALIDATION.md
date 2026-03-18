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
| 20-01-01 | 01 | 1 | MODL-01 | regression | `uv run pytest tests/ -x -q --no-header --tb=short` | ✅ | ✅ green |
| 20-01-02 | 01 | 1 | MODL-02 | regression | `uv run pytest tests/ -x -q --no-header --tb=short` | ✅ | ✅ green |
| 20-02-01 | 02 | 2 | MODL-03 | unit+regression | `uv run pytest tests/test_service.py tests/test_repository.py tests/test_hybrid_repository.py -x` | ✅ | ✅ green |
| 20-02-02 | 02 | 2 | MODL-04 | regression | `uv run pytest tests/test_models.py tests/test_service.py -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing test infrastructure covers all phase requirements. The 517 existing tests import and exercise every contracts/ model — no additional smoke tests needed.*

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
| Resolved | 0 |
| Skipped | 3 |

**Skipped gaps (redundant):**
- Import smoke test — already covered by 517 existing tests that import and use contracts/ models
- Deletion guards for old files — hardcodes historical decisions; no value as regression tests
- Full suite: 517 passed, 96% coverage
