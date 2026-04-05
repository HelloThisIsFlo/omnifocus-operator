---
phase: 40
slug: resolver-system-location-detection-name-resolution
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-05
validated: 2026-04-05
---

# Phase 40 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 7.x |
| **Config file** | pyproject.toml |
| **Quick run command** | `uv run pytest tests/test_service_resolve.py -x -q` |
| **Full suite command** | `uv run pytest tests/ -x -q` |
| **Estimated runtime** | ~23 seconds |

---

## Sampling Rate

- **After every task commit:** Run `uv run pytest tests/test_service_resolve.py -x -q`
- **After every plan wave:** Run `uv run pytest tests/ -x -q`
- **Before `/gsd-verify-work`:** Full suite must be green
- **Max feedback latency:** 23 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 40-01-01 | 01 | 1 | SLOC-02, SLOC-03, NRES-06 | T-40-01 | $-prefix short-circuits before name/ID lookup; unknown $-prefix returns educational error | unit | `uv run pytest tests/test_service_resolve.py -x -q` | ✅ | ✅ green |
| 40-01-02 | 01 | 1 | NRES-01, NRES-02, NRES-03, NRES-04, NRES-05 | T-40-02 | Ambiguity errors list entity IDs+names (agent's own data, no cross-user leak) | unit | `uv run pytest tests/test_service_resolve.py -x -q` | ✅ | ✅ green |
| 40-01-03 | 01 | 1 | NRES-08 | — | N/A | unit | `uv run pytest tests/test_service_resolve.py -x -q` | ✅ | ✅ green |
| 40-02-01 | 02 | 2 | NRES-01, NRES-02, NRES-03 | T-40-05, T-40-06 | Resolved IDs used in return dicts, not raw input | integration | `uv run pytest tests/test_service.py -k NameResolution -x -q` | ✅ | ✅ green |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

---

## Requirement Coverage Matrix

| Requirement | Description | Unit Tests | Integration Tests | Status |
|-------------|-------------|------------|-------------------|--------|
| SLOC-02 | $-prefix → system location routing | `test_system_location_inbox`, `test_resolve_container_inbox` | `test_add_task_parent_system_location`, `test_edit_task_move_ending_system_location` | COVERED |
| SLOC-03 | Unknown $ → error with valid locations | `test_system_location_unknown` | — | COVERED |
| NRES-01 | add_tasks parent accepts names | `test_resolve_container_by_name` | `test_add_task_parent_by_name`, `test_add_task_parent_by_name_substring`, `test_add_task_parent_name_not_found` | COVERED |
| NRES-02 | edit_tasks beginning/ending accept names | `test_resolve_container_by_name` | `test_edit_task_move_ending_by_name`, `test_edit_task_move_beginning_by_name` | COVERED |
| NRES-03 | edit_tasks before/after accept task names | `test_resolve_anchor_by_name` | `test_edit_task_move_before_by_name`, `test_edit_task_move_after_by_name`, `test_edit_task_move_anchor_not_found` | COVERED |
| NRES-04 | Multiple matches → error with IDs | `test_substring_match_ambiguous`, `test_ambiguous` | — | COVERED |
| NRES-05 | Zero matches → helpful error | `test_no_match_fuzzy_suggestions`, `test_no_match_no_suggestions`, `test_not_found` | `test_add_task_parent_name_not_found` | COVERED |
| NRES-06 | $-prefix never enters name resolution | `test_dollar_prefix_on_tags_reserved`, `test_resolve_anchor_inbox_rejected` | — | COVERED |
| NRES-08 | Tag substring matching | `test_substring_match`, `test_full_name_match`, `test_case_insensitive`, `test_id_fallback`, `test_multiple_tags`, `test_single_fetch` | — | COVERED |

---

## Wave 0 Requirements

*Existing infrastructure covers all phase requirements.*

---

## Manual-Only Verifications

*All phase behaviors have automated verification.*

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 23s
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** approved 2026-04-05

---

## Validation Audit 2026-04-05

| Metric | Count |
|--------|-------|
| Requirements audited | 9 |
| Gaps found | 0 |
| Resolved | 0 |
| Escalated | 0 |
| Unit tests covering phase | 48 |
| Integration tests covering phase | 10 |
| Full suite | 1559 passed, 98.24% coverage |
