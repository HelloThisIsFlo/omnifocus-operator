---
phase: 51
slug: task-ordering
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
validated: 2026-04-12
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
| 51-01-T1 | 01 | 1 | ORDER-01, ORDER-03 | T-51-01 | extra="forbid" rejects order on edit | unit | `uv run pytest tests/test_models.py::TestCommandModelStrictness::test_edit_task_command_rejects_order_field -v` | ✅ | ✅ green |
| 51-01-T2 | 01 | 1 | ORDER-01 (D-05) | — | N/A | unit | `uv run pytest tests/ -x -q` | ✅ | ✅ green |
| 51-02-T1 | 02 | 2 | ORDER-02, ORDER-04, ORDER-05 | T-51-03, T-51-04 | N/A | unit | `uv run pytest tests/test_hybrid_repository.py::TestTaskOrdering -v` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

**Task breakdown:**
- **51-01-T1** (Plan 01, Task 1): Add order field to Task model, update descriptions, fix bridge adapter. Covers ORDER-01 (field exists), ORDER-03 (edit rejected by extra="forbid").
- **51-01-T2** (Plan 01, Task 2): Update test factories and cross-path equivalence. Covers ORDER-01 (defaults) and D-05 (cross-path divergence).
- **51-02-T1** (Plan 02, Task 1): CTE ordering + dotted path computation. Covers ORDER-02 (sequential siblings), ORDER-04 (outline order), ORDER-05 (inbox after projects).

---

## Wave 0 Requirements

- [x] `tests/conftest.py` — add `order` default to `make_model_task_dict()`
- [x] `tests/test_cross_path_equivalence.py` — exclude `order` from `assert_equivalent()`
- [x] New tests in `tests/test_hybrid_repository.py` for order field presence, outline ordering, inbox-after-projects (TDD in Plan 02)

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| — | — | — | — |

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated

---

## Validation Audit 2026-04-12

| Metric | Count |
|--------|-------|
| Gaps found | 1 |
| Resolved | 1 |
| Escalated | 0 |

### Gap Resolution

**ORDER-03** (51-01-T1): Added explicit test proving `EditTaskCommand` rejects `order` field.
- Test: `tests/test_models.py::TestCommandModelStrictness::test_edit_task_command_rejects_order_field`
- Behavior: Verifies `EditTaskCommand.model_validate({"id": "t1", "order": "2.3.1"})` raises `ValidationError` matching "order"
- Status: ✅ green

Full test suite: 2030 passed, 98% coverage
