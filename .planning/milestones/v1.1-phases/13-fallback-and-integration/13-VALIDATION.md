---
phase: 13
slug: fallback-and-integration
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-07
validated: 2026-03-07
---

# Phase 13 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv) |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Suite size** | 313 tests |
| **Runtime** | ~11 seconds |
| **Coverage** | 98% |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 13-01-01 | 01 | 1 | FALL-01 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | Yes | green |
| 13-01-02 | 01 | 1 | FALL-01 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | Yes | green |
| 13-01-03 | 01 | 1 | FALL-03 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | Yes | green |
| 13-01-04 | 01 | 1 | FALL-03 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | Yes | green |
| 13-02-01 | 02 | 1 | FALL-02 | unit | `uv run pytest tests/test_adapter.py -x -q` | Yes | green |
| 13-02-02 | 02 | 2 | FALL-03 | integration | `uv run pytest tests/test_server.py -x -q` | Yes | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/test_repository_factory.py` — 13 tests for FALL-01, FALL-03 (factory routing + error messages)
- [x] `tests/test_adapter.py` — `TestFall02BridgeAvailabilityLimitation` for FALL-02 bridge availability
- [x] `tests/test_server.py` — error-serving mode for SQLite-not-found path

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bridge mode against live OmniFocus | FALL-01 | Requires real OmniFocus + RealBridge (SAFE-01) | UAT: Set `OMNIFOCUS_REPOSITORY=bridge`, start server, query tasks |
| Error message readability | FALL-03 | Subjective clarity check | Read error output, verify path + fix + workaround sections |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 3 requirements (FALL-01, FALL-02, FALL-03) have comprehensive automated test coverage. 313 tests pass, 98% coverage.
