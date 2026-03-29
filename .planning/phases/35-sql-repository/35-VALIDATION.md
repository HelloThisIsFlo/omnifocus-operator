---
phase: 35
slug: sql-repository
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-30
---

# Phase 35 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --tb=short` |
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
| 35-01-01 | 01 | 1 | TASK-01 | unit | `uv run pytest tests/repository/sql/ -x -q -k "list_tasks"` | ❌ W0 | ⬜ pending |
| 35-01-02 | 01 | 1 | TASK-02..11 | unit | `uv run pytest tests/repository/sql/ -x -q -k "list_tasks and filter"` | ❌ W0 | ⬜ pending |
| 35-01-03 | 01 | 1 | PROJ-01..07 | unit | `uv run pytest tests/repository/sql/ -x -q -k "list_projects"` | ❌ W0 | ⬜ pending |
| 35-01-04 | 01 | 1 | INFRA-02 | perf | `uv run pytest tests/repository/sql/ -x -q -k "performance"` | ❌ W0 | ⬜ pending |
| 35-02-01 | 02 | 1 | BROWSE-01 | unit | `uv run pytest tests/repository/sql/ -x -q -k "list_tags"` | ❌ W0 | ⬜ pending |
| 35-02-02 | 02 | 1 | BROWSE-02 | unit | `uv run pytest tests/repository/sql/ -x -q -k "list_folders"` | ❌ W0 | ⬜ pending |
| 35-02-03 | 02 | 1 | BROWSE-03 | unit | `uv run pytest tests/repository/sql/ -x -q -k "list_perspectives"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/repository/sql/test_list_tasks.py` — stubs for TASK-01..11
- [ ] `tests/repository/sql/test_list_projects.py` — stubs for PROJ-01..07
- [ ] `tests/repository/sql/test_list_tags.py` — stubs for BROWSE-01
- [ ] `tests/repository/sql/test_list_folders.py` — stubs for BROWSE-02
- [ ] `tests/repository/sql/test_list_perspectives.py` — stubs for BROWSE-03
- [ ] `tests/repository/sql/test_sql_performance.py` — stubs for INFRA-02

*Existing infrastructure (conftest, fixtures, InMemoryBridge) covers shared needs.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OmniFocus DB query | INFRA-02 | Requires live SQLite cache | UAT: run list_tasks against real DB, verify < 46ms |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
