---
phase: 16
slug: task-editing
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-08
---

# Phase 16 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio (Python), Vitest (JS bridge) |
| **Config file** | pyproject.toml (`asyncio_mode = "auto"`) |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ && npx vitest run` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 16-01-01 | 01 | 0 | EDIT-01 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_patch_name_only tests/test_service.py::TestEditTask::test_clear_due_date -x` | ✅ | ✅ green |
| 16-01-02 | 01 | 0 | EDIT-02 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_set_due_date tests/test_service.py::TestEditTask::test_set_estimated_minutes -x` | ✅ | ✅ green |
| 16-01-03 | 01 | 0 | EDIT-03 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_tag_replace -x` | ✅ | ✅ green |
| 16-01-04 | 01 | 0 | EDIT-04 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_tag_add -x` | ✅ | ✅ green |
| 16-01-05 | 01 | 0 | EDIT-05 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_tag_remove -x` | ✅ | ✅ green |
| 16-01-06 | 01 | 0 | EDIT-06 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_incompatible_tag_edit_modes_replace_with_add tests/test_service.py::TestEditTask::test_add_and_remove_tags_together -x` (tests renamed from `test_tag_mutual_exclusivity_*`) | ✅ | ✅ green |
| 16-01-07 | 01 | 0 | EDIT-07 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_move_to_project_ending tests/test_service.py::TestEditTask::test_move_to_task_beginning -x` | ✅ | ✅ green |
| 16-01-08 | 01 | 0 | EDIT-08 | unit | `uv run pytest tests/test_service.py::TestEditTask::test_move_to_inbox -x` | ✅ | ✅ green |
| 16-01-09 | 01 | 0 | EDIT-09 | integration | `uv run pytest tests/test_server.py::TestEditTasks -x` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OmniJS bridge actually modifies OmniFocus task | EDIT-01 | Requires live OmniFocus | UAT: edit task via MCP, verify in OmniFocus.app |
| moveTo actually moves task in OmniFocus | EDIT-07/08 | Requires live OmniFocus | UAT: move task via MCP, verify parent in OmniFocus.app |
| Inbox.beginning reference works | EDIT-08 | OmniJS runtime only | UAT: move task to inbox, verify it appears there |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 30s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-08

---

## Validation Audit 2026-03-08

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

### Test Summary
- **Service layer:** 20 tests in `tests/test_service.py::TestEditTask` (all green)
- **Integration:** 11 tests in `tests/test_server.py::TestEditTasks` (all green)
- **Bridge:** 32 tests in `bridge/tests/handleEditTask.test.js` (all green)
- **Total automated tests:** 63
