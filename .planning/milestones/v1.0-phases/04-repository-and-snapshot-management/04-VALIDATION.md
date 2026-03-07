---
phase: 4
slug: repository-and-snapshot-management
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-02
validated: 2026-03-07
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.3.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_repository.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~0.2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_repository.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | Status |
|---------|------|------|-------------|-----------|-------------------|--------|
| 04-01-01 | 01 | 1 | SNAP-01 | unit | `uv run pytest tests/test_repository.py::TestSNAP01FirstCall -x` | COVERED |
| 04-01-02 | 01 | 1 | SNAP-02 | unit | `uv run pytest tests/test_repository.py::TestSNAP02CachedReturn -x` | COVERED |
| 04-01-03 | 01 | 1 | SNAP-03 | unit | `uv run pytest tests/test_repository.py::TestSNAP03ObjectIdentity -x` | COVERED |
| 04-01-04 | 01 | 1 | SNAP-04 | unit | `uv run pytest tests/test_repository.py::TestSNAP04MtimeRefresh -x` | COVERED |
| 04-01-05 | 01 | 1 | SNAP-05 | unit | `uv run pytest tests/test_repository.py::TestSNAP05Concurrency -x` | COVERED |
| 04-01-06 | 01 | 1 | SNAP-06 | unit | `uv run pytest tests/test_repository.py::TestSNAP01FirstCall -x` | COVERED |

*SNAP-06 was revised to "lazy population on first call" (quick/1). Covered by SNAP-01 first-call tests.*

*Status: COVERED · PARTIAL · MISSING*

---

## Additional Coverage (beyond SNAP requirements)

| Area | Tests | Count |
|------|-------|-------|
| Error propagation | `TestErrorPropagation` | 6 |
| Concurrency edge cases | `TestConcurrencyEdgeCases` | 1 |
| FileMtimeSource integration | `TestFileMtimeSource` | 3 |

**Total: 19 tests, all green.**

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OmniFocus `.ofocus` mtime updates on data change | SNAP-03/04 | Requires live OmniFocus + real filesystem | Phase 8 UAT: edit a task in OmniFocus, verify mtime changes, verify snapshot refreshes |

---

## Validation Sign-Off

- [x] All tasks have automated verification
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] All SNAP requirements covered by tests
- [x] No watch-mode flags
- [x] Feedback latency < 5s (0.2s actual)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated

---

## Validation Audit 2026-03-07

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Total tests | 19 |
| All green | yes |
