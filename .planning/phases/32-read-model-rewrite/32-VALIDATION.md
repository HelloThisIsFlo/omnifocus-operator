---
phase: 32
slug: read-model-rewrite
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-28
audited: 2026-03-28
---

# Phase 32 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run python -m pytest tests/ -x -q --tb=short` |
| **Full suite command** | `uv run python -m pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 32-01-01 | 01 | 1 | READ-01 | unit | `uv run python -m pytest tests/test_models.py -x -k RepetitionRule` | ✅ | ✅ green |
| 32-01-02 | 01 | 1 | READ-02 | unit | `uv run python -m pytest tests/test_rrule.py -x` | ✅ | ✅ green |
| 32-01-03 | 01 | 1 | READ-04 | unit | `uv run python -m pytest tests/test_rrule.py -x -k round_trip` | ✅ | ✅ green |
| 32-02-01 | 02 | 2 | READ-03 | integration | `uv run python -m pytest tests/test_hybrid_repository.py tests/test_adapter.py -x -k repetition` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_rrule.py` — 89 tests covering parser, builder, models, round-trips, golden master
- [x] No new fixtures needed — existing factories updated in execution

*All Wave 0 requirements fulfilled during phase execution.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OmniFocus RRULE data parses correctly | READ-02 | Golden master uses snapshots, not live DB | UAT: `get_task` on a repeating task, verify structured repetitionRule |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-28

---

## Validation Audit 2026-03-28

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

**Coverage summary:**
- READ-01: 89 unit tests (frequency models) + 9 model tests (RepetitionRule shape)
- READ-02: 10 parser frequency-type tests + 15 golden master RRULE strings
- READ-03: 8 adapter integration tests + 2 hybrid repo integration tests
- READ-04: 29 round-trip + builder tests
- Full suite: 830 tests, 97% coverage, all green
