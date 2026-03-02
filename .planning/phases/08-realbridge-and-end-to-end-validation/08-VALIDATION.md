---
phase: 8
slug: realbridge-and-end-to-end-validation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 8 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2+ with pytest-asyncio 1.3.0+ |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x --timeout=10` |
| **Full suite command** | `uv run pytest --cov-fail-under=80` |
| **Estimated runtime** | ~5 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x --timeout=10`
- **After every plan wave:** Run `uv run pytest --cov-fail-under=80`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 10 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 08-01-01 | 01 | 1 | BRDG-04 | unit (mock subprocess) | `uv run pytest tests/test_ipc_engine.py::TestTriggerImplementation -x` | ❌ W0 | ⬜ pending |
| 08-01-02 | 01 | 1 | BRDG-04 | manual-only (UAT) | N/A — manual: `uv run python uat/test_read_only.py` | ❌ W0 | ⬜ pending |
| 08-01-03 | 01 | 1 | SAFE-01 | unit | `uv run pytest tests/test_service.py -k "real_refuses" -x` | ❌ W0 | ⬜ pending |
| 08-01-04 | 01 | 1 | SAFE-01 | CI grep | CI step in `.github/workflows/ci.yml` | ❌ W0 | ⬜ pending |
| 08-01-05 | 01 | 1 | SAFE-02 | meta | `uv run pytest --collect-only` verify no uat/ | ❌ W0 | ⬜ pending |
| 08-01-06 | 01 | 1 | TEST-02 | integration | `uv run pytest tests/test_server.py::TestARCH01 -x` | ✅ | ⬜ pending |
| 08-01-07 | 01 | 1 | TEST-03 | audit | `uv run pytest --co -q` verify all layers | ✅ | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] Refactor `tests/test_real_bridge.py` to `tests/test_ipc_engine.py` using SimulatorBridge
- [ ] `uat/test_read_only.py` — manual UAT script for BRDG-04
- [ ] `uat/README.md` — UAT philosophy document for SAFE-02
- [ ] Add SAFE-01 guard test in factory test file
- [ ] Add SAFE-01 CI grep step in `.github/workflows/ci.yml`
- [ ] Add `testpaths` exclusion for `uat/` in `pyproject.toml`
- [ ] Update `CLAUDE.md` with SAFE-01/02 rules
- [ ] Coverage config: add `simulator/__main__.py` to omit

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| RealBridge triggers OmniFocus via URL scheme | BRDG-04 | Requires live OmniFocus installation | Run `uv run python uat/test_read_only.py` — verify dump_all returns valid data |
| .ofocus path exists on target machine | BRDG-04 | Path depends on OmniFocus 4 installation | Check `~/Library/Group Containers/34YW5A73WQ.com.omnigroup.OmniFocus/com.omnigroup.OmniFocus4/OmniFocus.ofocus` exists |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 10s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
