---
phase: 27
slug: repository-contract-tests-for-behavioral-equivalence
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-21
---

# Phase 27 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x with pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_bridge_contract.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_bridge_contract.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| TBD | TBD | TBD | INFRA-13 | manual (UAT) | `uv run python uat/capture_golden_master.py` | ❌ W0 | ⬜ pending |
| TBD | TBD | TBD | INFRA-14 | unit | `uv run pytest tests/test_bridge_contract.py -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `uat/capture_golden_master.py` — interactive capture script
- [ ] `tests/golden/` — golden master fixture directory
- [ ] `tests/test_bridge_contract.py` — CI contract tests

*Existing infrastructure covers test framework and configuration.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Golden master capture from RealBridge | INFRA-13 | Requires live OmniFocus database (SAFE-01) | Run `uv run python uat/capture_golden_master.py`, follow guided prompts |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
