---
phase: 14
slug: model-refactor-lookups
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 14 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio |
| **Config file** | pyproject.toml `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x --no-cov -q` |
| **Full suite command** | `uv run pytest tests/` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --no-cov -q`
- **After every plan wave:** Run `uv run pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 14-01-01 | 01 | 1 | NAME-01 | integration | `uv run pytest tests/test_server.py -x -k "get_all"` | Needs update | pending |
| 14-01-02 | 01 | 1 | MODL-01 | unit | `uv run pytest tests/test_models.py -x -k "parent"` | Needs new | pending |
| 14-01-03 | 01 | 1 | MODL-02 | unit+integration | `uv run pytest tests/test_adapter.py tests/test_hybrid_repository.py -x` | Needs update | pending |
| 14-02-01 | 02 | 2 | LOOK-01 | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py -x -k "get_task"` | Needs new | pending |
| 14-02-02 | 02 | 2 | LOOK-02 | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py -x -k "get_project"` | Needs new | pending |
| 14-02-03 | 02 | 2 | LOOK-03 | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py -x -k "get_tag"` | Needs new | pending |
| 14-02-04 | 02 | 2 | LOOK-04 | unit+integration | `uv run pytest tests/test_server.py -x -k "not_found"` | Needs new | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] Update `conftest.py::make_task_dict` -- change `project`/`parent` string fields to `parent: ParentRef` shape
- [ ] Update all existing tests referencing `task.project` or `task.parent` as strings
- [ ] Update all existing tests referencing `list_all` tool name to `get_all`

*Wave 0 is embedded in Plan 01 tasks -- existing test fixtures must be updated before new code can pass.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RealBridge get-by-ID against live OmniFocus | LOOK-01/02/03 | SAFE-01: no automated tests touch RealBridge | UAT script in `uat/` -- run manually against live DB |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
