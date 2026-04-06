---
phase: 41
slug: write-pipeline-inbox-in-add-edit
status: complete
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-06
---

# Phase 41 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 8.x |
| **Config file** | `pyproject.toml` |
| **Quick run command** | `uv run pytest tests/test_contracts_field_constraints.py tests/test_service.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q --timeout=120` |
| **Estimated runtime** | ~24 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_contracts_field_constraints.py tests/test_service.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q --timeout=120`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 24 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 41-01-01 | 01 | 1 | MODL-09 | — | N/A | unit | `uv run pytest tests/test_contracts_type_aliases.py -x -q` | ✅ | ✅ green |
| 41-01-02 | 01 | 1 | MODL-10 | — | N/A | unit + schema | `uv run pytest tests/test_output_schema.py tests/test_contracts_field_constraints.py -x -q` | ✅ | ✅ green |
| 41-01-03 | 01 | 1 | WRIT-06 | T-41-01 | null ending rejected with educational error | unit | `uv run pytest tests/test_contracts_field_constraints.py::TestMoveActionNullRejection::test_ending_null_rejected -x -q` | ✅ | ✅ green |
| 41-01-04 | 01 | 1 | WRIT-07 | T-41-01 | null beginning rejected with educational error | unit | `uv run pytest tests/test_contracts_field_constraints.py::TestMoveActionNullRejection::test_beginning_null_rejected -x -q` | ✅ | ✅ green |
| 41-01-05 | 01 | 1 | WRIT-08 | T-41-01 | null before/after rejected with educational error | unit | `uv run pytest tests/test_contracts_field_constraints.py::TestMoveActionNullRejection -x -q` | ✅ | ✅ green |
| 41-02-01 | 02 | 2 | WRIT-01 | T-41-04 | $inbox parent resolves to inbox | integration | `uv run pytest tests/test_service.py -x -q -k "parent_inbox_resolves"` | ✅ | ✅ green |
| 41-02-02 | 02 | 2 | WRIT-02 | T-41-04 | omitted parent defaults to inbox | integration | `uv run pytest tests/test_service.py -x -q -k "parent_omitted_creates_inbox"` | ✅ | ✅ green |
| 41-02-03 | 02 | 2 | WRIT-03 | T-41-03 | null parent rejected with educational error | unit | `uv run pytest tests/test_contracts_field_constraints.py::TestAddTaskCommandParent::test_parent_null_rejected -x -q` | ✅ | ✅ green |
| 41-02-04 | 02 | 2 | WRIT-04 | — | ending=$inbox moves to inbox | integration | `uv run pytest tests/test_service.py -x -q -k "ending_inbox_moves"` | ✅ | ✅ green |
| 41-02-05 | 02 | 2 | WRIT-05 | — | beginning=$inbox moves to inbox | integration | `uv run pytest tests/test_service.py -x -q -k "beginning_inbox_moves"` | ✅ | ✅ green |
| 41-02-06 | 02 | 2 | WRIT-08 | — | before $inbox returns cross-type error | integration | `uv run pytest tests/test_service.py -x -q -k "before_inbox_rejected"` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Wave 0 Requirements

Existing infrastructure covers all phase requirements.

---

## Manual-Only Verifications

All phase behaviors have automated verification.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 24s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-06

---

## Validation Audit 2026-04-06

| Metric | Count |
|--------|-------|
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
