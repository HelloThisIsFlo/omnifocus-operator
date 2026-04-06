---
phase: 42
slug: read-output-restructure
status: approved
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 42 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q --timeout=30` |
| **Estimated runtime** | ~24 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q --timeout=30`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 24 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 42-01-01 | 01 | 1 | DESC-01, DESC-02 | — | N/A | unit | `uv run pytest tests/test_descriptions.py -x -q` | ✅ | ✅ green |
| 42-01-02 | 01 | 1 | MODL-04, MODL-05, MODL-06 | T-42-01 | Read-only output; shape change intentional | unit | `uv run pytest tests/test_models.py -x -q` | ✅ | ✅ green |
| 42-01-03 | 01 | 1 | MODL-07, MODL-08 | — | N/A | unit | `uv run pytest tests/test_models.py -x -q` | ✅ | ✅ green |
| 42-02-01 | 02 | 2 | READ-01, READ-02 | T-42-02 | Names already visible; no new info exposure | integration | `uv run pytest tests/test_hybrid_repository.py -x -q` | ✅ | ✅ green |
| 42-02-02 | 02 | 2 | READ-03, READ-04, READ-05, READ-06 | T-42-02 | Names already visible; no new info exposure | integration | `uv run pytest tests/test_hybrid_repository.py -x -q` | ✅ | ✅ green |
| 42-03-01 | 03 | 3 | READ-07 | T-42-03 | Test data only; no production impact | integration | `uv run pytest tests/test_adapter.py tests/test_cross_path_equivalence.py -x -q` | ✅ | ✅ green |
| 42-03-02 | 03 | 3 | READ-07 | — | N/A | schema | `uv run pytest tests/test_output_schema.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Golden master snapshots match new output shape | READ-01 thru READ-07 | Golden master re-capture is human-only per GOLD-01 | Run `just gm-capture` after all model changes land |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 24s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-06

---

## Validation Audit 2026-04-06

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
