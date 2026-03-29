---
phase: 33
slug: write-model-validation-bridge
status: draft
nyquist_compliant: true
wave_0_complete: true
created: 2026-03-28
---

# Phase 33 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/ -x -q --timeout=10` |
| **Full suite command** | `uv run pytest tests/ -q` |
| **Estimated runtime** | ~15 seconds |
| **Test directory layout** | Flat — all test files in `tests/`, no subdirectories (except `tests/doubles/` and `tests/golden_master/`) |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/ -x -q --timeout=10`
- **After every plan wave:** Run `uv run pytest tests/ -q`
- **Before `/gsd:verify-work`:** Full suite must be green
- **Max feedback latency:** 15 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Description | Automated Command | Status |
|---------|------|------|-------------|-------------------|--------|
| 33-01-T1 | 01 | 1 | Spec models + command integration | `uv run pytest tests/test_contracts_repetition_rule.py -x -q` | ⬜ pending |
| 33-01-T2 | 01 | 1 | Inverse mappings, validation, agent messages | `uv run pytest tests/test_rrule_schedule_inverse.py tests/test_validation_repetition.py -x -q` | ⬜ pending |
| 33-02-T1 | 02 | 2 | PayloadBuilder + domain logic + InMemoryBridge | `uv run pytest tests/test_service_payload.py tests/test_service_domain.py -x -q` | ⬜ pending |
| 33-02-T2 | 02 | 2 | _AddTaskPipeline + AddTaskResult warnings | `uv run pytest tests/test_service.py -x -q -k add && uv run pytest tests/test_output_schema.py -x -q` | ⬜ pending |
| 33-02-T3 | 02 | 2 | _EditTaskPipeline merge logic | `uv run pytest tests/test_service.py -x -q -k edit` | ⬜ pending |
| 33-03-T1 | 03 | 3 | Bridge JS reverse lookups + repetition rule handling | `uv run pytest -x -q` | ⬜ pending |
| 33-03-T2 | 03 | 3 | Tool descriptions + server error handling + output schema | `uv run pytest tests/test_server.py tests/test_output_schema.py -x -q` | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Key Verification Checkpoints

| Checkpoint | When | Command | Why |
|------------|------|---------|-----|
| Output schema after AddTaskResult change | After 33-02-T2 | `uv run pytest tests/test_output_schema.py -x -q` | CLAUDE.md: required after modifying output models |
| Full suite after Plan 02 | After 33-02-T3 | `uv run pytest -x -q` | Service layer complete, catch cross-cutting regressions |
| Full suite after Plan 03 | After 33-03-T2 | `uv run pytest -x -q` | Phase complete |

---

## Wave 0 Requirements

- [x] Existing test infrastructure covers all phase requirements — no new test fixtures needed beyond what each task creates
- [x] Test directory is flat (`tests/test_*.py`) — no `tests/contracts/` or `tests/service/` subdirectories
- [x] `tests/doubles/bridge.py` (InMemoryBridge) exists and will be extended in Plan 02 Task 1

*Existing infrastructure fully covers all phase requirements.*

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Task appears in OmniFocus with correct recurrence | ADD-01 | Requires real OmniFocus (SAFE-01) | UAT via `uat/` scripts against live database |
| Edited rule reflects in OmniFocus UI | EDIT-01 | Requires real OmniFocus (SAFE-01) | UAT via `uat/` scripts against live database |

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify commands
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 requirements satisfied (flat test layout, no missing fixtures)
- [x] No watch-mode flags
- [x] Feedback latency < 15s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
