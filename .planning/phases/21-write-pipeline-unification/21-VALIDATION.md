---
phase: 21
slug: write-pipeline-unification
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 21 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run python -m pytest -x -q --no-header` |
| **Full suite command** | `uv run python -m pytest -q --no-header` |
| **Estimated runtime** | ~13 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest -x -q --no-header`
- **After every plan wave:** Run `uv run python -m pytest -q --no-header`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 13 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 21-01-01 | 01 | 1 | PIPE-02 | unit | `uv run python -m pytest tests/test_service.py -k "TestAddTask" -x` | ✅ | ⬜ pending |
| 21-01-02 | 01 | 1 | PIPE-02 | unit | `uv run python -m pytest tests/test_service.py -k "TestEditTask" -x` | ✅ | ⬜ pending |
| 21-01-03 | 01 | 1 | PIPE-02 | unit | `uv run python -m pytest tests/test_hybrid_repository.py -k "excludes" -x` | ✅ | ⬜ pending |
| 21-02-01 | 02 | 1 | PIPE-01 | unit | `uv run python -m pytest tests/test_repository.py tests/test_hybrid_repository.py -k "add_task or edit_task" -x` | ✅ | ⬜ pending |
| 21-02-02 | 02 | 1 | PIPE-01 | unit | `uv run python -m pytest tests/test_repository.py -k "satisfies_protocol" -x` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. All 522+ tests exercise the write pipeline through service and repository layers. No new test files needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 13s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
