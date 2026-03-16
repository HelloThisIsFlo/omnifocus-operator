---
phase: 18
slug: write-model-strictness
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-16
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
| 18-01-01 | 01 | 1 | STRCT-01 | unit | `uv run python -m pytest tests/test_models.py -x -q -k "extra_forbid or unknown_field"` | ❌ W0 | ⬜ pending |
| 18-01-02 | 01 | 1 | STRCT-02 | unit | `uv run python -m pytest tests/test_models.py -x -q -k "read_model_permissive"` | ❌ W0 | ⬜ pending |
| 18-01-03 | 01 | 1 | STRCT-03 | unit | `uv run python -m pytest tests/test_models.py -x -q -k "unset_with_forbid"` | ❌ W0 | ⬜ pending |
| 18-01-04 | 01 | 1 | STRCT-01 | unit | `uv run python -m pytest tests/test_service.py -x -q -k "unknown_field"` | ✅ (needs update) | ⬜ pending |
| 18-01-05 | 01 | 1 | STRCT-01 | unit | `uv run python -m pytest tests/test_service.py -x -q -k "error_handler"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_models.py` — new tests for write model strictness (STRCT-01), read model permissiveness (STRCT-02), UNSET sentinel with forbid (STRCT-03)
- [ ] `tests/test_service.py` — update `test_unknown_fields_ignored` to assert ValidationError (STRCT-01), new test for server error handler field names (STRCT-01)

*Existing infrastructure covers framework and fixtures — only new test cases needed.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
