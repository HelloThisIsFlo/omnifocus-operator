---
phase: 49
slug: implement-naive-local-datetime-contract-for-all-date-inputs
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
updated: 2026-04-11
---

# Phase 49 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q --timeout=30` |
| **Estimated runtime** | ~25 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q --timeout=30`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 49-01-01 | 01 | 1 | LOCAL-01 | unit | `uv run pytest tests/test_contracts_field_constraints.py::TestDateFieldStrType tests/test_output_schema.py::TestWriteSchemaNoDateTimeFormat -v --no-cov` | ✅ green |
| 49-01-02 | 01 | 1 | LOCAL-02 | unit | `uv run pytest tests/test_contracts_field_constraints.py::TestDateFieldStrType::test_add_naive_datetime_accepted tests/test_date_filter_contracts.py -k "naive" -v --no-cov` | ✅ green |
| 49-01-03 | 01 | 1 | LOCAL-07 | unit | `uv run pytest tests/test_descriptions.py -v --no-cov` | ✅ green |
| 49-02-01 | 02 | 2 | LOCAL-03 | unit | `uv run pytest tests/test_service_domain.py::TestNormalizeDateInput::test_aware_utc_string_converted_to_naive_local tests/test_service_domain.py::TestNormalizeDateInput::test_aware_offset_string_converted_to_naive_local -v --no-cov` | ✅ green |
| 49-02-02 | 02 | 2 | LOCAL-04 | unit | `uv run pytest tests/test_service_domain.py::TestNormalizeDateInput::test_date_only_gets_midnight_appended -v --no-cov` | ✅ green |
| 49-02-03 | 02 | 2 | LOCAL-05 | structural | Verified via source inspection: `local_now()` in `_ListTasksPipeline._resolve_date_filters` and `_ListProjectsPipeline._build_repo_query`. No `datetime.now(UTC)` in service.py. | ✅ green |
| 49-02-04 | 02 | 2 | LOCAL-06 | unit | `uv run pytest tests/test_service_domain.py::TestNormalizeDateInput::test_naive_datetime_passes_through_unchanged -v --no-cov` | ✅ green |
| 49-03-01 | 03 | 3 | LOCAL-08 | manual | `grep "Naive-Local DateTime Principle" docs/architecture.md` returns match | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Naive-local round-trip through OmniFocus bridge | LOCAL-02 | Requires live OmniFocus database | UAT: create task with naive datetime, read back, verify match |
| Architecture documentation completeness | LOCAL-08 | Documentation review | Verify section in docs/architecture.md covers rationale, evidence, contract table |

---

## Supplementary Tests

Tests beyond requirement coverage that strengthen the validation:

| Test Class | Covers | Command |
|------------|--------|---------|
| `TestToUtcTsNaiveString` | `_to_utc_ts` handles naive strings without assertion error (post-Phase-49 regression guard) | `uv run pytest tests/test_service_domain.py::TestToUtcTsNaiveString -v --no-cov` |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-04-11

| Metric | Count |
|--------|-------|
| Gaps found | 4 |
| Resolved | 4 |
| Escalated | 0 |

**Tests added:** 7 (4 in `TestNormalizeDateInput`, 3 in `TestToUtcTsNaiveString`)
**File:** `tests/test_service_domain.py`
**Commit:** `ca86a8b`
