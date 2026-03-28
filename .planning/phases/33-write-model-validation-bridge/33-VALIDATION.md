---
phase: 33
slug: write-model-validation-bridge
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-28
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 33-01-01 | 01 | 1 | ADD-01..ADD-14 | unit | `uv run pytest tests/contracts/ -x -q -k repetition` | ✅ | ⬜ pending |
| 33-02-01 | 02 | 1 | VALID-01..VALID-05 | unit | `uv run pytest tests/ -x -q -k validation` | ❌ W0 | ⬜ pending |
| 33-03-01 | 03 | 2 | EDIT-01..EDIT-16 | unit | `uv run pytest tests/service/ -x -q -k edit` | ✅ | ⬜ pending |
| 33-04-01 | 04 | 2 | ADD-01..ADD-14 | integration | `uv run pytest tests/service/ -x -q -k add` | ✅ | ⬜ pending |
| 33-05-01 | 05 | 3 | ADD-01, EDIT-01 | integration | `uv run pytest tests/ -x -q -k bridge` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Existing test infrastructure covers all phase requirements — no new fixtures needed
- [ ] `tests/contracts/` — contract model tests (extend existing)
- [ ] `tests/service/` — pipeline tests (extend existing)

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Task appears in OmniFocus with correct recurrence | ADD-01 | Requires real OmniFocus (SAFE-01) | UAT via `uat/` scripts against live database |
| Edited rule reflects in OmniFocus UI | EDIT-01 | Requires real OmniFocus (SAFE-01) | UAT via `uat/` scripts against live database |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
