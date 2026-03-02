---
phase: 4
slug: repository-and-snapshot-management
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-03-02
---

# Phase 4 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.x + pytest-asyncio 1.3.x |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/test_repository.py -x` |
| **Full suite command** | `uv run pytest` |
| **Estimated runtime** | ~2 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_repository.py -x`
- **After every plan wave:** Run `uv run pytest`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 5 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|-----------|-------------------|-------------|--------|
| 04-01-01 | 01 | 1 | SNAP-01 | unit | `uv run pytest tests/test_repository.py::TestRepository::test_first_call_triggers_dump -x` | ❌ W0 | ⬜ pending |
| 04-01-02 | 01 | 1 | SNAP-02 | unit | `uv run pytest tests/test_repository.py::TestRepository::test_cached_read_no_bridge_call -x` | ❌ W0 | ⬜ pending |
| 04-01-03 | 01 | 1 | SNAP-03 | unit | `uv run pytest tests/test_repository.py::TestRepository::test_unchanged_mtime_serves_cache -x` | ❌ W0 | ⬜ pending |
| 04-01-04 | 01 | 1 | SNAP-04 | unit | `uv run pytest tests/test_repository.py::TestRepository::test_changed_mtime_triggers_refresh -x` | ❌ W0 | ⬜ pending |
| 04-01-05 | 01 | 1 | SNAP-05 | unit | `uv run pytest tests/test_repository.py::TestRepository::test_concurrent_reads_single_dump -x` | ❌ W0 | ⬜ pending |
| 04-01-06 | 01 | 1 | SNAP-06 | unit | `uv run pytest tests/test_repository.py::TestRepository::test_initialize_prewarms_cache -x` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_repository.py` — stubs for SNAP-01 through SNAP-06 + error propagation
- [ ] `tests/conftest.py` or test module — `FakeMtimeSource` fixture and snapshot dict helper

*Existing infrastructure covers framework install (pytest + pytest-asyncio already configured).*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| OmniFocus `.ofocus` mtime updates on data change | SNAP-03/04 | Requires live OmniFocus + real filesystem | Phase 8 UAT: edit a task in OmniFocus, verify mtime changes, verify snapshot refreshes |

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 5s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
