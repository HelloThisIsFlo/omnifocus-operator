---
phase: 46
slug: pipeline-query-paths
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 46 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run pytest tests/ -x -q --no-header` |
| **Full suite command** | `uv run pytest tests/ -q --no-header` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --no-header`
- **After every plan wave:** Run `uv run pytest tests/ -q --no-header`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 46-01-01 | 01 | 1 | RESOLVE-11 | — | N/A | unit + integration | `uv run pytest tests/test_resolve_dates.py::TestOverdueShortcut -x` | Resolver: yes, Pipeline: ❌ W0 | ⬜ pending |
| 46-01-02 | 01 | 1 | RESOLVE-12 | — | N/A | unit + integration | `uv run pytest tests/test_resolve_dates.py::TestSoonShortcut -x` | Resolver: yes, Pipeline+Repo: ❌ W0 | ⬜ pending |
| 46-02-01 | 02 | 1 | EXEC-01 | — | N/A | unit | `uv run pytest tests/test_query_builder.py -x` | ❌ W0 | ⬜ pending |
| 46-02-02 | 02 | 1 | EXEC-07 | — | N/A | unit | `uv run pytest tests/test_query_builder.py -x` | ❌ W0 | ⬜ pending |
| 46-03-01 | 03 | 1 | EXEC-02 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py -x` | ❌ W0 | ⬜ pending |
| 46-03-02 | 03 | 1 | EXEC-03 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py -x` | ❌ W0 | ⬜ pending |
| 46-03-03 | 03 | 1 | EXEC-04 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py -x` | ❌ W0 | ⬜ pending |
| 46-03-04 | 03 | 1 | EXEC-05 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py -x` | ❌ W0 | ⬜ pending |
| 46-03-05 | 03 | 1 | EXEC-06 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py -x` | ❌ W0 | ⬜ pending |
| 46-03-06 | 03 | 1 | EXEC-09 | — | N/A | integration | `uv run pytest tests/test_list_pipelines.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_query_builder.py` — date predicate tests (EXEC-01, EXEC-07)
- [ ] `tests/test_list_pipelines.py` — pipeline date resolution tests (EXEC-02 through EXEC-06, EXEC-09)
- [ ] `tests/test_list_pipelines.py` — `get_due_soon_setting()` tests for HybridRepository (RESOLVE-12)
- [ ] `tests/test_list_pipelines.py` — `get_due_soon_setting()` tests for BridgeOnlyRepository env var path (RESOLVE-12)
- [ ] Test fixture updates: `make_task_dict()` may need `effectiveCompletionDate` and `effectiveDropDate` fields exercised

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| DueSoonSetting read from live OmniFocus Settings table | RESOLVE-12 | Requires real OmniFocus database | UAT: call `list_tasks(due="soon")` against live DB, verify results match OmniFocus UI |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
