---
phase: 55
slug: notes-graduation
status: draft
nyquist_compliant: false
wave_0_complete: false
created: 2026-04-16
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
| **Estimated runtime** | ~60 seconds (quick), ~3-5 min (full, 2086 tests) |

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
| 55-01-* | 01 | 1 | NOTE-02, NOTE-03 (contract) | — | N/A | unit (contract) | `uv run pytest tests/test_contracts_actions.py::TestNoteAction -x -q` | ❌ W0 (new file or extend existing) | ⬜ pending |
| 55-02-* | 02 | 2 | NOTE-02, NOTE-03, NOTE-04 (domain) | — | N/A | unit (domain) | `uv run pytest tests/test_service_domain.py::TestProcessNoteAction -x -q` | ❌ W0 | ⬜ pending |
| 55-03-* | 03 | 2-3 | NOTE-01, NOTE-02, NOTE-03, NOTE-04 (pipeline) | — | N/A | integration | `uv run pytest tests/test_service.py::TestEditTask -x -q` | ✅ (needs rewrite + new tests) | ⬜ pending |
| 55-04-* | 04 | 3 | NOTE-01 (schema), NOTE-05 (regression) | — | N/A | unit (schema) | `uv run pytest tests/test_output_schema.py tests/test_descriptions.py -x -q` | ✅ existing | ⬜ pending |

*Status: ⬜ pending · ✅ green · ❌ red · ⚠️ flaky*

See `55-RESEARCH.md` §Phase Requirements → Test Map for the complete per-requirement matrix (21 rows).

---

## Wave 0 Requirements

- [ ] `tests/test_contracts_actions.py` (NEW file) OR extended class in `tests/test_service_domain.py` — `NoteAction` contract validator tests (exclusivity, at-least-one, type rejection; 4–5 tests)
- [ ] `tests/test_service_domain.py::TestProcessNoteAction` (NEW class) — `DomainLogic.process_note_action` unit tests (8 tests covering UNSET, append-empty, append-on-empty, append-on-non-empty, replace-identical, clear-on-empty, clear-on-non-empty, replace-with-new-content)
- [ ] `tests/test_service.py::TestEditTask` — NEW integration tests for `test_note_action_alone`, `test_note_with_other_actions`, no-op warning propagation (3–4 tests)
- [ ] `tests/test_output_schema.py` — NEW test asserting `EditTaskCommand` JSON schema has no top-level `note` property
- [ ] **Framework install:** none — pytest already present

---

## Manual-Only Verifications

| Behavior | Requirement | Why Manual | Test Instructions |
|----------|-------------|------------|-------------------|
| Live OmniFocus `actions.note.append` on a real task | NOTE-02 | SAFE-01/02 — no RealBridge in CI; only human-initiated UAT | Run `uat/` scripts manually against real OmniFocus database (human only, not agent/CI) |
| Live OmniFocus `actions.note.replace` clearing an existing note | NOTE-03 | Same as above | Same UAT pathway |

All automated tests use `InMemoryBridge` / `SimulatorBridge` exclusively per project CLAUDE.md.

---

## Validation Sign-Off

- [ ] All tasks have `<automated>` verify or Wave 0 dependencies
- [ ] Sampling continuity: no 3 consecutive tasks without automated verify
- [ ] Wave 0 covers all MISSING references
- [ ] No watch-mode flags
- [ ] Feedback latency < 60s
- [ ] `nyquist_compliant: true` set in frontmatter

**Approval:** pending
