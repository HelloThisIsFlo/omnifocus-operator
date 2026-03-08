---
phase: 15
slug: write-pipeline-task-creation
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-08
validated: 2026-03-08
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
| **Bridge tests** | `npx vitest run bridge/tests/bridge.test.js` |
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
| 15-01-01 | 01 | 1 | CREA-01 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_create_minimal -x` | ✅ | ✅ green |
| 15-01-02 | 01 | 1 | CREA-02 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_create_with_parent_project -x` | ✅ | ✅ green |
| 15-01-03 | 01 | 1 | CREA-03 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_all_fields -x` | ✅ | ✅ green |
| 15-01-04 | 01 | 1 | CREA-04 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_no_parent_inbox -x` | ✅ | ✅ green |
| 15-01-05 | 01 | 1 | CREA-05 | unit | `uv run pytest tests/test_service.py::TestAddTask::test_empty_name -x` | ✅ | ✅ green |
| 15-02-01 | 02 | 1 | CREA-06 | integration | `uv run pytest tests/test_server.py::TestAddTasks -x` | ✅ | ✅ green |
| 15-02-02 | 02 | 1 | CREA-07 | unit | `uv run pytest tests/test_server.py::TestAddTasks::test_add_tasks_single_item_constraint -x` | ✅ | ✅ green |
| 15-02-03 | 02 | 1 | CREA-08 | unit | `uv run pytest tests/test_hybrid_repository.py::TestAddTask -x` | ✅ | ✅ green |
| 15-bridge | 01 | 1 | CREA-06 | unit | `npx vitest run bridge/tests/bridge.test.js` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_service.py::TestAddTask` — 13 service-level add_task tests (validation, parent/tag resolution)
- [x] `tests/test_server.py::TestAddTasks` — 12 MCP tool integration tests
- [x] `tests/test_hybrid_repository.py::TestAddTask` — 8 repository write + staleness tests
- [x] `bridge/tests/bridge.test.js::handleAddTask` — 9 vitest tests + 1 dispatch routing test
- [x] `tests/test_models.py::TestWriteModels` — 5 write model tests
- [x] `tests/test_repository.py::TestInMemoryAddTask` — 5 in-memory repository tests

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

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated

---

## Validation Audit 2026-03-08

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

**Details:**
- GAP: bridge.js `handleAddTask` had zero vitest tests
- FIX: Added 10 tests (9 unit + 1 dispatch) to `bridge/tests/bridge.test.js`
- All 391 Python tests + 36 vitest tests passing
