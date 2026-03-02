---
phase: 5
slug: service-layer-and-mcp-server
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 5 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ --tb=short` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ --tb=short`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 05-01-01 | 01 | 1 | ARCH-01, ARCH-02 | unit | `uv run pytest tests/test_service.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-02 | 01 | 1 | ARCH-01, ARCH-02 | unit | `uv run pytest tests/test_server.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-03 | 01 | 1 | TOOL-01, TOOL-02, TOOL-03 | integration | `uv run pytest tests/test_list_all.py -x -q` | ❌ W0 | ⬜ pending |
| 05-01-04 | 01 | 1 | TOOL-04 | unit | `uv run pytest tests/test_stderr.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_service.py` — stubs for OperatorService
- [ ] `tests/test_server.py` — stubs for MCP server lifespan and DI
- [ ] `tests/test_list_all.py` — stubs for list_all tool integration
- [ ] `tests/test_stderr.py` — stubs for stdout redirect safety

*Existing pytest infrastructure covers framework requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RealBridge startup error | ARCH-02 | RealBridge is Phase 8 | Set `OMNIFOCUS_BRIDGE=real`, verify clear error message |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
