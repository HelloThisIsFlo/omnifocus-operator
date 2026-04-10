---
phase: 48
slug: refactor-datefilter-into-discriminated-union-with-typed-date
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-10
audited: 2026-04-10
---

# Phase 48 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_date_filter_contracts.py tests/test_resolve_dates.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~16 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_date_filter_contracts.py tests/test_resolve_dates.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 16 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 48-01-01 | 01 | 1 | UNION-01 | T-48-01 | Discriminator routes non-dict to absolute_range safely | unit | `uv run pytest tests/test_date_filter_contracts.py::TestUnionDiscrimination tests/test_date_filter_contracts.py::TestDateFilterValidShorthand tests/test_date_filter_contracts.py::TestDateFilterTypedBounds -x -q` | ✅ | ✅ green |
| 48-01-02 | 01 | 1 | UNION-02 | T-48-02 | Naive datetimes rejected with educational error | unit | `uv run pytest tests/test_date_filter_contracts.py::TestDateFilterAbsolute::test_naive_datetime_rejected_before tests/test_date_filter_contracts.py::TestDateFilterAbsolute::test_naive_datetime_rejected_after -x -q` | ✅ | ✅ green |
| 48-01-03 | 01 | 1 | UNION-03 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py::TestDateFilterEmpty -x -q` | ✅ | ✅ green |
| 48-01-04 | 01 | 1 | UNION-04 | T-48-01 | Non-dict routed to Pydantic rejection, no ValueError bypass | unit | `uv run pytest tests/test_date_filter_contracts.py::TestDateFilterNonDictInput -x -q` | ✅ | ✅ green |
| 48-01-05 | 01 | 1 | UNION-05 | — | N/A | unit | `uv run pytest tests/test_date_filter_constants.py -x -q` | ✅ | ✅ green |
| 48-02-01 | 02 | 2 | UNION-06 | T-48-03 | isinstance dispatch more precise than attribute probing | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | ✅ | ✅ green |
| 48-02-02 | 02 | 2 | UNION-07 | T-48-04 | AbsoluteRangeFilter isinstance is O(1) | unit | `uv run pytest tests/test_service_domain.py -x -q` | ✅ | ✅ green |
| 48-02-03 | 02 | 2 | UNION-08 | — | N/A | integration | `uv run pytest -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

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
- [x] Feedback latency < 16s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-10

---

## Validation Audit 2026-04-10

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Suite status at audit time:** 1936 passed in 15.92s
