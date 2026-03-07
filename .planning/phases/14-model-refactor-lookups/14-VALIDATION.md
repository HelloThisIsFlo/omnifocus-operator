---
phase: 14
slug: model-refactor-lookups
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-07
validated: 2026-03-07
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
| **Actual runtime** | ~9 seconds |
| **Total tests** | 348 |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --no-cov -q`
- **After every plan wave:** Run `uv run pytest tests/`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Test Files | Status |
|---------|------|------|-------------|-----------|-------------------|------------|--------|
| 14-01-01 | 01 | 1 | NAME-01 | integration | `uv run pytest tests/test_server.py tests/test_service.py -x -k "get_all"` | test_server.py (5), test_service.py (3), test_simulator_bridge.py (1), test_simulator_integration.py (1) | green |
| 14-01-02 | 01 | 1 | MODL-01 | unit | `uv run pytest tests/test_models.py -x -k "parent"` | test_models.py: TestParentRef (3) + Task parent tests (3) | green |
| 14-01-03 | 01 | 1 | MODL-02 | unit+integration | `uv run pytest tests/test_adapter.py tests/test_hybrid_repository.py -x -k "parent"` | test_adapter.py: TestAdaptTaskParentRef (3), test_hybrid_repository.py: parent ref tests (6) | green |
| 14-02-01 | 02 | 2 | LOOK-01 | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py tests/test_service.py -x -k "get_task"` | test_hybrid_repository.py (4), test_server.py (3), test_service.py (2) | green |
| 14-02-02 | 02 | 2 | LOOK-02 | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py tests/test_service.py -x -k "get_project"` | test_hybrid_repository.py (2), test_server.py (3), test_service.py (2) | green |
| 14-02-03 | 02 | 2 | LOOK-03 | unit+integration | `uv run pytest tests/test_hybrid_repository.py tests/test_server.py tests/test_service.py -x -k "get_tag"` | test_hybrid_repository.py (2), test_server.py (3), test_service.py (2) | green |
| 14-02-04 | 02 | 2 | LOOK-04 | unit+integration | `uv run pytest tests/test_server.py tests/test_hybrid_repository.py tests/test_service.py -x -k "not_found"` | test_server.py (3), test_hybrid_repository.py (3), test_service.py (3) | green |

---

## Wave 0 Requirements

- [x] Update `conftest.py::make_task_dict` -- change `project`/`parent` string fields to `parent: ParentRef` shape
- [x] Update all existing tests referencing `task.project` or `task.parent` as strings
- [x] Update all existing tests referencing `list_all` tool name to `get_all`

*All Wave 0 items completed in Plan 01 execution.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RealBridge get-by-ID against live OmniFocus | LOOK-01/02/03 | SAFE-01: no automated tests touch RealBridge | UAT script in `uat/` -- run manually against live DB |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s (actual: ~9s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-03-07

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Requirements audited | 7 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests covering phase | 35+ |
| Full suite | 348 passing |
