---
phase: 19
slug: inmemorybridge-export-cleanup
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-17
---

# Phase 19 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ with pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x --no-header -q` |
| **Full suite command** | `uv run pytest tests/ --no-header -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --no-header -q`
- **After every plan wave:** Run `uv run pytest tests/ --no-header -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 19-01-01 | 01 | 1 | INFRA-01 | unit | `uv run pytest tests/ -x -q --no-header` | ✅ | ⬜ pending |
| 19-01-02 | 01 | 1 | INFRA-03 | unit | `uv run pytest tests/ -x -q --no-header` | ✅ | ⬜ pending |
| 19-01-03 | 01 | 1 | INFRA-02 | meta/grep | `grep -rn "from omnifocus_operator.bridge import.*InMemoryBridge" tests/` (must return empty) | N/A | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements. The 534+ test suite is the primary verification — if all tests pass after import migration, the requirements are satisfied. No new test framework setup needed.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
