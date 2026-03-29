---
phase: 34
slug: contracts-and-query-foundation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-29
---

# Phase 34 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_list_contracts.py tests/test_query_builder.py -x -q --no-cov` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_list_contracts.py tests/test_query_builder.py -x -q --no-cov`
- **After every plan wave:** Run `uv run pytest -x -q --no-cov`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | 01 | 1 | INFRA-01 | unit | `uv run pytest tests/test_query_builder.py -x -q --no-cov` | No -- Wave 0 | ⬜ pending |
| TBD | 01 | 1 | INFRA-04 | unit | `uv run pytest tests/test_list_contracts.py -x -q --no-cov` | No -- Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_list_contracts.py` — query model validation, ListResult serialization, defaults, unknown field rejection
- [ ] `tests/test_query_builder.py` — parameterized SQL generation, availability clauses, limit/offset, count-only

*Existing test infrastructure covers regression: `tests/test_contracts_type_aliases.py`, `tests/test_output_schema.py`*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
