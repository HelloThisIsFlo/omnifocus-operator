---
phase: 22
slug: service-decomposition
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-19
---

# Phase 22 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest (via uv run) |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run python -m pytest tests/test_service.py -x -q` |
| **Full suite command** | `uv run python -m pytest tests/ -x -q` |
| **Estimated runtime** | ~8 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest tests/test_service.py -x -q`
- **After every plan wave:** Run `uv run python -m pytest tests/ -x -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 22-01-01 | 01 | 1 | SVCR-04 | integration | `uv run python -m pytest tests/test_service.py tests/test_server.py -x -q` | ✅ | ⬜ pending |
| 22-01-02 | 01 | 1 | SVCR-01 | unit | `uv run python -m pytest tests/test_service_resolve.py -x -q` | ❌ W0 | ⬜ pending |
| 22-01-03 | 01 | 1 | SVCR-02 | unit | `uv run python -m pytest tests/test_service_domain.py -x -q` | ❌ W0 | ⬜ pending |
| 22-01-04 | 01 | 1 | SVCR-03 | unit | `uv run python -m pytest tests/test_service_payload.py -x -q` | ❌ W0 | ⬜ pending |
| 22-01-05 | 01 | 1 | SVCR-05 | unit | `uv run python -m pytest tests/test_service_resolve.py tests/test_service_domain.py tests/test_service_payload.py -x -q` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_service_resolve.py` — stubs for SVCR-01 (Resolver unit tests with real InMemoryRepo)
- [ ] `tests/test_service_domain.py` — stubs for SVCR-02 (DomainLogic unit tests with stub Resolver)
- [ ] `tests/test_service_payload.py` — stubs for SVCR-03 (PayloadBuilder pure unit tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Import path preservation in IDE | SVCR-04 | IDE auto-import behavior | Verify `from omnifocus_operator.service import OperatorService` resolves correctly |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
