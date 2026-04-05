---
phase: 35
slug: sql-repository
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-30
validated: 2026-03-30
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_hybrid_repository.py -x -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 35-01-01 | 01 | 1 | TASK-01 | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k "list_tasks"` | ✅ | ✅ green |
| 35-01-02 | 01 | 1 | TASK-02..11 | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k "list_tasks and (flagged or inbox or project or tags or estimated or availability or search or pagination or combined or no_results or has_more)"` | ✅ | ✅ green |
| 35-01-03 | 01 | 1 | PROJ-01..07 | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k "list_projects"` | ✅ | ✅ green |
| 35-01-04 | 01 | 1 | INFRA-02 | perf | `uv run pytest tests/test_hybrid_repository.py -x -q -k "filtered_faster"` | ✅ | ✅ green |
| 35-02-01 | 02 | 1 | BROWSE-01 | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k "list_tags"` | ✅ | ✅ green |
| 35-02-02 | 02 | 1 | BROWSE-02 | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k "list_folders"` | ✅ | ✅ green |
| 35-02-03 | 02 | 1 | BROWSE-03 | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k "list_perspectives"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

All tests live in `tests/test_hybrid_repository.py` using the established `@pytest.mark.hybrid_db(...)` marker and `create_test_db` fixture pattern. No new test files or framework changes needed.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OmniFocus DB absolute timing | INFRA-02 | Requires live SQLite cache with production data volume | UAT: run list_tasks against real DB, verify sub-46ms response |

*Relative performance (filtered < full) is automated. Absolute timing against production data requires human.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-03-30

---

## Validation Audit 2026-03-30

| Metric | Count |
|--------|-------|
| Tasks audited | 7 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Notes:** VALIDATION.md was created pre-execution with predicted test paths (`tests/repository/sql/*.py`). Execution placed all tests in `tests/test_hybrid_repository.py` following the established project convention. All 39 phase-related tests pass. Updated file paths and statuses to reflect actual state.
