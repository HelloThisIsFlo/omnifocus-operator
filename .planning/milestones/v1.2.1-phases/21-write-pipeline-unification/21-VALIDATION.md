---
phase: 21
slug: write-pipeline-unification
status: complete
nyquist_compliant: true
wave_0_complete: true
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
| 21-01-01 | 01 | 1 | PIPE-02 | unit | `uv run python -m pytest tests/test_service.py -k "TestAddTask" -x` | ✅ | ✅ green (19 passed) |
| 21-01-02 | 01 | 1 | PIPE-02 | unit | `uv run python -m pytest tests/test_service.py -k "TestEditTask" -x` | ✅ | ✅ green (71 passed) |
| 21-01-03 | 01 | 1 | PIPE-02 | unit | `uv run python -m pytest tests/test_hybrid_repository.py -k "only_sends_populated" -x` | ✅ | ✅ green (1 passed) |
| 21-02-01 | 02 | 1 | PIPE-01 | unit | `uv run python -m pytest tests/test_repository.py tests/test_hybrid_repository.py -k "add_task or edit_task" -x` | ✅ | ✅ green (14 passed) |
| 21-02-02 | 02 | 1 | PIPE-01 | unit | `uv run python -m pytest tests/test_repository.py -k "satisfies_protocol" -x` | ✅ | ✅ green (1 passed) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. All 522+ tests exercise the write pipeline through service and repository layers. No new test files needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 13s (12.77s full suite)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved (2026-03-19)

---

## Validation Audit 2026-03-19

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Notes:** All 5 task verifications pass green. One stale command filter corrected (21-01-03: `-k "excludes"` → `-k "only_sends_populated"` after test rename in plan 02). Full suite: 522 passed, 96.93% coverage, 12.77s.
