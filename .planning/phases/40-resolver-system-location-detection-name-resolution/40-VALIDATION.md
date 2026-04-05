---
phase: 40
slug: resolver-system-location-detection-name-resolution
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-05
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_service_resolve.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_service_resolve.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 40-01-01 | 01 | 1 | SLOC-02, SLOC-03, NRES-06 | — | N/A | unit | `uv run pytest tests/test_service_resolve.py -x -q` | ✅ | ⬜ pending |
| 40-01-02 | 01 | 1 | NRES-01, NRES-02, NRES-03, NRES-04, NRES-05 | — | N/A | unit | `uv run pytest tests/test_service_resolve.py -x -q` | ✅ | ⬜ pending |
| 40-01-03 | 01 | 1 | NRES-08 | — | N/A | unit | `uv run pytest tests/test_service_resolve.py -x -q` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

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
