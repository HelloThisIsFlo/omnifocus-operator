---
phase: 12
slug: sqlite-reader
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
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
| 12-01-01 | 01 | 1 | SQLITE-01 | unit | `uv run pytest tests/test_hybrid_repository.py::test_read_all_entities -x` | Wave 0 | pending |
| 12-01-02 | 01 | 1 | SQLITE-02 | unit | `uv run pytest tests/test_hybrid_repository.py::test_read_only_connection -x` | Wave 0 | pending |
| 12-01-03 | 01 | 1 | SQLITE-03 | unit | `uv run pytest tests/test_hybrid_repository.py::test_status_mapping -x` | Wave 0 | pending |
| 12-01-04 | 01 | 1 | SQLITE-04 | integration | `uv run pytest tests/test_hybrid_repository.py::test_reads_without_omnifocus -x` | Wave 0 | pending |
| 12-02-01 | 02 | 1 | FRESH-01 | unit | `uv run pytest tests/test_hybrid_repository.py::test_freshness_wal_polling -x` | Wave 0 | pending |
| 12-02-02 | 02 | 1 | FRESH-02 | unit | `uv run pytest tests/test_hybrid_repository.py::test_freshness_db_fallback -x` | Wave 0 | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hybrid_repository.py` -- stubs for SQLITE-01 through FRESH-02
- [ ] Test helper: `create_test_db()` function (in test file or conftest) -- builds in-memory SQLite with schema and seed rows
- [ ] UAT script: `uat/test_sqlite_reader.py` -- validates against real OmniFocus SQLite (manual only, SAFE-01/02)

*Existing pytest infrastructure covers framework installation.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Real OmniFocus SQLite read | SQLITE-01 | Requires live OmniFocus database (SAFE-01/02) | Run `uat/test_sqlite_reader.py` against real DB |
| WAL polling with live OmniFocus | FRESH-01 | Requires OmniFocus writing to DB | Make change in OmniFocus, verify server detects WAL mtime change |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
