---
phase: 2
slug: data-models
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-01
---

# Phase 2 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ with pytest-asyncio (auto mode) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_models.py -x` |
| **Full suite command** | `uv run pytest --timeout=10` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_models.py -x`
- **After every plan wave:** Run `uv run pytest --timeout=10`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 3 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 02-01-01 | 01 | 1 | MODL-07 | unit | `uv run pytest tests/test_models.py::test_base_config_aliases -x` | ❌ W0 | ⬜ pending |
| 02-01-02 | 01 | 1 | MODL-01 | unit | `uv run pytest tests/test_models.py::test_task_from_bridge_json -x` | ❌ W0 | ⬜ pending |
| 02-01-03 | 01 | 1 | MODL-02 | unit | `uv run pytest tests/test_models.py::test_project_from_bridge_json -x` | ❌ W0 | ⬜ pending |
| 02-01-04 | 01 | 1 | MODL-03 | unit | `uv run pytest tests/test_models.py::test_tag_from_bridge_json -x` | ❌ W0 | ⬜ pending |
| 02-01-05 | 01 | 1 | MODL-04 | unit | `uv run pytest tests/test_models.py::test_folder_from_bridge_json -x` | ❌ W0 | ⬜ pending |
| 02-01-06 | 01 | 1 | MODL-05 | unit | `uv run pytest tests/test_models.py::test_perspective_from_bridge_json -x` | ❌ W0 | ⬜ pending |
| 02-01-07 | 01 | 1 | MODL-06 | unit | `uv run pytest tests/test_models.py::test_database_snapshot_round_trip -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_models.py` — stubs for MODL-01 through MODL-07
- [ ] `tests/conftest.py` — add fixture factories (`make_task_dict`, `make_project_dict`, etc.)
- [ ] `src/omnifocus_operator/models/` — entire models package (does not exist yet)

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 3s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
