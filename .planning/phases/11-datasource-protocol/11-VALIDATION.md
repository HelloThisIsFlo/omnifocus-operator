---
phase: 11
slug: datasource-protocol
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 11 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `pyproject.toml` (pytest section) |
| **Quick run command** | `uv run python -m pytest tests/ -x -q` |
| **Full suite command** | `uv run python -m pytest tests/ -q` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/ -x -q`
- **After every plan wave:** Run `uv run python -m pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 11-01-01 | 01 | 1 | ARCH-01 | unit | `uv run python -m pytest tests/test_repository.py -x -q` | Yes (restructured) | pending |
| 11-01-02 | 01 | 1 | ARCH-01 | unit | `uv run python -m pytest tests/test_repository.py -x -q` | Yes (restructured) | pending |
| 11-01-03 | 01 | 1 | ARCH-02 | unit | `uv run python -m pytest tests/test_service.py tests/test_server.py -x -q` | Yes (updated) | pending |
| 11-01-04 | 01 | 1 | ARCH-03 | unit | `uv run python -m pytest tests/test_repository.py tests/test_service.py -x -q` | Yes (migrated) | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. Tests will be migrated, not created from scratch.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
