---
phase: 9
slug: error-serving-degraded-mode
status: audited
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-06
audited: 2026-03-06
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_service.py tests/test_server.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_service.py tests/test_server.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | ERR-01 | unit | `uv run pytest tests/test_service.py -x -k test_getattr_raises_runtime_error` | tests/test_service.py:148 | COVERED |
| 09-01-02 | 01 | 1 | ERR-02 | unit | `uv run pytest tests/test_service.py -x -k test_getattr_raises_for_arbitrary_attribute` | tests/test_service.py:156 | COVERED |
| 09-01-03 | 01 | 1 | ERR-03 | integration | `uv run pytest tests/test_server.py -x -k test_tool_call_returns_error_when_lifespan_fails` | tests/test_server.py:459 | COVERED |
| 09-01-04 | 01 | 1 | ERR-04 | integration | `uv run pytest tests/test_server.py -x -k degraded` | tests/test_server.py:459 | COVERED |
| 09-01-05 | 01 | 1 | ERR-05 | integration | `uv run pytest tests/test_server.py -x -k test_default_real_bridge_fails_at_startup` | tests/test_server.py:128 | COVERED |
| 09-01-06 | 01 | 1 | ERR-06 | integration | `uv run pytest tests/test_server.py -x -k test_degraded_mode_logs_traceback_at_error_level` | tests/test_server.py:483 | COVERED |
| 09-01-07 | 01 | 1 | ERR-07 | integration | `uv run pytest tests/test_server.py -x -k test_degraded_mode_logs_warning_on_tool_call` | tests/test_server.py:511 | COVERED |

*Status: COVERED · PARTIAL · MISSING*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 5s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** passed

---

## Validation Audit 2026-03-06

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

All 7 requirements (ERR-01 through ERR-07) have dedicated automated tests.
29 tests pass, 80.04% coverage. Full suite green.
