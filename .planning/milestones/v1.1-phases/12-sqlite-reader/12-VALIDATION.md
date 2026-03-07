---
phase: 12
slug: sqlite-reader
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-07
validated: 2026-03-07
---

# Phase 12 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run pytest tests/test_hybrid_repository.py -x --timeout=10` |
| **Full suite command** | `uv run pytest tests/ --timeout=30` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_hybrid_repository.py -x --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 12-01-01 | 01 | 1 | SQLITE-01 | unit | `uv run pytest tests/test_hybrid_repository.py::TestReadAllEntities -x` | Yes | green |
| 12-01-02 | 01 | 1 | SQLITE-02 | unit | `uv run pytest tests/test_hybrid_repository.py::TestConnectionSemantics -x` | Yes | green |
| 12-01-03 | 01 | 1 | SQLITE-03 | unit | `uv run pytest tests/test_hybrid_repository.py::TestTaskStatus -x` | Yes | green |
| 12-01-04 | 01 | 1 | SQLITE-04 | integration | `uv run pytest tests/test_hybrid_repository.py::TestEdgeCases::test_reads_without_omnifocus -x` | Yes | green |
| 12-02-01 | 02 | 1 | FRESH-01 | unit | `uv run pytest tests/test_hybrid_repository.py::TestFreshness::test_freshness_wal_polling -x` | Yes | green |
| 12-02-02 | 02 | 1 | FRESH-02 | unit | `uv run pytest tests/test_hybrid_repository.py::TestFreshness::test_freshness_db_fallback -x` | Yes | green |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [x] `tests/test_hybrid_repository.py` -- 48 tests covering SQLITE-01 through FRESH-02
- [x] Test helper: `create_test_db()` function in test file -- builds file-based SQLite with OmniFocus schema and seed rows
- [x] UAT script: `uat/test_sqlite_reader.py` -- validates against real OmniFocus SQLite (manual only, SAFE-01/02)

*All Wave 0 requirements satisfied during phase execution.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OmniFocus SQLite read | SQLITE-01 | Requires live OmniFocus database (SAFE-01/02) | Run `uat/test_sqlite_reader.py` against real DB |
| WAL polling with live OmniFocus | FRESH-01 | Requires OmniFocus writing to DB | Make change in OmniFocus, verify server detects WAL mtime change |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s (48 tests in 2.87s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 6 requirements (SQLITE-01..04, FRESH-01..02) have automated test coverage across 48 test cases. Full suite: 284 tests green.
