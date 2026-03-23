---
phase: 24
slug: test-double-relocation-to-tests
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-20
---

# Phase 24 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x with pytest-asyncio, pytest-cov, pytest-timeout |
| **Config file** | `pyproject.toml` (`[tool.pytest.ini_options]`) |
| **Quick run command** | `uv run python -m pytest tests/test_bridge.py::TestTestDoubleRelocation -v` |
| **Full suite command** | `uv run python -m pytest -x --timeout=60` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run python -m pytest -x --timeout=60`
- **After every plan wave:** Run `uv run python -m pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 2 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 24-01-01 | 01 | 1 | INFRA-08 | negative import | `uv run python -m pytest tests/test_bridge.py::TestTestDoubleRelocation -v` | ✅ | ✅ green |
| 24-01-01 | 01 | 1 | INFRA-08 | import verification | `uv run python -c "from tests.doubles import InMemoryBridge, BridgeCall, SimulatorBridge, ConstantMtimeSource, InMemoryRepository"` | ✅ | ✅ green |
| 24-01-02 | 01 | 1 | INFRA-09 | structural | `grep -r "from tests\." src/` (must return empty) | ✅ | ✅ green |
| 24-01-02 | 01 | 1 | INFRA-08, INFRA-09 | regression | `uv run python -m pytest -x --timeout=60` (597 tests) | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. No new test framework, config, or fixture setup needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 2s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-03-20

---

## Validation Audit 2026-03-20

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
