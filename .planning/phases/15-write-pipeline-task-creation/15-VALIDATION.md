---
phase: 15
slug: write-pipeline-task-creation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-08
---

# Phase 15 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + anyio (Python), vitest (JS bridge) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options], `vitest.config.js` |
| **Quick run command** | `uv run pytest tests/ -x --no-cov -q` |
| **Full suite command** | `uv run pytest tests/ --cov` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --no-cov -q`
- **After every plan wave:** Run `uv run pytest tests/ --cov`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 15-01-01 | 01 | 1 | CREA-01 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_create_minimal -x` | ❌ W0 | ⬜ pending |
| 15-01-02 | 01 | 1 | CREA-02 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_parent_resolution -x` | ❌ W0 | ⬜ pending |
| 15-01-03 | 01 | 1 | CREA-03 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_all_fields -x` | ❌ W0 | ⬜ pending |
| 15-01-04 | 01 | 1 | CREA-04 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_no_parent_inbox -x` | ❌ W0 | ⬜ pending |
| 15-01-05 | 01 | 1 | CREA-05 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_validation -x` | ❌ W0 | ⬜ pending |
| 15-02-01 | 02 | 1 | CREA-06 | integration | `uv run pytest tests/test_server.py::TestAddTasks -x` | ❌ W0 | ⬜ pending |
| 15-02-02 | 02 | 1 | CREA-07 | unit | `uv run pytest tests/test_server.py::TestAddTasks::test_single_item_constraint -x` | ❌ W0 | ⬜ pending |
| 15-02-03 | 02 | 1 | CREA-08 | unit | `uv run pytest tests/test_hybrid_repository.py::TestAddTask -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_service.py::TestAddTask` — service-level add_task tests (validation, parent/tag resolution)
- [ ] `tests/test_server.py::TestAddTasks` — MCP tool integration tests
- [ ] `tests/test_hybrid_repository.py::TestAddTask` — repository write + staleness tests
- [ ] `tests/test_bridge.py` — bridge.js `handleAddTask` vitest tests
- [ ] Write model classes (TaskCreateSpec, TaskCreateResult) — needed before tests

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Task appears in OmniFocus inbox | CREA-01 | Requires live OmniFocus | UAT: call add_tasks via MCP, verify in OmniFocus UI |
| Task appears under correct parent | CREA-02 | Requires live OmniFocus | UAT: create task with parent ID, verify placement |
| All fields persist correctly | CREA-03 | Requires live OmniFocus | UAT: create task with all fields, verify each in UI |
| Next read returns fresh data | CREA-08 | Requires live OmniFocus + WAL | UAT: create task, immediately call get_all, verify new task present |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
