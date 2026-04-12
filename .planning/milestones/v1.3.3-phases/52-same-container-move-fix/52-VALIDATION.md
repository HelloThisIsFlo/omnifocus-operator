---
phase: 52
slug: same-container-move-fix
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-12
---

# Phase 52 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x with pytest-asyncio |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_service_domain.py tests/test_service.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~27 seconds (full), ~1 second (quick) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_service_domain.py tests/test_service.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 27 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 52-01-01 | 01 | 1 | MOVE-01 | — | N/A | unit | `uv run pytest tests/test_service_domain.py::TestProcessMove::test_move_beginning_translates_to_before_first_child -x -q` | ✅ | ✅ green |
| 52-01-02 | 01 | 1 | MOVE-02 | — | N/A | unit | `uv run pytest tests/test_service_domain.py::TestProcessMove::test_move_ending_translates_to_after_last_child -x -q` | ✅ | ✅ green |
| 52-01-03 | 01 | 1 | MOVE-03 | T-52-01 | Parameterized SQL queries | unit | `uv run pytest tests/test_service_domain.py::TestProcessMove -x -q` | ✅ | ✅ green |
| 52-01-04 | 01 | 1 | MOVE-04 | — | N/A | unit | `uv run pytest tests/test_service_domain.py::TestProcessMove::test_move_beginning_empty_container_no_translation tests/test_service_domain.py::TestProcessMove::test_move_ending_empty_container_no_translation -x -q` | ✅ | ✅ green |
| 52-01-05 | 01 | 1 | MOVE-05 | — | N/A | integration | `uv run pytest tests/ -x -q` (full suite regression) | ✅ | ✅ green |
| 52-01-06 | 01 | 1 | WARN-02 | — | N/A | unit | `uv run pytest tests/test_service_domain.py::TestProcessMove::test_move_beginning_translates_to_before_first_child -x -q` | ✅ | ✅ green |
| 52-01-07 | 01 | 1 | WARN-03 | — | N/A | unit | `uv run pytest tests/test_service_domain.py::TestProcessMove::test_move_ending_translates_to_after_last_child -x -q` | ✅ | ✅ green |
| 52-02-01 | 02 | 2 | MOVE-06 | — | N/A | structural | `uv run pytest tests/test_agent_messages.py -x -q` (AST enforcement prevents orphaned constants) | ✅ | ✅ green |
| 52-02-02 | 02 | 2 | WARN-01 | — | N/A | unit | `uv run pytest tests/test_service_domain.py::TestMoveNoOpDetection -x -q` | ✅ | ✅ green |
| 52-02-03 | 02 | 2 | WARN-02 | — | N/A | unit+integration | `uv run pytest tests/test_service_domain.py::TestProcessMove tests/test_service.py::TestEditTask::test_same_container_move_noop_detected -x -q` | ✅ | ✅ green |
| 52-02-04 | 02 | 2 | WARN-03 | — | N/A | unit+integration | `uv run pytest tests/test_service_domain.py::TestProcessMove tests/test_service.py::TestEditTask::test_same_container_move_noop_detected -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Test Coverage Detail

### Domain-level tests (`tests/test_service_domain.py`)

**TestProcessMove** — translation logic:
- `test_move_beginning_translates_to_before_first_child` — MOVE-01, MOVE-03, WARN-02
- `test_move_ending_translates_to_after_last_child` — MOVE-02, MOVE-03, WARN-03
- `test_move_beginning_empty_container_no_translation` — MOVE-04
- `test_move_ending_empty_container_no_translation` — MOVE-04
- `test_move_to_inbox_beginning_translates` — MOVE-05 (inbox path)
- `test_move_to_inbox_ending_empty_no_translation` — MOVE-04 (inbox empty)

**TestMoveNoOpDetection** — anchor_id == task_id detection:
- `test_anchor_id_equals_task_id_beginning_is_noop` — WARN-01 (SC8)
- `test_anchor_id_equals_task_id_ending_is_noop` — WARN-01 (SC9)
- `test_anchor_id_different_from_task_id_not_noop` — WARN-01 (SC6/SC7)
- `test_untranslated_same_container_is_noop` — WARN-01 (empty container)
- `test_untranslated_different_container_not_noop` — WARN-01 (different container)

### Service integration tests (`tests/test_service.py`)

- `test_same_container_move_noop_detected` — end-to-end via BridgeOnlyRepository (WARN-01, WARN-02, WARN-03)
- `test_noop_same_container_move_single_warning` — no duplicate warnings (WARN-01)

### Structural validation

- `test_all_warning_constants_referenced_in_consumers` — AST enforcement prevents orphaned constants (MOVE-06)

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 27s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-12
