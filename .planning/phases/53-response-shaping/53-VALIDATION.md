---
phase: 53
slug: response-shaping
status: verified
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-14
---

# Phase 53 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 53-01-01 | 01 | 1 | RENAME-01 | unit | `uv run python -c "from omnifocus_operator.models.common import ActionableEntity; print([f for f in ActionableEntity.model_fields if 'inherited' in f])"` | ✅ | ✅ green |
| 53-01-02 | 01 | 1 | RENAME-01 | integration | `uv run pytest tests/ -x -q` | ✅ | ✅ green |
| 53-02-01 | 02 | 2 | FSEL-13 | unit | `uv run python -c "from omnifocus_operator.server import create_server; print('OK')"` | ✅ | ✅ green |
| 53-02-02 | 02 | 2 | FSEL-13 | integration | `uv run pytest tests/test_descriptions.py tests/test_server.py -x -q` | ✅ | ✅ green |
| 53-03-01 | 03 | 3 | STRIP-01, STRIP-02, STRIP-03, FSEL-02, FSEL-10, FSEL-11, FSEL-12 | unit | `uv run pytest tests/test_projection.py -x -q` | ✅ | ✅ green |
| 53-03-02 | 03 | 3 | STRIP-01, STRIP-02, STRIP-03, FSEL-02, FSEL-10 | enforcement | `uv run pytest tests/test_projection.py::TestFieldGroupSync -x -q` | ✅ | ✅ green |
| 53-04-01 | 04 | 4 | FSEL-01, FSEL-03, FSEL-04, FSEL-05, FSEL-06, FSEL-07, FSEL-08, FSEL-09 | unit | `uv run python -c "from omnifocus_operator.contracts.use_cases.list.tasks import ListTasksQuery; q = ListTasksQuery(include=['notes']); print('include:', q.include)"` | ✅ | ✅ green |
| 53-04-02 | 04 | 4 | FSEL-01, FSEL-03, FSEL-04, FSEL-05, FSEL-06, FSEL-07, FSEL-08, FSEL-09 | integration | `uv run pytest tests/test_server.py::TestResponseShaping tests/test_projection.py -x -q` | ✅ | ✅ green |
| 53-05-01 | 05 | 5 | COUNT-01 | enforcement | `uv run pytest tests/test_descriptions.py -x -q` | ✅ | ✅ green |
| 53-05-02 | 05 | 5 | COUNT-01 | integration | `uv run pytest tests/test_server.py -x -q -k "limit_zero"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement-to-Test Coverage Map

| Requirement | Description | Test File(s) | Test Name(s) | Status |
|-------------|-------------|--------------|--------------|--------|
| RENAME-01 | effective→inherited field rename | test_server.py, test_hybrid_repository.py, test_models.py | camelCase output assertions, mapper assertions, model field checks | ✅ COVERED |
| FSEL-13 | server/ package structure | test_descriptions.py, test_server.py | AST scan of handlers.py, import chain tests | ✅ COVERED |
| STRIP-01 | Strip null/[]/""/ false/"none" | test_projection.py | TestStripping (5 value tests + multi-strip + strip_all) | ✅ COVERED |
| STRIP-02 | availability never stripped | test_projection.py | TestStripping::test_availability_never_stripped | ✅ COVERED |
| STRIP-03 | Envelope fields not stripped | test_projection.py | TestStripping::test_envelope_fields_not_in_entity_scope | ✅ COVERED |
| FSEL-02 | Default field sets defined | test_projection.py | TestFieldGroupSync (bidirectional model-group sync) | ✅ COVERED |
| FSEL-10 | Groups centralized in config | test_projection.py | TestFieldGroupSync (6 sync tests) | ✅ COVERED |
| FSEL-11 | Projection is post-filter | test_list_contracts.py | include/only absent from RepoQuery parity test | ✅ COVERED |
| FSEL-12 | Projection is server-layer | test_server.py, test_projection.py | Handlers call projection; service returns full models | ✅ COVERED |
| FSEL-01 | include param on list tools | test_server.py | TestResponseShaping::test_list_tasks_with_include_notes | ✅ COVERED |
| FSEL-03 | Available include groups | test_projection.py | TestFieldSelection (groups + review group tests) | ✅ COVERED |
| FSEL-04 | Invalid include → error | test_server.py | TestResponseShaping::test_list_tasks_invalid_include_returns_error | ✅ COVERED |
| FSEL-05 | only for field selection | test_projection.py, test_server.py | TestFieldSelection::test_only_*, TestResponseShaping::test_list_tasks_with_only_returns_selected_fields | ✅ COVERED |
| FSEL-06 | include+only conflict → warning | test_projection.py | TestFieldSelection::test_include_only_conflict | ✅ COVERED |
| FSEL-07 | Invalid only → warning | test_projection.py | TestFieldSelection::test_invalid_only_warning, test_only_with_multiple_invalid_produces_multiple_warnings | ✅ COVERED |
| FSEL-08 | include: ["*"] → all fields | test_projection.py, test_server.py | TestFieldSelection::test_include_star, TestResponseShaping::test_list_tasks_with_include_star_returns_all_fields | ✅ COVERED |
| FSEL-09 | get_*/get_all strip only | test_server.py | TestResponseShaping::test_get_task_strips_null_fields, test_get_all_strips_entities, test_add_tasks_returns_unmodified | ✅ COVERED |
| COUNT-01 | limit: 0 count-only | test_server.py | TestResponseShaping::test_list_tasks_limit_zero_returns_count_only, test_list_projects_limit_zero_returns_count_only | ✅ COVERED |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** verified 2026-04-14

---

## Validation Audit 2026-04-14

| Metric | Count |
|--------|-------|
| Requirements audited | 18 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Test files covering phase | 5 (test_projection.py, test_server.py, test_descriptions.py, test_list_contracts.py, test_models.py) |
| Total tests in phase scope | 56 (34 projection + 13 response shaping + 9 descriptions) |
| Full suite | 2086 passed |
