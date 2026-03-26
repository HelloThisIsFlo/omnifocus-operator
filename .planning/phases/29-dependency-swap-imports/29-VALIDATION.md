---
phase: 29
slug: dependency-swap-imports
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 29 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_server.py -x --no-cov` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~30 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_server.py -x --no-cov`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 30 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 29-01-01 | 01 | 1 | DEP-01 | integration | `uv run pytest tests/test_server.py -x --no-cov` | ✅ | ⬜ pending |
| 29-01-02 | 01 | 1 | DEP-02 | smoke | `grep -r 'mcp.server.fastmcp' src/ && exit 1 \|\| exit 0` | ✅ | ⬜ pending |
| 29-01-03 | 01 | 1 | DEP-03 | smoke | `grep 'ctx.lifespan_context' src/omnifocus_operator/server.py` | ✅ | ⬜ pending |
| 29-01-04 | 01 | 1 | DEP-04 | smoke | `grep 'fastmcp>=3.1.1' pyproject.toml` | ✅ | ⬜ pending |
| 29-02-01 | 02 | 1 | PROG-01 | manual | No test — ctx.report_progress no-ops in test client | N/A | ⬜ pending |
| 29-02-02 | 02 | 1 | PROG-02 | manual | No test — ctx.report_progress no-ops in test client | N/A | ⬜ pending |
| 29-03-01 | 03 | 2 | DOC-01 | smoke | `grep 'fastmcp>=3.1.1' README.md` | ✅ | ⬜ pending |
| 29-03-02 | 03 | 2 | DOC-02 | smoke | `grep 'fastmcp' docs/index.html` | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The 534+ existing tests validate that all 6 tools remain functional after the import migration. No new test files needed for Phase 29.

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| add_tasks reports progress | PROG-01 | ctx.report_progress no-ops in test client | Call add_tasks with multiple items via Claude Desktop, verify progress callbacks appear in client |
| edit_tasks reports progress | PROG-02 | ctx.report_progress no-ops in test client | Call edit_tasks with multiple items via Claude Desktop, verify progress callbacks appear in client |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 30s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
