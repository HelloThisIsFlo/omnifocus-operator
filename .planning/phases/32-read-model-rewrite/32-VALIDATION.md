---
phase: 32
slug: read-model-rewrite
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
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
| 32-01-01 | 01 | 1 | READ-01 | unit | `uv run python -m pytest tests/test_models.py -x -k RepetitionRule` | ✅ (rewrite needed) | ⬜ pending |
| 32-01-02 | 01 | 1 | READ-02 | unit | `uv run python -m pytest tests/test_rrule.py -x` | ❌ W0 | ⬜ pending |
| 32-01-03 | 01 | 1 | READ-04 | unit | `uv run python -m pytest tests/test_rrule.py -x -k round_trip` | ❌ W0 | ⬜ pending |
| 32-02-01 | 02 | 2 | READ-03 | integration | `uv run python -m pytest tests/test_hybrid_repository.py tests/test_adapter.py -x -k repetition` | ✅ (update needed) | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_rrule.py` — stubs for READ-02, READ-04 (parser unit tests, round-trip tests)
- [ ] No new fixtures needed — existing `conftest.py` factories need updating, not new fixtures

*Existing infrastructure covers most requirements. Wave 0 creates test stubs for the new rrule parser module.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OmniFocus RRULE data parses correctly | READ-02 | Golden master uses snapshots, not live DB | UAT: `get_task` on a repeating task, verify structured repetitionRule |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
