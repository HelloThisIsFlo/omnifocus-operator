---
phase: 31
slug: middleware-logging
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-26
---

# Phase 31 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio 1.3.0 |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_server.py tests/test_middleware.py -x -q --no-cov` |
| **Full suite command** | `uv run pytest --timeout=30` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_server.py tests/test_middleware.py -x -q --no-cov`
- **After every plan wave:** Run `uv run pytest --timeout=30`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 31-01-01 | 01 | 1 | MW-01 | unit | `uv run pytest tests/test_middleware.py -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 31-01-02 | 01 | 1 | MW-02 | grep | `! grep -r 'log_tool_call' src/` | n/a | ⬜ pending |
| 31-01-03 | 01 | 1 | MW-03 | integration | `uv run pytest tests/test_server.py -x -q --no-cov` | ✅ | ⬜ pending |
| 31-02-01 | 02 | 2 | LOG-01 | unit | `uv run pytest tests/test_middleware.py -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 31-02-02 | 02 | 2 | LOG-02 | unit | `uv run pytest tests/test_middleware.py -x -q --no-cov` | ❌ W0 | ⬜ pending |
| 31-02-03 | 02 | 2 | LOG-03 | grep | `grep -r 'getLogger("omnifocus_operator")' src/ \| grep -v __main__` returns 0 | n/a | ⬜ pending |
| 31-02-04 | 02 | 2 | LOG-04 | grep | `! grep -r 'hijack' src/` | n/a | ⬜ pending |
| 31-02-05 | 02 | 2 | LOG-05 | grep | `! grep -rP 'ctx\.(info\|warning)\(' src/` | n/a | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_middleware.py` — stubs for MW-01, LOG-01, LOG-02 (middleware logs correctly, handler setup verification)
- [ ] Middleware tests need: mock logger to capture log calls, verify entry/exit/error messages, verify timing is non-zero

*Existing test infrastructure (`tests/test_server.py`, `conftest.py`) covers integration verification for MW-03.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Logs visible in Claude Desktop | LOG-01 | Requires live MCP session | Start server in Claude Desktop, call any tool, check Developer > Logs |
| Logs written to file | LOG-02 | Requires real file system interaction | Call tool, check `~/Library/Logs/omnifocus-operator.log` |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
