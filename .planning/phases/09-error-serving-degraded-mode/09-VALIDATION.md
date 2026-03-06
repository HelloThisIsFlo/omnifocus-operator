---
phase: 9
slug: error-serving-degraded-mode
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-06
---

# Phase 9 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x + pytest-asyncio |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_server.py tests/test_service.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_server.py tests/test_service.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 09-01-01 | 01 | 1 | ERR-01 | unit | `uv run pytest tests/test_service.py -x -k error_service_raises` | ❌ W0 | ⬜ pending |
| 09-01-02 | 01 | 1 | ERR-02 | unit | `uv run pytest tests/test_service.py -x -k error_getattr` | ❌ W0 | ⬜ pending |
| 09-01-03 | 01 | 1 | ERR-03 | integration | `uv run pytest tests/test_server.py -x -k error_lifespan` | ❌ W0 | ⬜ pending |
| 09-01-04 | 01 | 1 | ERR-04 | integration | `uv run pytest tests/test_server.py -x -k degraded` | ❌ W0 | ⬜ pending |
| 09-01-05 | 01 | 1 | ERR-05 | unit | `uv run pytest tests/test_server.py -x -k startup` | ✅ needs update | ⬜ pending |
| 09-01-06 | 01 | 1 | ERR-06 | integration | `uv run pytest tests/test_server.py -x -k error_log` | ❌ W0 | ⬜ pending |
| 09-01-07 | 01 | 1 | ERR-07 | integration | `uv run pytest tests/test_server.py -x -k warning` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_service.py` — error service unit tests (ERR-01, ERR-02)
- [ ] `tests/test_server.py` — degraded mode integration tests (ERR-03, ERR-04, ERR-06, ERR-07)
- [ ] Update existing `test_default_real_bridge_fails_at_startup` to verify degraded mode instead of ExceptionGroup (ERR-05)

*Existing infrastructure covers framework and fixtures.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
