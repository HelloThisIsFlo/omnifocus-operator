---
phase: 10
slug: model-overhaul
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-07
---

# Phase 10 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + vitest |
| **Config file** | `pyproject.toml` (pytest section) + `vitest.config.js` |
| **Quick run command** | `uv run pytest tests/test_models.py -x` |
| **Full suite command** | `uv run pytest && cd bridge && npx vitest run` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest -x`
- **After every plan wave:** Run `uv run pytest && cd bridge && npx vitest run`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 10-01-01 | 01 | 1 | MODEL-01, MODEL-02 | unit | `uv run pytest tests/test_models.py -x` | Yes (needs update) | pending |
| 10-01-02 | 01 | 1 | MODEL-03 | unit | `uv run pytest tests/test_models.py -x` | Yes (needs update) | pending |
| 10-02-01 | 02 | 2 | MODEL-04, MODEL-05 | unit | `uv run pytest tests/test_models.py -x` | Yes (needs update) | pending |
| 10-02-02 | 02 | 2 | MODEL-06 | integration | `uv run pytest && cd bridge && npx vitest run` | Yes (needs update) | pending |

*Status: pending · green · red · flaky*

---

## Wave 0 Requirements

- [ ] `bridge/adapter.py` — new module for bridge-to-model mapping
- [ ] `uat/test_model_overhaul.py` — new UAT script

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RealBridge live data roundtrip | MODEL-06 | Requires live OmniFocus database | Run `uat/test_model_overhaul.py` against local OmniFocus |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
