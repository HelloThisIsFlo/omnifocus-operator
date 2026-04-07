---
phase: 45
slug: date-models-resolution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 45 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ with pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_date_filter_contracts.py tests/test_resolve_dates.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_date_filter_contracts.py tests/test_resolve_dates.py -x -q`
- **After every plan wave:** Run `uv run pytest -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 45-01-01 | 01 | 1 | DATE-01 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-01-02 | 01 | 1 | DATE-02 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-01-03 | 01 | 1 | DATE-03 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-01-04 | 01 | 1 | DATE-04 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-01-05 | 01 | 1 | DATE-05 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-01-06 | 01 | 1 | DATE-06 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-01-07 | 01 | 1 | DATE-09 | — | N/A | unit | `uv run pytest tests/test_date_filter_contracts.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-01 | 02 | 1 | RESOLVE-01 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-02 | 02 | 1 | RESOLVE-02 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-03 | 02 | 1 | RESOLVE-03 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-04 | 02 | 1 | RESOLVE-04 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-05 | 02 | 1 | RESOLVE-05 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-06 | 02 | 1 | RESOLVE-06 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-07 | 02 | 1 | RESOLVE-07 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-08 | 02 | 1 | RESOLVE-08 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-09 | 02 | 1 | RESOLVE-09 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |
| 45-02-10 | 02 | 1 | RESOLVE-10 | — | N/A | unit | `uv run pytest tests/test_resolve_dates.py -x -q` | No -- Wave 0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_date_filter_contracts.py` — DateFilter model validation, union behavior on ListTasksQuery, field-specific shortcuts (DATE-01 through DATE-09)
- [ ] `tests/test_resolve_dates.py` — resolver function for all input forms, boundary conditions, week start config (RESOLVE-01 through RESOLVE-10)
- [ ] No framework install needed — pytest already configured

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
