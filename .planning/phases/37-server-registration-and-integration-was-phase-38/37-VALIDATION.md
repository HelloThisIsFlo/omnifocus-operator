---
phase: 37
slug: server-registration-and-integration-was-phase-38
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-03
---

# Phase 37 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q --tb=short` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --tb=short`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 37-01-01 | 01 | 1 | SRCH-01, SRCH-02, SRCH-03, SRCH-04 | unit | `uv run pytest tests/test_cross_path_equivalence.py -x -q -k "search"` | ✅ | ✅ green |
| 37-01-02 | 01 | 1 | RTOOL-01, RTOOL-02, RTOOL-03 | unit | `uv run pytest tests/test_cross_path_equivalence.py -x -q -k "perspectives"` | ✅ | ✅ green |
| 37-02-01 | 02 | 2 | INFRA-05 | integration | `uv run pytest tests/test_server.py -x -q -k "list_"` | ✅ | ✅ green |
| 37-02-02 | 02 | 2 | DOC-10, DOC-11, DOC-12, DOC-13, DOC-14 | unit | `uv run pytest tests/test_descriptions.py -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements. New test files will be created as part of plan tasks (not a separate Wave 0).

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tool descriptions readable by LLM | DOC-10..14 | Subjective quality | Review tool descriptions in MCP inspector |

*All other behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** ✅ compliant

## Validation Audit 2026-04-03

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 4 task-requirement mappings have automated test coverage. 1479 tests passing, 98% coverage. No auditor agent needed.
