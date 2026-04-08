---
phase: 47
slug: cross-path-equivalence-breaking-changes
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-08
---

# Phase 47 — Validation Strategy

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
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 47-01-01 | 01 | 1 | BREAK-03 | — | N/A | unit | `uv run pytest tests/contracts/ -x -q -k "availability"` | ✅ | ⬜ pending |
| 47-01-02 | 01 | 1 | BREAK-06 | — | N/A | unit | `uv run pytest tests/contracts/ -x -q -k "lifecycle"` | ✅ | ⬜ pending |
| 47-02-01 | 02 | 1 | BREAK-04, BREAK-05 | — | N/A | unit | `uv run pytest tests/service/ -x -q -k "defer_hint"` | ❌ W0 | ⬜ pending |
| 47-02-02 | 02 | 1 | BREAK-03 | — | N/A | unit | `uv run pytest tests/service/ -x -q -k "remaining"` | ❌ W0 | ⬜ pending |
| 47-03-01 | 03 | 2 | EXEC-10, EXEC-11 | — | N/A | integration | `uv run pytest tests/test_cross_path_equivalence.py -x -q` | ✅ | ⬜ pending |
| 47-04-01 | 04 | 2 | BREAK-07 | — | N/A | unit | `uv run pytest tests/ -x -q -k "description"` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- Existing infrastructure covers all phase requirements. Test files for cross-path equivalence, contracts, and service already exist.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Tool descriptions render correctly in MCP client | BREAK-07 | Agent-facing display quality is subjective | Inspect `list_tasks` tool description in Claude Desktop inspector |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
