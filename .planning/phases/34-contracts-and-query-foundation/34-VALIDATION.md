---
phase: 34
slug: contracts-and-query-foundation
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-29
validated: 2026-04-05
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
| T01-T03 | 01 | 1 | INFRA-04 | unit | `uv run pytest tests/test_list_contracts.py -x -q --no-cov` | Yes (29 tests) | ✅ green |
| T01-T03 | 02 | 2 | INFRA-01 | unit | `uv run pytest tests/test_query_builder.py -x -q --no-cov` | Yes (47 tests) | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_list_contracts.py` — query model validation, ListResult serialization, defaults, unknown field rejection (29 tests)
- [x] `tests/test_query_builder.py` — parameterized SQL generation, availability clauses, limit/offset, count-only (47 tests)

*Existing test infrastructure covers regression: `tests/test_contracts_type_aliases.py`, `tests/test_output_schema.py`*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s (0.25s actual)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ✅ validated 2026-04-05

## Validation Audit 2026-04-05

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

Full suite: 1528 passed (17.45s). Phase test subset: 121 passed (0.25s).
