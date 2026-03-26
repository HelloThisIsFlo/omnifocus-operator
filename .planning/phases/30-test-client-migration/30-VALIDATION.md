---
phase: 30
slug: test-client-migration
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-26
audited: 2026-03-26
---

# Phase 30 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_server.py -x -q` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~11 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_server.py -x -q`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 11 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 30-01-01 | 01 | 1 | TEST-01 | migration | `grep -r '_ClientSessionProxy' tests/ --include='*.py'` | ✅ | ✅ green |
| 30-01-02 | 01 | 1 | TEST-02 | migration | `grep -r 'run_with_client' tests/ --include='*.py'` | ✅ | ✅ green |
| 30-02-01 | 02 | 1 | TEST-03 | migration | `grep -rc 'async with Client(server)' tests/test_server.py tests/test_simulator_bridge.py tests/test_simulator_integration.py` | ✅ | ✅ green |
| 30-03-01 | 01+02 | 1 | TEST-04 | cleanup | `grep -rn 'isError' tests/ --include='*.py' \| grep -v '"""'` | ✅ | ✅ green |
| 30-04-01 | 02 | 2 | TEST-05 | regression | `uv run pytest -x --no-cov` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Audit 2026-03-26

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |

### Evidence

- **TEST-01**: `grep -r '_ClientSessionProxy' tests/ --include='*.py'` → 0 matches
- **TEST-02**: `grep -r 'run_with_client' tests/ --include='*.py'` → 0 matches
- **TEST-03**: `Client(server)` pattern → 17 uses across 3 test files
- **TEST-04**: `grep -rn 'isError' tests/ --include='*.py'` → 0 code matches (2 docstring references, expected)
- **TEST-05**: `uv run pytest -x --no-cov` → 697 passed in 10.62s

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** complete
