---
phase: 22
slug: service-decomposition
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-19
audited: 2026-03-20
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
| 22-01-01 | 01 | 1 | SVCR-04 | integration | `uv run python -m pytest tests/test_service.py tests/test_server.py -x -q` | ✅ | ✅ green (164 passed) |
| 22-01-02 | 01 | 1 | SVCR-01 | unit | `uv run python -m pytest tests/test_service_resolve.py -x -q` | ✅ | ✅ green (17 passed) |
| 22-01-03 | 01 | 1 | SVCR-02 | unit | `uv run python -m pytest tests/test_service_domain.py -x -q` | ✅ | ✅ green (25 passed) |
| 22-01-04 | 01 | 1 | SVCR-03 | unit | `uv run python -m pytest tests/test_service_payload.py -x -q` | ✅ | ✅ green (15 passed) |
| 22-01-05 | 01 | 1 | SVCR-05 | unit | `uv run python -m pytest tests/test_service_resolve.py tests/test_service_domain.py tests/test_service_payload.py -x -q` | ✅ | ✅ green (57 passed) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [x] `tests/test_service_resolve.py` — 17 tests for SVCR-01 (Resolver unit tests with real InMemoryRepo)
- [x] `tests/test_service_domain.py` — 25 tests for SVCR-02 (DomainLogic unit tests with stub Resolver)
- [x] `tests/test_service_payload.py` — 15 tests for SVCR-03 (PayloadBuilder pure unit tests)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Import path preservation in IDE | SVCR-04 | IDE auto-import behavior | Verify `from omnifocus_operator.service import OperatorService` resolves correctly |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 10s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete

---

## Validation Audit 2026-03-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
