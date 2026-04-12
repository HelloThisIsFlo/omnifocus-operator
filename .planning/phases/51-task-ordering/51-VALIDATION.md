---
phase: 51
slug: task-ordering
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-12
---

# Phase 51 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest + pytest-asyncio |
| **Config file** | `pyproject.toml` `[tool.pytest.ini_options]` |
| **Quick run command** | `uv run pytest tests/ -x -q` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 51-01-01 | 01 | 1 | ORDER-01 | — | N/A | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k order` | ❌ W0 | ⬜ pending |
| 51-01-02 | 01 | 1 | ORDER-01 | — | N/A | unit | `uv run pytest tests/test_bridge_only_repository.py -x -q -k order` | ❌ W0 | ⬜ pending |
| 51-02-01 | 02 | 1 | ORDER-02 | — | N/A | unit | `uv run pytest tests/test_query_builder.py -x -q -k order` | ❌ W0 | ⬜ pending |
| 51-03-01 | 03 | 1 | ORDER-03 | — | N/A | unit | `uv run pytest tests/test_output_schema.py -x -q` | ✅ | ⬜ pending |
| 51-04-01 | 04 | 2 | ORDER-04 | — | N/A | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k outline_order` | ❌ W0 | ⬜ pending |
| 51-05-01 | 05 | 2 | ORDER-05 | — | N/A | unit | `uv run pytest tests/test_hybrid_repository.py -x -q -k inbox_after` | ❌ W0 | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

- [ ] `tests/test_hybrid_repository.py` — tests for order field presence, outline ordering, inbox-after-projects
- [ ] `tests/test_bridge_only_repository.py` — test for order=None on bridge path
- [ ] `tests/test_query_builder.py` — tests for CTE-based ordering SQL
- [ ] `tests/conftest.py` — add `order` default to `make_model_task_dict()` and `make_task_dict()`
- [ ] `tests/test_cross_path_equivalence.py` — exclude `order` from `assert_equivalent()`

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 15s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
