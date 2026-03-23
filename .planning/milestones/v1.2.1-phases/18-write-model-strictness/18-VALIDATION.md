---
phase: 18
slug: write-model-strictness
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-16
validated: 2026-03-16
---

# Phase 18 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.3.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run python -m pytest tests/test_models.py tests/test_service.py -x -q --no-header --tb=short` |
| **Full suite command** | `uv run python -m pytest` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_models.py tests/test_service.py -x -q --no-header --tb=short`
- **After every plan wave:** Run `uv run python -m pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 18-01-01 | 01 | 1 | STRCT-01 | unit | `uv run python -m pytest tests/test_models.py -x -q -k "rejects_unknown_field"` | ✅ | ✅ green |
| 18-01-02 | 01 | 1 | STRCT-02 | unit | `uv run python -m pytest tests/test_models.py -x -q -k "accepts_unknown_field or read_model"` | ✅ | ✅ green |
| 18-01-03 | 01 | 1 | STRCT-03 | unit | `uv run python -m pytest tests/test_models.py -x -q -k "unset_defaults_with_forbid or set_values_with_forbid"` | ✅ | ✅ green |
| 18-01-04 | 01 | 1 | STRCT-01 | unit | `uv run python -m pytest tests/test_service.py -x -q -k "unknown_fields_rejected"` | ✅ | ✅ green |
| 18-01-05 | 01 | 1 | STRCT-01 | integration | `uv run python -m pytest tests/test_server.py -x -q -k "unknown_field_names_field"` | ✅ | ✅ green |
| 18-02-01 | 02 | 1 | STRCT-01 | unit | `uv run python -m pytest tests/test_warnings.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_models.py` — TestWriteModelStrictness: 11 tests for write model strictness (STRCT-01), read model permissiveness (STRCT-02), UNSET sentinel with forbid (STRCT-03)
- [x] `tests/test_service.py` — `test_unknown_fields_rejected` asserts ValidationError (STRCT-01)
- [x] `tests/test_server.py` — `test_add_tasks_unknown_field_names_field` + `test_edit_tasks_unknown_field_names_field` (STRCT-01)
- [x] `tests/test_warnings.py` — 4 integrity tests for warning consolidation

*All Wave 0 tests were created during execution via TDD.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-16

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests covering phase | 19 |
