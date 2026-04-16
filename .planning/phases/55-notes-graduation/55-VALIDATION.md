---
phase: 55
slug: notes-graduation
status: validated
nyquist_compliant: true
wave_0_complete: true
created: 2026-04-16
audited: 2026-04-16
---

# Phase 55 — Validation Strategy

> Per-phase validation contract for feedback sampling during execution.
> Full reference: `.planning/phases/55-notes-graduation/55-RESEARCH.md` §Validation Architecture.

---

## Test Infrastructure

| Property | Value |
|----------|-------|
| **Framework** | pytest 9.0.2 + pytest-asyncio |
| **Config file** | `pyproject.toml` (pytest settings) |
| **Quick run command** | `uv run pytest tests/test_service_domain.py tests/test_contracts_type_aliases.py tests/test_service.py -x -q` |
| **Full suite command** | `uv run pytest -x -q` |
| **Estimated runtime** | ~60 seconds (quick), ~15 seconds full (2163 tests) |

**Mandatory regression (project CLAUDE.md):**
- `uv run pytest tests/test_output_schema.py -x -q` — after any model change touching tool output
- `uv run pytest tests/test_descriptions.py -x -q` — AST enforcement for description centralization

---

## Sampling Rate

- **After every task commit:** Run quick run command
- **After every plan wave:** Run full suite command
- **Before `/gsd-verify-work`:** Full suite must be green + mypy clean + output-schema regression green
- **Max feedback latency:** ~60 seconds

---

## Per-Task Verification Map

| Task ID | Plan | Wave | Requirement | Threat Ref | Secure Behavior | Test Type | Automated Command | File Exists | Status |
|---------|------|------|-------------|------------|-----------------|-----------|-------------------|-------------|--------|
| 55-01-* | 01 | 1 | NOTE-01, NOTE-02, NOTE-03, NOTE-05 (contract) | — | N/A | unit (contract) | `uv run pytest tests/test_service_domain.py::TestNoteAction -x -q` | ✅ | ✅ green (4/4) |
| 55-02-* | 02 | 2 | NOTE-02, NOTE-03, NOTE-04 (domain) | — | N/A | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction -x -q` | ✅ | ✅ green (15/15) |
| 55-03-* | 03 | 3 | NOTE-01, NOTE-02, NOTE-03, NOTE-04 (integration) | — | N/A | integration | `uv run pytest tests/test_service.py::TestEditTask::test_note_action_alone tests/test_service.py::TestEditTask::test_note_with_other_actions tests/test_service.py::TestEditTask::test_note_noop_warning_surfaces_in_result -x -q` | ✅ | ✅ green (3/3) |
| 55-03-* | 03 | 3 | NOTE-01 (schema), NOTE-05 (regression) | — | N/A | unit (schema + regression) | `uv run pytest tests/test_output_schema.py tests/test_descriptions.py tests/test_service.py::TestAddTask -x -q` | ✅ | ✅ green (63/63) |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

### Requirement → Test Coverage

| Requirement | Coverage | Layer |
|-------------|----------|-------|
| **NOTE-01** (top-level `note` removed) | `test_edit_task_command_has_no_top_level_note` + `tests/test_contracts_type_aliases.py` + `tests/test_descriptions.py` AST | schema + unit + AST |
| **NOTE-02** (`append` semantics + N1 no-op) | `TestNoteAction::test_append_null_rejected_by_type` + `TestProcessNoteAction::test_append_on_non_empty_note_concatenates_with_separator` + `test_append_empty_string_is_noop_with_n1_warning` | contract + domain |
| **NOTE-03** (`replace` semantics + N2/N3 no-ops) | `TestNoteAction` exclusivity + `TestProcessNoteAction::test_replace_with_new_content_sets_note / test_replace_null_clears_non_empty_note / test_replace_empty_string_clears_non_empty_note / test_replace_identical_content_is_noop_with_n2_warning / test_replace_null_on_none_note_is_noop_with_n3_warning` + `test_note_noop_warning_surfaces_in_result` | contract + domain + integration |
| **NOTE-04** (append-on-empty sets directly) | `TestProcessNoteAction::test_append_on_empty_string_note_sets_directly / test_append_on_none_note_sets_directly / test_append_on_whitespace_only_note_discards_whitespace` + `test_note_action_alone` (integration proof) | domain + integration |
| **NOTE-05** (`AddTaskCommand.note` unchanged) | `TestAddTask` (19 tests) + `tests/test_output_schema.py` | integration + schema |

See `55-RESEARCH.md` §Phase Requirements → Test Map for the full 21-row research-time matrix.

---

## Wave 0 Requirements

- [x] `tests/test_service_domain.py::TestNoteAction` (NEW class) — `NoteAction` contract validator tests (exclusivity, at-least-one, null rejection, PatchOrClear null valid; 4 tests)
- [x] `tests/test_service_domain.py::TestProcessNoteAction` (NEW class) — `DomainLogic.process_note_action` unit tests (15 tests covering UNSET passthrough, append-on-empty/whitespace/non-empty, append-empty N1, replace new/identical N2, replace null/empty clears, clear-already-empty N3, whitespace-only-not-noop)
- [x] `tests/test_service.py::TestEditTask` — integration tests: `test_note_action_alone`, `test_note_with_other_actions`, `test_note_noop_warning_surfaces_in_result` (3 tests)
- [x] `tests/test_output_schema.py::TestWriteSchemaNoDateTimeFormat::test_edit_task_command_has_no_top_level_note` — schema regression asserting `EditTaskCommand` JSON schema has no top-level `note` property
- [x] **Framework install:** none — pytest already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live OmniFocus `actions.note.append` on a real task | NOTE-02 | SAFE-01/02 — no RealBridge in CI; only human-initiated UAT | Run `uat/` scripts manually against real OmniFocus database (human only, not agent/CI) |
| Live OmniFocus `actions.note.replace` clearing an existing note | NOTE-03 | Same as above | Same UAT pathway |

All automated tests use `InMemoryBridge` / `SimulatorBridge` exclusively per project CLAUDE.md.

---

## Validation Sign-Off

- [x] All tasks have `<automated>` verify or Wave 0 dependencies
- [x] Sampling continuity: no 3 consecutive tasks without automated verify
- [x] Wave 0 covers all MISSING references
- [x] No watch-mode flags
- [x] Feedback latency < 60s (full suite runs in ~15s)
- [x] `nyquist_compliant: true` set in frontmatter

**Approval:** validated 2026-04-16 — all 5 NOTE-XX requirements have direct automated coverage; full suite 2163 tests green.

---

## Validation Audit 2026-04-16

Post-execution audit against completed phase (commits `0c7f53dd` → `6fab22fb`).

| Metric | Count |
|--------|-------|
| Requirements | 5 (NOTE-01 through NOTE-05) |
| Gaps found | 0 |
| Resolved | 0 (no gaps) |
| Escalated | 0 |
| New tests added during audit | 0 |
| Full-suite status | 2163 / 2163 green |

### Audit notes

- **Layer mapping drift (not a gap):** RESEARCH.md's test matrix classified three NOTE-03 cases (`replace` on non-empty note: new content, null clears, empty clears) as integration tests. Execution placed them at the domain layer (`TestProcessNoteAction`) instead. Domain-layer coverage is semantically equivalent for these decision-tree branches; pipeline wiring is independently verified by `test_note_action_alone` and `test_note_with_other_actions`. No automated coverage gap exists.
- **File-location note:** RESEARCH.md mentioned an optional `tests/test_contracts_actions.py` file for `TestNoteAction`. Execution followed the "add to existing `tests/test_service_domain.py`" path explicitly allowed by the research matrix — no new file was created.
