---
phase: 50
slug: use-omnifocus-settings-api-for-date-preferences-and-due-soon
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-11
---

# Phase 50 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q --timeout=30`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 50-01-01 | 01 | 1 | PREF-01 | — | N/A | unit | `uv run pytest tests/ -x -q -k "settings or preferences"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_preferences.py` — stubs for PREF-01 through PREF-13
- [ ] Existing `tests/conftest.py` — shared fixtures (InMemoryBridge handler for `get_settings`)

*Existing infrastructure covers most phase requirements. Wave 0 adds preferences-specific test stubs and InMemoryBridge handler.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Bridge reads live OmniFocus settings | PREF-01 | Requires real OmniFocus app | UAT: call `get_settings` via Claude Code CLI, verify returned values match OmniFocus preferences |
| Date-only write applies user's default time | PREF-05 | Requires real OmniFocus to verify task creation time | UAT: add task with date-only dueDate, verify in OmniFocus that configured default time is applied |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
