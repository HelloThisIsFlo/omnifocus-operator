---
phase: 20
slug: model-taxonomy
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-18
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
| 20-01-01 | 01 | 1 | MODL-01 | smoke | `uv run python -c "from omnifocus_operator.contracts.use_cases.create_task import CreateTaskCommand, CreateTaskRepoPayload, CreateTaskResult"` | ❌ W0 | ⬜ pending |
| 20-01-02 | 01 | 1 | MODL-02 | regression | `uv run pytest tests/ -x -q --no-header --tb=short` | ✅ | ⬜ pending |
| 20-02-01 | 02 | 2 | MODL-03 | unit+regression | `uv run pytest tests/test_service.py tests/test_repository.py tests/test_hybrid_repository.py -x` | ✅ | ⬜ pending |
| 20-02-02 | 02 | 2 | MODL-04 | regression | `uv run pytest tests/test_models.py tests/test_service.py -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Import smoke test verifying `contracts/` package is importable with correct model names
- [ ] Verification that `models/write.py` is deleted and `from omnifocus_operator.models.write import ...` raises ImportError
- [ ] Verification that `bridge/protocol.py` and `repository/protocol.py` are deleted

*Existing infrastructure covers most phase requirements — Wave 0 adds only import/deletion verification.*

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
