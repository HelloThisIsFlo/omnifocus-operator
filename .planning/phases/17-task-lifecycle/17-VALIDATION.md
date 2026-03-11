---
phase: 17
slug: task-lifecycle
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-11
---

# Phase 17 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | pyproject.toml |
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
| 17-01-01 | 01 | 1 | LIFE-04 | unit | `uv run pytest tests/test_models.py -x -k lifecycle` | ❌ W0 | ⬜ pending |
| 17-01-02 | 01 | 1 | LIFE-01 | unit | `uv run pytest tests/test_service.py -x -k lifecycle_complete` | ❌ W0 | ⬜ pending |
| 17-01-03 | 01 | 1 | LIFE-02 | unit | `uv run pytest tests/test_service.py -x -k lifecycle_drop` | ❌ W0 | ⬜ pending |
| 17-01-04 | 01 | 1 | LIFE-05 | unit | `uv run pytest tests/test_service.py -x -k "lifecycle and (repeat or noop or cross)"` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- None — existing test infrastructure covers all phase requirements. New tests will be added to existing test files (`test_service.py`, `test_server.py`, `test_models.py`, `test_bridge.test.js`).

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Complete task in live OmniFocus | LIFE-01 | Requires RealBridge + live OmniFocus (SAFE-01) | UAT: edit_tasks with lifecycle="complete", verify in OmniFocus |
| Drop task in live OmniFocus | LIFE-02 | Requires RealBridge + live OmniFocus (SAFE-01) | UAT: edit_tasks with lifecycle="drop", verify in OmniFocus |
| Repeating task behavior | LIFE-05 | Repeating task behavior only observable in live OmniFocus | UAT: complete a repeating task, verify new instance created |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
