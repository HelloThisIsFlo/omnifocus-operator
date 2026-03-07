---
phase: 10
slug: model-overhaul
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-07
validated: 2026-03-07
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + vitest |
| **Config file** | `pyproject.toml` (pytest section) + `vitest.config.js` |
| **Quick run command** | `uv run pytest tests/test_adapter.py tests/test_models.py -x` |
| **Full suite command** | `uv run pytest && cd bridge && npx vitest run` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest && cd bridge && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | MODEL-01, MODEL-02 | unit | `uv run pytest tests/test_models.py -x` | Yes | green |
| 10-01-02 | 01 | 1 | MODEL-03 | unit | `uv run pytest tests/test_adapter.py -x` | Yes | green |
| 10-02-01 | 02 | 2 | MODEL-04, MODEL-05 | unit | `uv run pytest tests/test_models.py -x` | Yes | green |
| 10-02-02 | 02 | 2 | MODEL-06 | integration | `uv run pytest && cd bridge && npx vitest run` | Yes | green |
| 10-03-01 | 03 | 3 | Adapter idempotency | unit | `uv run pytest tests/test_adapter.py::TestAdapterIdempotency -v` | Yes | green |
| 10-03-02 | 03 | 3 | Error paths (scheduleType, anchorDateKey) | unit | `uv run pytest tests/test_adapter.py::TestAdaptRepetitionRule -v` | Yes | green |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [x] `bridge/adapter.py` — new module for bridge-to-model mapping
- [x] `uat/test_model_overhaul.py` — new UAT script

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RealBridge live data roundtrip | MODEL-06 | Requires live OmniFocus database | Run `uat/test_model_overhaul.py` against local OmniFocus |

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

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 3 |
| Resolved | 3 |
| Escalated | 0 |

**Tests added:** 6 new tests in `tests/test_adapter.py`
- `TestAdapterIdempotency` (4 tests): task/project skip when no `status` key, tag/folder skip when already snake_case
- `TestAdaptRepetitionRule::test_unknown_schedule_type_raises`: unknown scheduleType ValueError
- `TestAdaptRepetitionRule::test_unknown_anchor_date_key_raises`: unknown anchorDateKey ValueError

**Coverage:** adapter.py 91% → 100%, total 97.74% → 98.50%
