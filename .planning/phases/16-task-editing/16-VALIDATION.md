---
phase: 16
slug: task-editing
status: draft
nyquist_compliant: false
wave_0_complete: false
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
| 16-01-01 | 01 | 0 | EDIT-01 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-02 | 01 | 0 | EDIT-02 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-03 | 01 | 0 | EDIT-03 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-04 | 01 | 0 | EDIT-04 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-05 | 01 | 0 | EDIT-05 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-06 | 01 | 0 | EDIT-06 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-07 | 01 | 0 | EDIT-07 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-08 | 01 | 0 | EDIT-08 | unit | `uv run pytest tests/test_service.py::TestEditTask -x` | ❌ W0 | ⬜ pending |
| 16-01-09 | 01 | 0 | EDIT-09 | integration | `uv run pytest tests/test_server.py::TestEditTasks -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_service.py::TestEditTask` — service-layer edit tests (EDIT-01 through EDIT-08)
- [ ] `tests/test_server.py::TestEditTasks` — MCP tool integration tests (EDIT-09)
- [ ] `bridge_tests/` — Vitest tests for handleEditTask
- [ ] TaskEditSpec, MoveToSpec, TaskEditResult models in `models/write.py`
- [ ] edit_task on Repository protocol + all 3 implementations

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OmniJS bridge actually modifies OmniFocus task | EDIT-01 | Requires live OmniFocus | UAT: edit task via MCP, verify in OmniFocus.app |
| moveTo actually moves task in OmniFocus | EDIT-07/08 | Requires live OmniFocus | UAT: move task via MCP, verify parent in OmniFocus.app |
| Inbox.beginning reference works | EDIT-08 | OmniJS runtime only | UAT: move task to inbox, verify it appears there |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
