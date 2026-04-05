---
phase: 39
slug: foundation-constants-reference-models
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
---

# Phase 39 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` [tool.pytest.ini_options] |
| **Quick run command** | `uv run pytest tests/test_models.py tests/test_system_locations.py -x -q --no-cov` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~8 seconds (full), ~0.3 seconds (quick) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_models.py tests/test_system_locations.py -x -q --no-cov`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 8 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 39-01-01 | 01 | 1 | SLOC-01 | unit | `uv run pytest tests/test_system_locations.py -x -q --no-cov` | ✅ | ✅ green |
| 39-01-02 | 01 | 1 | MODL-01 | unit | `uv run pytest tests/test_models.py::TestProjectRef -x -q --no-cov` | ✅ | ✅ green |
| 39-01-02 | 01 | 1 | MODL-02 | unit | `uv run pytest tests/test_models.py::TestTaskRef -x -q --no-cov` | ✅ | ✅ green |
| 39-01-02 | 01 | 1 | MODL-03 | unit | `uv run pytest tests/test_models.py::TestFolderRef -x -q --no-cov` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have automated verify
- [x] Sampling continuity: no gaps without automated verify
- [x] All MISSING references resolved
- [x] No watch-mode flags
- [x] Feedback latency < 8s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-05

## Validation Audit 2026-04-05

| Metric | Count |
|--------|-------|
| Gaps found | 4 |
| Resolved | 4 |
| Escalated | 0 |
