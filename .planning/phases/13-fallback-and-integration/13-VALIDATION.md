---
phase: 13
slug: fallback-and-integration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
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
| **Estimated runtime** | ~15 seconds |

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
| 13-01-01 | 01 | 1 | FALL-01 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 | pending |
| 13-01-02 | 01 | 1 | FALL-01 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 | pending |
| 13-01-03 | 01 | 1 | FALL-03 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 | pending |
| 13-01-04 | 01 | 1 | FALL-03 | unit | `uv run pytest tests/test_repository_factory.py -x -q` | No -- Wave 0 | pending |
| 13-02-01 | 02 | 1 | FALL-02 | unit | `uv run pytest tests/test_adapter.py -x -q` | Partial | pending |
| 13-02-02 | 02 | 2 | FALL-03 | integration | `uv run pytest tests/test_server.py -x -q` | Partial | pending |

*Status: pending / green / red / flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_repository_factory.py` — stubs for FALL-01, FALL-03 (factory routing + error messages)
- [ ] Adapter test assertion for FALL-02 bridge availability (may extend existing `tests/test_adapter.py`)
- [ ] Server integration test for SQLite-not-found -> ErrorOperatorService path

*These must be created before execution begins.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bridge mode against live OmniFocus | FALL-01 | Requires real OmniFocus + RealBridge (SAFE-01) | UAT: Set `OMNIFOCUS_REPOSITORY=bridge`, start server, query tasks |
| Error message readability | FALL-03 | Subjective clarity check | Read error output, verify path + fix + workaround sections |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
