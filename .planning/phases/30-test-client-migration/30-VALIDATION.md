---
phase: 30
slug: test-client-migration
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/server/ -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/server/ -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-01-01 | 01 | 1 | TEST-01 | migration | `uv run pytest tests/server/test_server.py -x -q` | ✅ | ⬜ pending |
| 30-01-02 | 01 | 1 | TEST-02 | migration | `uv run pytest tests/server/test_server.py -x -q` | ✅ | ⬜ pending |
| 30-02-01 | 02 | 1 | TEST-03 | migration | `uv run pytest tests/server/test_server_errors.py -x -q` | ✅ | ⬜ pending |
| 30-03-01 | 03 | 2 | TEST-04 | cleanup | `uv run pytest tests/ -x -q` | ✅ | ⬜ pending |
| 30-04-01 | 04 | 2 | TEST-05 | regression | `uv run pytest` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
