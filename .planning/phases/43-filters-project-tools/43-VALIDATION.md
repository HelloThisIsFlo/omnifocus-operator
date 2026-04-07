---
phase: 43
slug: filters-project-tools
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-07
---

# Phase 43 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 43-01-01 | 01 | 1 | FILT-01 | — | N/A | unit | `uv run pytest tests/ -x -q -k "inbox_filter"` | ❌ W0 | ⬜ pending |
| 43-01-02 | 01 | 1 | FILT-02 | — | N/A | unit | `uv run pytest tests/ -x -q -k "inbox_name_filter"` | ❌ W0 | ⬜ pending |
| 43-01-03 | 01 | 1 | FILT-03, FILT-04, FILT-05 | — | N/A | unit | `uv run pytest tests/ -x -q -k "contradictory"` | ❌ W0 | ⬜ pending |
| 43-02-01 | 02 | 1 | PROJ-01, PROJ-02 | — | N/A | unit | `uv run pytest tests/ -x -q -k "get_project_inbox"` | ❌ W0 | ⬜ pending |
| 43-02-02 | 02 | 1 | PROJ-03 | — | N/A | unit | `uv run pytest tests/ -x -q -k "list_projects_inbox"` | ❌ W0 | ⬜ pending |
| 43-03-01 | 03 | 2 | NRES-07 | — | N/A | unit | `uv run pytest tests/ -x -q -k "nres07"` | ❌ W0 | ⬜ pending |
| 43-04-01 | 04 | 2 | DESC-03, DESC-04 | — | N/A | unit | `uv run pytest tests/ -x -q -k "description"` | ❌ W0 | ⬜ pending |

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
