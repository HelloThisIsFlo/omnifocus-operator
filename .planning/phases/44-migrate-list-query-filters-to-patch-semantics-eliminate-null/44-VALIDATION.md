---
phase: 44
slug: migrate-list-query-filters-to-patch-semantics-eliminate-null
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-07
---

# Phase 44 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_list_contracts.py tests/test_list_pipelines.py -x -q` |
| **Full suite command** | `uv run pytest tests/ --ignore=tests/doubles -x -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_list_contracts.py tests/test_list_pipelines.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ --ignore=tests/doubles -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 44-01-01 | 01 | 1 | PATCH-01..03 | T-44-01 | reject_null_filters intercepts null before Pydantic (no _Unset leak) | unit | `uv run pytest tests/test_list_contracts.py::TestUnsetToNone tests/test_list_contracts.py::TestRejectNullFilters tests/test_list_contracts.py::TestValidateNonEmptyList -x -q` | ✅ | ✅ green |
| 44-01-02 | 01 | 1 | PATCH-04..09 | T-44-02 | Null on Patch fields raises educational error; UNSET defaults; empty tags rejected; offset=0 | unit | `uv run pytest tests/test_list_contracts.py::TestNullRejection tests/test_list_contracts.py::TestEmptyListRejection tests/test_list_contracts.py::TestQueryModelDefaults tests/test_list_contracts.py::TestOffsetRequiresLimit -x -q` | ✅ | ✅ green |
| 44-02-01 | 02 | 2 | PATCH-10..11 | — | AvailabilityFilter enums with ALL; empty availability rejected | unit | `uv run pytest tests/test_list_contracts.py::TestAvailabilityFilterEnums tests/test_list_contracts.py::TestAvailabilityFilterOnQueryModels tests/test_list_contracts.py::TestEmptyAvailabilityRejection -x -q` | ✅ | ✅ green |
| 44-02-02 | 02 | 2 | PATCH-12..13 | T-44-03, T-44-05 | UNSET→None at service/repo boundary; matches_inbox_name UNSET-safe; ALL expansion with mixed warning | integration | `uv run pytest tests/test_list_pipelines.py::TestMatchesInboxName tests/test_list_pipelines.py::TestAvailabilityExpansion tests/test_list_pipelines.py::TestListPassThroughs -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 8s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-07

---

## Validation Audit 2026-04-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
